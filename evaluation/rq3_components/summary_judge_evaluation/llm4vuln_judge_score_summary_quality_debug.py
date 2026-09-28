import argparse
import json
import re
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import sys
import time
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError

MAX_RETRIES = 3

# --- Blablador Client Interface ---
class BlabladorClient:
    def __init__(self, model_name, api_key, timeout=60.0):
        self.model_name = model_name
        self.client = OpenAI(
            base_url="https://api.blablador.fz-juelich.de/v1/",
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )

    def list_models(self):
        return [m.id for m in self.client.models.list().data]

    def ping(self):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": "Reply with exactly: OK"}
            ],
            temperature=0,
            max_tokens=256,
        )

        print("\n--- FULL RESPONSE ---")
        print(response.model_dump_json(indent=2))
        print("--- END RESPONSE ---\n")

        return response.choices[0].message.content

    def generate_text(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            content = response.choices[0].message.content

            print(
                f"finish_reason={response.choices[0].finish_reason}, "
                f"completion_tokens={response.usage.completion_tokens}"
            )
            if content is None:
                print(
                    "[WARNING] API request succeeded, but "
                    "response.choices[0].message.content is None"
                )
                return ""

            return content
        
        except APITimeoutError as e:
            print(f"\n[ERROR] Timeout talking to Blablador: {e}")
            return ""
        except APIConnectionError as e:
            print(f"\n[ERROR] Connection error talking to Blablador: {e}")
            return ""
        except APIStatusError as e:
            print(f"\n[ERROR] Blablador HTTP {e.status_code}: {e}")
            if getattr(e, "response", None) is not None:
                try:
                    print(f"[ERROR] Response body: {e.response.text}")
                except Exception:
                    pass
            return ""
        except Exception as e:
            print(f"\n[ERROR] Unexpected Blablador error ({type(e).__name__}): {e}")
            return ""

PATTERNS = {
    "faithfulness": r"Faithfulness:\s*([1-5])",
    "coverage": r"Functional Coverage:\s*([1-5])",
    "retrieval": r"Retrieval Utility:\s*([1-5])",
    "conciseness": r"Conciseness:\s*([1-5])",
    "clarity": r"Clarity:\s*([1-5])",
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--judge-model", default="alias-fast")
    parser.add_argument("--api-key", required=True, help="Your Blablador API key")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--list-models", action="store_true", help="List models visible to this token, then exit")
    parser.add_argument("--ping", action="store_true", help="Send a tiny chat request to --judge-model, then exit")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate at most N samples per input JSON")
    parser.add_argument("--sleep-between", type=float, default=0.0, help="Seconds to sleep between API calls")
    return parser.parse_args()

def valid_scores(scores):
    return all(v is not None for v in scores.values())

def build_prompt(code, summary):
    return f"""You are an expert in C/C++ program analysis. The provided summary is not intended as developer documentation. It will be embedded and used to retrieve semantically similar code from a vulnerability knowledge base. Evaluate the quality of the summary with respect to the source code.
Every criterion must receive an integer score from 1 to 5 and one concise rationale. Never output "N/A", "Not applicable", or leave a score blank. If a criterion cannot reasonably be assessed, assign the lowest appropriate score (1) and explain why.

Faithfulness (1–5)
Every statement must be supported by the source code. Penalize unsupported or incorrect claims.

Functional Coverage (1–5)
Does the summary capture the primary purpose and functionally important behavior of the code? Penalize omission of major functionality or emphasis on minor implementation details.

Retrieval Utility (1–5)
If this summary were used for semantic retrieval, how well would it retrieve semantically similar implementations or vulnerability-relevant code? Reward summaries that preserve discriminative semantic information and penalize summaries that are overly generic.

Conciseness (1–5)
Does the summary remain informative while avoiding unnecessary details or redundancy?

Clarity (1–5)
Is the summary grammatically correct, easy to read, and unambiguous?

### Source Code
{code}

### Summary
{summary}

Evaluate only the quality of the summary with respect to the source code. Do not reward or penalize the summary for failing to identify a vulnerability unless that behavior is explicitly evident from the code itself.
Output exactly in this format:

Faithfulness: <score> | <rationale>
Functional Coverage: <score> | <rationale>
Retrieval Utility: <score> | <rationale>
Conciseness: <score> | <rationale>
Clarity: <score> | <rationale>
"""

def evaluate(client, code, summary):
    prompt_msgs = [{"role": "user", "content": build_prompt(code, summary)}]
    return client.generate_text(messages=prompt_msgs)


def parse_scores(text):
    result = {}

    if not text:
        return {name: None for name in PATTERNS}

    for name, pattern in PATTERNS.items():
        m = re.search(pattern, text)
        result[name] = int(m.group(1)) if m else None

    return result


def main():
    args = parse_args()
    llm = BlabladorClient(args.judge_model, args.api_key, timeout=args.timeout)

    if args.list_models:
        try:
            models = llm.list_models()
            print(f"API reachable. {len(models)} models/aliases visible:")
            for model in models:
                print(model)
        except Exception as e:
            print(f"[ERROR] Model-list request failed ({type(e).__name__}): {e}")
            raise SystemExit(2)
        return

    if args.ping:
        try:
            print(f"Pinging model {args.judge_model!r} ...")
            print(f"Response: {llm.ping()!r}")
        except Exception as e:
            status = getattr(e, "status_code", None)
            print(f"[ERROR] Ping failed ({type(e).__name__}, status={status}): {e}")
            raise SystemExit(2)
        return

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    model_summary = []
    json_files = sorted(input_dir.glob("*.json"))
    for json_file in tqdm(json_files, desc="Models"):
        model_name = json_file.stem
        print(f"Evaluating {model_name}")
        data = json.loads(json_file.read_text())
        if args.limit is not None:
            data = data[:args.limit]

        rows = []
        invalid_outputs = 0
        for sample in tqdm(data, desc=f"{model_name}", leave=False):
            response = None
            scores_are_valid = None
            scores = None

            for attempt in range(MAX_RETRIES):
                response = evaluate(llm, sample["source_code"], sample["generated_summary"])

                print("\n--- RAW JUDGE RESPONSE ---")
                print(response)
                print("--- END JUDGE RESPONSE ---\n")

                scores = parse_scores(response)
                print("Parsed scores:", scores)
                if args.sleep_between:
                    time.sleep(args.sleep_between)

                if valid_scores(scores):
                    scores_are_valid = True
                    break

            if not scores_are_valid:
                invalid_outputs += 1
                print(
                    f"[WARNING] Failed to parse scores for "
                    f"{sample['cve_id']} after {MAX_RETRIES} attempts."
                )

            rows.append({
                "cve_id": sample["cve_id"],
                **scores,
                "judge_response": response,
            })

        df = pd.DataFrame(rows)
        df.to_csv(
            output_dir / f"{model_name}_judge_scores.csv",
            index=False,
        )

        model_summary.append({
            "model": model_name,
            "faithfulness": df.faithfulness.mean(),
            "coverage": df.coverage.mean(),
            "retrieval": df.retrieval.mean(),
            "conciseness": df.conciseness.mean(),
            "clarity": df.clarity.mean(),

            "num_samples": len(df),
            "invalid_outputs": invalid_outputs,
        })

    pd.DataFrame(model_summary).to_csv(output_dir / "summary.csv",index=False)


if __name__ == "__main__":
    main()