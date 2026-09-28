import os
import json
import csv
import logging
from llm_client import generate_simple_prompt, get_llm_client, parse_kv_string_to_dict

templates = {
    1: 'In the above code snippet, check for potential security vulnerabilities and decide whether the function is vulnerable. '
       'Answer with exactly one label on the first line: Vulnerable or Non-vulnerable. '
       'Do not output any other label. If you add an explanation, put it after the first line. '
       'You are now an excellent programmer.'
       'You are conducting a function vulnerability detection task for C/C++ language.',
    2: 'The node information of the function is as follows:',
    3: 'The edge information of the function is as follows:',
    4: 'Here is an example for you to learn from:'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

fh = logging.FileHandler('devignmetricsgpt4.log')
fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
fh.setFormatter(logging.Formatter(fmt))

logger.addHandler(fh)


def normalize_prediction(prediction_text):
    text = prediction_text.strip().lower()
    first_line = text.splitlines()[0].strip() if text else ""

    if first_line == "0":
        return 0
    if first_line == "1":
        return 1
    if first_line == "non-vulnerable":
        return 0
    if first_line == "vulnerable":
        return 1

    if text == "0":
        return 0
    if text == "1":
        return 1
    if "non-vulnerable" in text or "non vulnerable" in text or "not vulnerable" in text:
        return 0
    if (
        "do not appear to be any obvious security vulnerabilities" in text
        or "does not appear to have any obvious security vulnerabilities" in text
        or "there are no immediate security vulnerabilities" in text
        or "there do not appear to be any immediate security vulnerabilities" in text
        or "does not appear to be vulnerable" in text
        or "no obvious security vulnerabilities" in text
    ):
        return 0
    if "vulnerable" in text:
        return 1
    return 2


def calculate_pairwise_accuracy(prediction_records):
    pairs = {}
    for record in prediction_records:
        pair_id = record.get("pair_id")
        if not pair_id:
            continue
        pairs.setdefault(pair_id, []).append(record)

    complete_pairs = 0
    correct_pairs = 0
    incomplete_pair_groups = 0

    for samples in pairs.values():
        if len(samples) != 2:
            incomplete_pair_groups += 1
            continue

        complete_pairs += 1
        if all(sample["prediction"] == sample["target"] for sample in samples):
            correct_pairs += 1

    pairwise_accuracy = correct_pairs / complete_pairs if complete_pairs > 0 else 0
    return pairwise_accuracy, correct_pairs, complete_pairs, incomplete_pair_groups


def main():
    dataset_path = os.getenv('GRACE_DEVIGN_TEST_PATH', os.path.join('data', 'devign_test_processed.json'))
    output_path = os.getenv('GRACE_RESULTS_PATH', 'devignresultsgpt4.csv')
    model_name = os.getenv('GRACE_LLM_NAME', 'codeqwen1.5-7b-chat')
    model_settings = parse_kv_string_to_dict(os.getenv("GRACE_MODEL_SETTINGS", "temperature=0;max_new_tokens=64"))
    client = get_llm_client(model_name)

    with open(dataset_path, 'r') as f:
        data = json.load(f)

    def calculate_metrics(predictions, ground_truth):
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        true_negatives = 0

        for pred, target in zip(predictions, ground_truth):
            if pred == target == 1:
                true_positives += 1
            elif pred == target == 0:
                true_negatives += 1
            elif pred == 1 and target == 0:
                false_positives += 1
            elif pred == 0 and target == 1:
                false_negatives += 1

        if not predictions:
            return 0, 0, 0, 0
        accuracy = (true_positives + true_negatives) / len(predictions)
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        return accuracy, precision, recall, f1

    prediction_ls = []
    ground_truth = []
    rows_to_write = []
    prediction_records = []

    for row in data[0:2000]:
        if 'func' not in row or 'target' not in row:
            continue

        input_code = row['func'][:4000]
        prompt = f"{input_code}{templates[1]}"

        try:
            prediction_text = client.generate_text(
                generate_simple_prompt(prompt),
                model_settings=model_settings,
            )
        except Exception as exc:
            prediction_text = f"ERROR: {exc}"

        prediction = normalize_prediction(prediction_text)
        target = row['target']

        prediction_ls.append(prediction)
        ground_truth.append(target)
        rows_to_write.append([prediction, target, prediction_text])
        prediction_records.append({
            "pair_id": row.get("pair_id"),
            "prediction": prediction,
            "target": target,
        })

        print(prediction_ls)
        print(ground_truth)

        accuracy, precision, recall, f1 = calculate_metrics(prediction_ls, ground_truth)
        print("Accuracy:", accuracy)
        print("Precision:", precision)
        print("Recall:", recall)
        print("F1 Score:", f1)

        logger.info("Accuracy: %f", accuracy)
        logger.info("Precision: %f", precision)
        logger.info("Recall: %f", recall)
        logger.info("F1 Score: %f", f1)

    pairwise_accuracy, correct_pairs, complete_pairs, incomplete_pair_groups = calculate_pairwise_accuracy(prediction_records)
    print("Pairwise Accuracy:", pairwise_accuracy)
    print("Pairwise Correct Pairs:", correct_pairs)
    print("Pairwise Complete Pairs:", complete_pairs)
    print("Pairwise Incomplete Pair Groups:", incomplete_pair_groups)

    logger.info("Pairwise Accuracy: %f", pairwise_accuracy)
    logger.info("Pairwise Correct Pairs: %d", correct_pairs)
    logger.info("Pairwise Complete Pairs: %d", complete_pairs)
    logger.info("Pairwise Incomplete Pair Groups: %d", incomplete_pair_groups)

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Prediction', 'Groundtruth', 'RawOutput'])
        writer.writerows(rows_to_write)

if __name__ == '__main__':
    main()


