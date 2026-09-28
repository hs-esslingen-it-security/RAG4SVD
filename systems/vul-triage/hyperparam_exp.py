import re
import json
import argparse

import pandas as pd

from control_flow.control_flow.vuln_flow_analyzer import analyze_code_str, analyze_code_str_no_ast, analyze_code_str_no_cfg, analyze_code_str_no_dfg
from retrieval import search_by_query, parse_cwe_xml, get_weakness_by_id
from tqdm import tqdm
from llm_client import get_llm_client, remove_thinking

#client = OpenAI(api_key="YOUR_API_KEY", base_url="https://api.poixe.com/v1")

user_prompt1_base = (
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
)

user_prompt1_concise = (
    user_prompt1_base +
    "9. Keep the summary concise and factual.\n\n"
    "If the code is incomplete or unclear, describe only the observable behavior rather than guessing the intended functionality.\n\n"
)

user_prompt1_normal = (
    user_prompt1_base +
    "\nIf the code is incomplete or unclear, describe only the observable behavior rather than guessing the intended functionality.\n\n"
)

user_prompt1_detailed = (
    user_prompt1_base +
    "9. A detailed, complete code description is required.\n\n"
    "If the code is incomplete or unclear, describe only the observable behavior rather than guessing the intended functionality.\n\n"
)

user_prompt2_max2 = (
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

user_prompt2_max4 = (
    "You are a senior application security expert and professional code auditor. "
    "Your task is to analyze the provided source code and identify realistic security vulnerabilities.\n\n"

    "Instructions:\n"
    "1. Carefully analyze the target code.\n"
    "2. Identify vulnerabilities that are realistically present or highly likely.\n"
    "3. Think step-by-step internally, but do NOT output your reasoning process.\n"
    "4. You may report AT MOST FOUR vulnerability types.\n"
    "5. If only one vulnerability exists, report only one.\n"
    "6. If no vulnerabilities are found, output: 'No'\n"
    "7. You should be bold in predicting code vulnerabilities.\n\n"

    "Output Format (STRICT):\n"
    "1. Vulnerability Type: Description of the vulnerability type (describe the general vulnerability concept only, do NOT reference the specific code).\n"
    "2. Vulnerability Type: Description of the vulnerability type.\n"
    "3. ...\n\n"

    "Rules:\n"
    "- Maximum of FOUR vulnerabilities.\n"
    "- The description should explain the vulnerability class in general terms.\n"
    "- Do not reference specific variables, functions, or code snippets.\n"
    "- Do not include reasoning or analysis steps.\n\n"
)

vuln_detection_prompt_pair = """
You are a senior software security auditor specializing in static code analysis and vulnerability detection.
Your task is to compare the two pieces of code and their respective auxiliary information, and then determine whether there are any vulnerabilities in the codes.
Fully scan all vulnerabilities, including high, medium, and low, without missing any known vulnerability patterns.

-----------------
Input Description
-----------------

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

-----------------
Internal Analysis Procedure (DO NOT OUTPUT)
-----------------

1. Understand the functionality and purpose of the source code.
2. Identify potential security-sensitive operations (memory operations, system calls, input handling).
3. Trace possible data flows from external inputs to sensitive operations.
4. Determine whether any input validation, sanitization, or boundary checks exist.

-----------------
Critical Reasoning Rules (DO NOT OUTPUT)
-----------------

1. As long as there is a little bit of security risk, unsafe, must be determined as a vulnerability.
2. The output consists of two lines. The first line is the judgment of Code-1, and the second line is the judgment of Code-2. Both should only contain 'Yes' or 'No'.
3. Do NOT use markdown, bullet points, or special formatting.
4. Key checks: SQL injection, XSS, command injection, ultra vires, buffer overflow, null pointer, unvalidated input, weak encryption scheme, permission issues.
5. Don't leave out any possible code vulnerabilities, because they can lead to unexpected losses.

-----------------
Output Format (STRICT)
-----------------

Yes/No (for Code-1)
Yes/No (for Code-2)
"""

vuln_detection_prompt_single = """
You are a senior kotlin software security auditor specializing in static code analysis and vulnerability detection.
Your task is to determine whether the given source code contains vulnerabilities.
The code to be tested is used in security scenarios:anti-attack, anti-spider, interface rate limiting and delay, etc.
Don't leave out any possible code vulnerabilities in a secure scenario, because they can lead to unexpected losses.

------------------------------------------------
Input Description
------------------------------------------------

[Source Code]
The target source code to analyze.

[Source Code Description]
A high-level explanation of the code logic.

[Static Structural Information]
Static analysis results such as control flow graph, call graph, and structural features.

[Possible Vulnerability Description and Example]
A description of a possible vulnerability pattern and example vulnerable code.

------------------------------------------------
Internal Analysis Procedure (DO NOT OUTPUT)
------------------------------------------------

1. Understand the functionality and purpose of the source code.
2. Identify potential security-sensitive operations (memory operations, system calls, input handling).
3. Trace possible data flows from external inputs to sensitive operations.
4. Fully scan all vulnerabilities, including high, medium, and low, without missing any known vulnerability patterns.

------------------------------------------------
Critical Reasoning Rules (DO NOT OUTPUT)
------------------------------------------------

1. As long as there is a little bit of security risk, unsafe, must be determined as a vulnerability.
2. Output only "Yes" or "No".
3. Do NOT use markdown, bullet points, or special formatting.
4. Key checks: SQL injection, XSS, command injection, ultra vires, buffer overflow, null pointer, unvalidated input, weak encryption scheme, permission issues.
5. For example: "private fun getRandomDelay(): Long = Random.nextLong(180, 360)" This line of code should be regarded as having a flaw because "it uses an insecure random number generator, which is predictable, unsafe, and cannot be used for defense against attacks / interface spoofing."

------------------------------------------------
Output Format (STRICT)
------------------------------------------------

Yes/No
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
    return remove_thinking(response)


def process_string_to_array(raw_str: str) -> list:
    """
    Remove leading line numbers and convert the string into a line-by-line list.

    :param raw_str: Original numbered string
    :return: Cleaned list of strings (one element per line, excluding empty lines)
    """

    # Step 1: Split the string into individual lines
    lines = raw_str.split('\n')

    # Step 2: Define a regex to match leading numbers (e.g., "1.", "123.")
    # Regex explanation:
    # ^      -> beginning of the line
    # \d+    -> one or more digits
    # \.     -> literal period
    # \s*    -> optional whitespace
    pattern = re.compile(r'^\d+\.\s*')

    # Step 3: Remove numbering and filter out empty lines
    result = []
    for line in lines:
        cleaned_line = pattern.sub('', line).strip()
        if cleaned_line:
            result.append(cleaned_line)

    return result


def read_jsonl_iteratively(file_path):
    """
    Iteratively read a JSONL file and return the target and func fields
    for every pair of records.

    :param file_path: Path to the JSONL file
    :yield: A tuple containing two dictionaries, each with target and func
    """
    buffer = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Skip empty lines
            line = line.strip()
            if not line:
                continue

            try:
                # Parse a single JSON object
                data = json.loads(line)
                # Extract the target and func fields (returns None if absent)
                result = {
                    "target": data.get("target"),
                    "func": data.get("func")
                }
                buffer.append(result)

                # Yield two records once the buffer contains a pair
                if len(buffer) == 2:
                    yield buffer[0], buffer[1]
                    buffer = []

            except json.JSONDecodeError as e:
                 # Catch JSON parsing errors without interrupting the program
                print(f"Failed to parse JSON on line {line_num}: {e}")
                continue

        # Handle the remaining record if the total number of records is odd
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
        knowledge += "No obvious vulnerabilities were initially found.Further analysis of potential vulnerabilities is required."
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
                # Parse the XML file and build the CWE mapping
                weakness_dict = parse_cwe_xml(XML_FILE)
                # Retrieve weakness information by ID
                result = get_weakness_by_id(weakness_dict, ID)

                if result:
                    code = ""
                    for segment in result['Bad_Example_Code']:
                        code += segment

                    knowledge = (
                        knowledge
                        + f"\n{order}. {result['Name']}: "
                        + result['Description']
                        + " Examples of Vulnerable Code: "
                        + code
                    )
                    order += 1
    return knowledge


def extract_preds(output_text):
    """
    Extract prediction labels from the model output.

    :param output_text:
        Input text containing exactly two lines,
        each being Yes/No (case- and whitespace-insensitive)

    :return:
        List containing two labels:
        [label_code1, label_code2]
    """

    # Split into lines, remove empty lines, and strip whitespace
    lines = [line.strip() for line in output_text.split('\n') if line.strip()]

    
    # Ensure exactly two valid lines are present
    if len(lines) != 2:
        raise ValueError("The input must contain exactly two valid lines (Yes/No).")
    labels = []
    for line in lines:
        lower_line = line.lower()
        if lower_line == 'yes':
            labels.append(1)
        elif lower_line == 'no':
            labels.append(0)
        else:
            raise ValueError(f"Invalid prediction value: {line}. Only Yes/No are supported.")

    return labels


def calculate_metrics(predictions, labels):
    """
    Compute vulnerability detection evaluation metrics.

    Args:
        predictions: List of predicted labels.
        labels: List of ground-truth labels.

    Returns:
        Dictionary containing all evaluation metrics.
    """
    print("\n--- Evaluation Metrics ---")

    n = len(predictions)
    p_c = 0
    p_v = 0
    p_b = 0
    p_r = 0
    e = 0
    tn = 0
    fp = 0
    fn = 0
    tp = 0

    for i in range(0, n, 2):
        pred_i, pred_j = predictions[i], predictions[i + 1]
        true_i, true_j = labels[i], labels[i + 1]
        if pred_i == true_i and pred_j == true_j:
            p_c += 1
        if pred_i == 1 and pred_j == 1:
            p_v += 1
        if pred_i == 0 and pred_j == 0:
            p_b += 1
        if pred_i != true_i and pred_j != true_j:
            p_r += 1
        if pred_i != true_i or pred_j != true_j:
            e += 1

    for pred, true in zip(predictions, labels):
        if true == 1 and pred == 1:
            tp += 1
        elif true == 0 and pred == 1:
            fp += 1
        elif true == 0 and pred == 0:
            tn += 1
        elif true == 1 and pred == 0:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    print(f"P-C : {p_c:.4f}")
    print(f"P-V : {p_v:.4f}")
    print(f"P-B : {p_b:.4f}")
    print(f"P-R : {p_r:.4f}")
    print(f"E : {e:.4f}")
    print(f"\nPrecision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"FPR (False Positive Rate): {fpr:.4f}")

    return {
        'P_C': p_c,
        'P_V': p_v,
        'P_B': p_b,
        'P_R': p_r,
        'E': e,
        'Precision': precision,
        'Recall': recall,
        'FPR': fpr
    }

def evaluate_jsonl_file_pair_wise(jsonl_file="primevul_train_paired_cur.jsonl", detail_level="C", info_comb="all", desc_level="concise", max_vuln=2, summary_model="qwen2.5-coder-3b-instruct", rag_model="qwen2.5-coder-3b-instruct", detection_model="qwen2.5-coder-3b-instruct"):
    """
    Evaluate the vulnerability detection model on a JSONL dataset.

    Args:
        jsonl_file: Path to the JSONL file.

    Returns:
        Dictionary containing all evaluation metrics.
    """
    total_cases = count_lines_in_jsonl(jsonl_file)

    predictions = []
    labels = []
    model_cache = {}
    summary_client = get_or_create_model_client(model_cache, summary_model)
    rag_client = get_or_create_model_client(model_cache, rag_model)
    detection_client = get_or_create_model_client(model_cache, detection_model)
    with tqdm(total=total_cases / 2, desc="Processing sample pairs", unit="item") as pbar:
        for item1, item2 in read_jsonl_iteratively(jsonl_file):
            code_content1, label1 = item1['func'], item1['target']
            code_content2, label2 = item2['func'], item2['target']
            labels.append(label1)
            labels.append(label2)

            if code_content1 and code_content2:
                # Generate static structural information
                if info_comb == "all":
                    analyze_code = analyze_code_str
                elif info_comb == "no_ast":
                    analyze_code = analyze_code_str_no_ast
                elif info_comb == "no_cfg":
                    analyze_code = analyze_code_str_no_cfg
                elif info_comb == "no_dfg":
                    analyze_code = analyze_code_str_no_dfg

                result1 = analyze_code(code_content1, detail_level=detail_level)
                result2 = analyze_code(code_content2, detail_level=detail_level)
                cf_info1 = result1["results"][detail_level]["prompt_text"]
                cf_info2 = result2["results"][detail_level]["prompt_text"]

                if desc_level == "concise":
                    user_prompt1 = user_prompt1_concise
                elif desc_level == "normal":
                    user_prompt1 = user_prompt1_normal
                elif desc_level == "detailed":
                    user_prompt1 = user_prompt1_detailed

                agent1_prompt1 = user_prompt1 + f"Target Code:\n```\n{code_content1}\n```"
                agent1_prompt2 = user_prompt1 + f"Target Code:\n```\n{code_content2}\n```"

                understanding1 = call_gpt(agent1_prompt1, summary_client)
                understanding2 = call_gpt(agent1_prompt2, summary_client)

                if max_vuln == 2:
                    user_prompt2 = user_prompt2_max2
                elif max_vuln == 4:
                    user_prompt2 = user_prompt2_max4

                agent2_prompt1 = user_prompt2 + f"Target Code:\n```\n{code_content1}\n```"
                agent2_prompt2 = user_prompt2 + f"Target Code:\n```\n{code_content2}\n```"
                query_content1 = call_gpt(agent2_prompt1, rag_client)
                query_content2 = call_gpt(agent2_prompt2, rag_client)

                knowledge1 = get_knowledge(query_content1)
                knowledge2 = get_knowledge(query_content2)

                prompt = (
                        vuln_detection_prompt_pair
                        + "\n\n### Input\n"
                        + "{Code-1}"
                        + "\n[Source Code]\n" + code_content1
                        + "\n\n[Source Code Description]\n" + understanding1
                        + "\n\n[Static Structural Information]" + cf_info1
                        + "\n\n[Possible Vulnerability Description and Example]" + knowledge1
                        + "\n\n{Code-2}"
                        + "\n[Source Code]\n" + code_content2
                        + "\n\n[Source Code Description]\n" + understanding2
                        + "\n\n[Static Structural Information]" + cf_info2
                        + "\n\n[Possible Vulnerability Description and Example]" + knowledge2
                )

                inference = call_gpt(prompt, detection_client)
                # print("\n>>>" + inference)
                preds = extract_preds(inference)
                predictions += preds
                print(preds)

            pbar.update(1)

    return calculate_metrics(predictions, labels)


def evaluate_csv_file_single_wise(csv_file, summary_model="qwen2.5-coder-3b-instruct", rag_model="qwen2.5-coder-3b-instruct", detection_model="qwen2.5-coder-3b-instruct"):
    """
    Evaluate the vulnerability detection model on a CSV dataset.

    Args:
        csv_file: Path to the CSV file.

    Returns:
        Dictionary containing all evaluation metrics.
    """
    df = pd.read_csv(csv_file)

    predictions = []
    labels = []

    model_cache = {}
    summary_client = get_or_create_model_client(model_cache, summary_model)
    rag_client = get_or_create_model_client(model_cache, rag_model)
    detection_client = get_or_create_model_client(model_cache, detection_model)

    total_cases = len(df)
    with tqdm(total=total_cases, desc="Processing samples", unit="item") as pbar:
        for code_content, label in zip(df["code"], df["label"]):
            labels.append(int(label))
            if code_content:
                result = analyze_code_str(code_content, detail_level="C")
                cf_info = result["results"]["C"]["prompt_text"]

                understanding = call_gpt(user_prompt1_concise, summary_client)

                query_content = call_gpt(user_prompt2_max2, rag_client)
                knowledge = get_knowledge(query_content)

                prompt = (
                        vuln_detection_prompt_single
                        + "\n\n### Input\n"
                        + "\n[Source Code]\n" + code_content
                        + "\n\n[Source Code Description]\n" + understanding
                        + "\n\n[Static Structural Information]" + cf_info
                        + "\n\n[Possible Vulnerability Description and Example]" + knowledge
                )

                inference = call_gpt(prompt, detection_client)
                # print("\n>>>" + inference)

                if ('Yes' in inference[0:3]):
                    predictions.append(1)
                    print(1)
                else:
                    predictions.append(0)
                    print(0)

            pbar.update(1)

    return calculate_metrics(predictions, labels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Vulnerability Detection")

    parser.add_argument("--mode", type=str, default="pairwise", choices=["pairwise", "single"],
                        help="Detection mode: pairwise or single")
    parser.add_argument("--input_file", type=str, required=True,
                        help="Input file path (JSONL for pairwise, CSV for single)")
    parser.add_argument("--detail_level", type=str, default="C", choices=["C", "B", "A"],
                        help="Detail level for code analysis: C (Complete), B (Standard), A (Brief)")
    parser.add_argument("--info_comb", type=str, default="all", choices=["all", "no_ast", "no_cfg", "no_dfg"],
                        help="Information combination: all, no_ast, no_cfg, no_dfg")
    parser.add_argument("--desc_level", type=str, default="concise", choices=["concise", "normal", "detailed"],
                        help="Description level: concise, normal, detailed")
    parser.add_argument("--max_vuln", type=int, default=2, choices=[2, 4],
                        help="Maximum number of vulnerabilities to detect: 2 or 4")

    args = parser.parse_args()

    if args.mode == "pairwise":
        metrics = evaluate_jsonl_file_pair_wise(
            jsonl_file=args.input_file,
            detail_level=args.detail_level,
            info_comb=args.info_comb,
            desc_level=args.desc_level,
            max_vuln=args.max_vuln
        )
    else:
        metrics = evaluate_csv_file_single_wise(csv_file=args.input_file)