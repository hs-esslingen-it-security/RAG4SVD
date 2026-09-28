import argparse
import json
import re
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import sys

MAX_RETRIES = 3
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.llm_client import get_llm_client

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
    parser.add_argument("--judge-model", default="gpt-oss-120b")
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
    prompt = build_prompt(code, summary)

    response = client.generate_text(
        prompt=[{"role": "user", "content": prompt}],
    )
    return response


def parse_scores(text):
    result = {}
    for name, pattern in PATTERNS.items():
        m = re.search(pattern, text)
        if m:
            result[name] = int(m.group(1))
        else:
            result[name] = None
    return result


def main():
    args = parse_args()
    llm = get_llm_client(args.judge_model)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    print(f"Working directory: {Path.cwd()}")
    print(f"Input directory: {input_dir.resolve()}")
    print(f"Input exists: {input_dir.exists()}")
    print(f"Input is directory: {input_dir.is_dir()}")

    output_dir.mkdir(exist_ok=True)

    model_summary = []
    json_files = sorted(input_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files")

    for json_file in tqdm(json_files, desc="Models"):
        model_name = json_file.stem
        print(f"Evaluating {model_name}")
        data = json.loads(json_file.read_text())

        rows = []
        invalid_outputs = 0
        for sample in tqdm(data, desc=f"{model_name}", leave=False):
            response = None
            scores_are_valid = None
            scores = None

            for attempt in range(MAX_RETRIES):
                response = evaluate(llm, sample["source_code"], sample["generated_purpose"] + " " + sample["generated_function"])
                scores = parse_scores(response)

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
                "judge_model": args.judge_model,
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
            "judge_model": args.judge_model,
            "faithfulness": df.faithfulness.mean(),
            "coverage": df.coverage.mean(),
            "retrieval": df.retrieval.mean(),
            "conciseness": df.conciseness.mean(),
            "clarity": df.clarity.mean(),

            "num_samples": len(df),
            "invalid_outputs": invalid_outputs,
        })

    pd.DataFrame(model_summary).to_csv(output_dir / "summary.csv",index=False,)


if __name__ == "__main__":
    main()