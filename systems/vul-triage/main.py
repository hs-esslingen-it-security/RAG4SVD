import re
import json
import argparse
import torch
import numpy as np
import random
from control_flow.control_flow.vuln_flow_analyzer import analyze_code_str
from retrieval import search_by_query, parse_cwe_xml, get_weakness_by_id
from tqdm import tqdm
from metrics_tracker import VulnerabilityMetricsTracker
from llm_client import get_llm_client, remove_thinking

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)
    # If using the HPC later:
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(42)

user_prompt1 = (
    "You are a senior software engineer and static code analyst.\n"
    "Your task is to understand the functionality of the given source code.\n\n"

    "Instructions:\n"
    "1. Carefully analyze the code to determine its main functionality.\n"
    "2. Identify important operations such as input handling, memory operations, file operations, or system calls.\n"
    "3. Describe how data flows through the program when possible.\n"
    "4. Think through the logic internally step-by-step, but DO NOT output your reasoning process.\n"
    "5. Only describe behavior that can be directly inferred from the code.\n"
    "6. Do NOT speculate about functionality that is not visible in the code.\n"
    "7. Do NOT repeat or quote the code.\n"
    "8. Do NOT use markdown, bullet points, or special formatting.\n"
    "9. Keep the summary concise and factual.\n\n"

    "If the code is incomplete or unclear, describe only the observable behavior rather than guessing the intended functionality.\n\n"
)

user_prompt2 = (
    "You are a senior application security expert and professional code auditor. "
    "Your task is to analyze the provided source code and identify realistic security vulnerabilities.\n\n"

    "Instructions:\n"
    "1. Carefully analyze the target code.\n"
    "2. Identify vulnerabilities that are realistically present or highly likely.\n"
    "3. Think step-by-step internally, but do NOT output your reasoning process.\n"
    "4. You may report AT MOST TWO vulnerability types.\n"
    "5. If only one vulnerability exists, report only one.\n"
    "6. If no vulnerabilities are found, output: 'No'\n"
    "7. You should be bold in predicting code vulnerabilities.\n\n"

    "Output Format (STRICT):\n"
    "1. Vulnerability Type: Description of the vulnerability type (describe the general vulnerability concept only, do NOT reference the specific code).\n"
    "2. Vulnerability Type: Description of the vulnerability type.\n\n"

    "Rules:\n"
    "- Maximum of TWO vulnerabilities.\n"
    "- The description should explain the vulnerability class in general terms.\n"
    "- Do not reference specific variables, functions, or code snippets.\n"
    "- Do not include reasoning or analysis steps.\n\n"
)

VULN_DETECTION_PROMPT = """
You are a senior software security auditor specializing in static code analysis and vulnerability detection.
Your task is to compare the two pieces of code and their respective auxiliary information, and then determine whether there are any vulnerabilities in the codes.
Fully scan all vulnerabilities, including high, medium, and low, without missing any known vulnerability patterns.

-----------------------------------------------
Input Description
-----------------------------------------------

{Code-1}
[Source Code]
The target source code to analyze.

[Source Code Description]
A high-level explanation of the code logic.

[Static Structural Information]
Static analysis results such as control flow graph, call graph, and structural features.

[Possible Vulnerability Description and Example]
A description of a possible vulnerability pattern and example vulnerable code.

{Code-2}
The type of content is the same as that of Code-1.

-----------------------------------------------
Internal Analysis Procedure (DO NOT OUTPUT)
-----------------------------------------------

1. Understand the functionality and purpose of the source code.
2. Identify potential security-sensitive operations (memory operations, system calls, input handling).
3. Trace possible data flows from external inputs to sensitive operations.
4. Determine whether any input validation, sanitization, or boundary checks exist.

-----------------------------------------------
Critical Reasoning Rules (DO NOT OUTPUT)
-----------------------------------------------

1. As long as there is a little bit of security risk, unsafe, must be determined as a vulnerability.
2. The output consists of two lines. The first line is the judgment of Code-1, and the second line is the judgment of Code-2. Both should only contain 'Yes' or 'No'.
3. Do NOT use markdown, bullet points, or special formatting.
4. Key checks: SQL injection, XSS, command injection, ultra vires, buffer overflow, null pointer, unvalidated input, weak encryption scheme, permission issues.
5. Don't leave out any possible code vulnerabilities, because they can lead to unexpected losses.

-----------------------------------------------
Output Format (STRICT)
-----------------------------------------------

Yes/No (for Code-1)
Yes/No (for Code-2)
"""


def get_or_create_model_client(model_cache, model_name):
    if model_name not in model_cache:
        model_cache[model_name] = get_llm_client(model_name)
    return model_cache[model_name]


def call_gpt(prompt, client):
    response = client.generate_text(
        prompt,
        model_settings={"do_sample": False},
    )
    return remove_thinking(response).strip()


def process_string_to_array(raw_str: str) -> list:
    """
    Remove leading line numbers and convert the string into a line-by-line list.

    :param raw_str: Original numbered string
    :return: Cleaned list of strings (one element per line, excluding empty lines)
    """
    lines = raw_str.split('\n')

    pattern = re.compile(r'^\d+.\s*')

    result = []
    for line in lines:
        cleaned_line = pattern.sub('', line).strip()
        if cleaned_line:
            result.append(cleaned_line)

    return result


def read_jsonl_iteratively(file_path):
    """
    Iteratively read a JSONL file and return the target and func fields
    for every two records.

    :param file_path: Path to the JSONL file
    :yield: Tuple containing two dictionaries, each with target and func
    """
    buffer = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                result = {
                    "target": data.get("target"),
                    "func": data.get("func")
                }
                buffer.append(result)

                if len(buffer) == 2:
                    yield buffer[0], buffer[1]
                    buffer = []

            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON on line {line_num}: {e}")
                continue

        if len(buffer) == 1:
            print("Warning: One unpaired record remains at the end of the file")


def count_lines_in_jsonl(file_path):
    """
    Count the number of valid (non-empty) lines in a JSONL file.

    :param file_path: Path to the file
    :return: Number of valid lines
    """
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def get_knowledge(query_content):
    knowledge = ''
    if query_content == "No":
        knowledge += "No obvious vulnerabilities were initially found. Further analysis of potential vulnerabilities is required."
        print("No potential vulnerabilities found; no query generated.")
    else:
        query_array = process_string_to_array(query_content)
        order = 1
        id_list = []
        for query in query_array:
            query_result = search_by_query(query, top_k=1)

            for ID, score in query_result:
                if ID in id_list:
                    continue
                else:
                    id_list.append(ID)
                XML_FILE = "cwec_latest.xml/cwec_v4.19.1.xml"
                weakness_dict = parse_cwe_xml(XML_FILE)
                result = get_weakness_by_id(weakness_dict, ID)

                if result:
                    code = ""
                    for segment in result['Bad_Example_Code']:
                        code += segment

                    knowledge = knowledge + "\n" + str(order) + "、" + result['Name'] + "：" + result[
                        'Description'] \
                                + " Examples of Vulnerable Code:" + code
                    order += 1
    return knowledge


def sanitize_prediction_output(output_text: str) -> str:
    """
    Normalize LLM output before Yes/No parsing.

    Removes:
    - <think>...</think> blocks
    - leading/trailing whitespace
    - empty lines
    - markdown fences
    - accidental spaces around answers
    """
    output_text = remove_thinking(output_text)
    # Remove markdown artifacts
    output_text = output_text.replace("```", "")
    # Normalize whitespace
    lines = [line.strip() for line in output_text.splitlines() if line.strip()]

    return "\n".join(lines)

def extract_preds(output_text):
    """
    Extract prediction labels from the model output.

    :param output_text: Input text containing exactly two lines,
                        each being Yes/No (case- and whitespace-insensitive)
    :return: List containing two labels [label_code1, label_code2]
    """
    # matches = re.findall(r"\b(Yes|No)\b", output_text, re.I)
    # if len(matches) >= 2:
    #     matches = matches[:2]
    #lines = [line.strip() for line in output_text.split('\n') if line.strip()]
    
    output_text = sanitize_prediction_output(output_text)
    lines = output_text.splitlines()

    if len(lines) != 2:
        raise ValueError("The input must contain exactly two valid lines (Yes/No).")

    labels = []
    for line in lines:
        lower_line = line.lower().strip()
        if lower_line == 'yes':
            labels.append(1)
        elif lower_line == 'no':
            labels.append(0)
        else:
            raise ValueError(f"Invalid prediction value: {line}. Only Yes/No are supported.")

    return labels


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run vulnerability detection with ablation study')
    parser.add_argument('--wotask', type=str, default='all',
                        choices=['all', 'wo_ctrl_info_pth', 'wo_rag_pth', 'wo_exp_pth', 'nan'],
                        help='Ablation mode: all (all modules), wo_ctrl_info_pth (without control flow), '
                             'wo_rag_pth (without RAG), wo_exp_pth (without code understanding), '
                             'nan (without any auxiliary info)')
    parser.add_argument('--mode', type=str, default='pairwise', choices=['pairwise', 'single'],
                        help='Evaluation mode: pairwise or single')
    parser.add_argument('--jsonl_file', type=str, default='primevul_test_paired.jsonl',
                        help='Path to JSONL file')
    parser.add_argument('--metrics_file', type=str, default='metrics_log.txt',
                        help='Output file for real-time metrics logging')
    parser.add_argument('--summary_model', type=str, default='qwen2.5-coder-3b-instruct',
                        help='Hugging Face model used for code understanding')
    parser.add_argument('--rag_model', type=str, default='qwen2.5-coder-3b-instruct',
                        help='Hugging Face model used for RAG query generation')
    parser.add_argument('--detection_model', type=str, default='qwen2.5-coder-3b-instruct',
                        help='Hugging Face model used for final vulnerability detection')
    parser.add_argument('--model', type=str, default=None,
                        help='Optional shared model name for all three roles; overrides the per-role flags when set')

    args = parser.parse_args()

    if args.model:
        summary_model = rag_model = detection_model = args.model
    else:
        summary_model = args.summary_model
        rag_model = args.rag_model
        detection_model = args.detection_model

    model_cache = {}
    summary_client = get_or_create_model_client(model_cache, summary_model)
    rag_client = get_or_create_model_client(model_cache, rag_model)
    detection_client = get_or_create_model_client(model_cache, detection_model)

    print(f"Running in mode: {args.wotask}")
    print(f"Summary model: {summary_model}")
    print(f"RAG model: {rag_model}")
    print(f"Detection model: {detection_model}")

    jsonl_file = args.jsonl_file
    total_cases = count_lines_in_jsonl(jsonl_file)

    predictions = []
    labels = []

    metrics_tracker = VulnerabilityMetricsTracker(output_file=args.metrics_file)

    with tqdm(total=total_cases / 2, desc="Processing sample pairs", unit="item") as pbar:
        for item1, item2 in read_jsonl_iteratively(jsonl_file):
            code_content1, label1 = item1['func'], item1['target']
            code_content2, label2 = item2['func'], item2['target']
            labels.append(label1)
            labels.append(label2)

            cf_info1 = ""
            cf_info2 = ""
            understanding1 = ""
            understanding2 = ""
            knowledge1 = ""
            knowledge2 = ""

            # Native mode: skip all auxiliary modules and use only the original source code
            if args.wotask == 'nan':
                pass
            else:
                # Static structural information
                if args.wotask != 'wo_ctrl_info_pth' and code_content1 and code_content2:
                    result1 = analyze_code_str(code_content1, detail_level="C")
                    result2 = analyze_code_str(code_content2, detail_level="C")
                    cf_info1 = result1["results"]["C"]["prompt_text"]
                    cf_info2 = result2["results"]["C"]["prompt_text"]

                # Source code understanding (summary generation)
                if args.wotask != 'wo_exp_pth' and code_content1 and code_content2:
                    agent1_prompt1 = user_prompt1 + f"Target Code:\n```\n{code_content1}\n```"
                    agent1_prompt2 = user_prompt1 + f"Target Code:\n```\n{code_content2}\n```"

                    understanding1 = call_gpt(agent1_prompt1, summary_client)
                    understanding2 = call_gpt(agent1_prompt2, summary_client)

                # RAG (retrieval prompt)
                if args.wotask != 'wo_rag_pth' and code_content1 and code_content2:
                    agent2_prompt1 = user_prompt2 + f"Target Code:\n```\n{code_content1}\n```"
                    agent2_prompt2 = user_prompt2 + f"Target Code:\n```\n{code_content2}\n```"
                    query_content1 = call_gpt(agent2_prompt1, rag_client)
                    query_content2 = call_gpt(agent2_prompt2, rag_client)

                    knowledge1 = get_knowledge(query_content1)
                    knowledge2 = get_knowledge(query_content2)

            # final detection prompt
            prompt = (
                    VULN_DETECTION_PROMPT
                    + "\n\n### Input\n"
                    + "{Code-1}"
                    + "\n[Source Code]\n" + code_content1
            )

            if args.wotask != 'wo_exp_pth' and understanding1:
                prompt += "\n\n[Source Code Description]\n" + understanding1

            if args.wotask != 'wo_ctrl_info_pth' and cf_info1:
                prompt += "\n\n[Static Structural Information]" + cf_info1

            if args.wotask != 'wo_rag_pth' and knowledge1:
                prompt += "\n\n[Possible Vulnerability Description and Example]" + knowledge1

            # add the Code-2 section
            prompt += (
                    "\n\n{Code-2}"
                    + "\n[Source Code]\n" + code_content2
            )

            if args.wotask != 'wo_exp_pth' and understanding2:
                prompt += "\n\n[Source Code Description]\n" + understanding2

            if args.wotask != 'wo_ctrl_info_pth' and cf_info2:
                prompt += "\n\n[Static Structural Information]" + cf_info2

            if args.wotask != 'wo_rag_pth' and knowledge2:
                prompt += "\n\n[Possible Vulnerability Description and Example]" + knowledge2

            #inference = call_gpt(prompt, detection_client)
            inference = call_gpt([{"role": "user", "content": prompt}], detection_client)

            try:
                preds = extract_preds(inference)
                predictions += preds
                
                true_i, true_j = labels[-2], labels[-1]
                pred_i, pred_j = preds[0], preds[1]
                metrics_tracker.update_pair_metrics(pred_i, pred_j, true_i, true_j)
                print(preds)

            except ValueError as e:
                print(f"\n[!] Parsing Error on sample pair: {e}")
                print(f"[!] Raw Model Output: {repr(inference)}")
                continue
            
            pbar.update(1)

    metrics_tracker.print_summary(mode=args.mode)