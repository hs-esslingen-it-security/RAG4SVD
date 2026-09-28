import json

def run_on_json(json_file):
    with open(json_file) as f:
        data = json.load(f)
    c_better_pre = 0
    c_better_rec = 0
    c_better_f1 = 0
    total = 0
    c_higher_tp = 0
    c_higher_fp = 0
    c_higher_fn = 0
    c_higher_tn = 0
    n_higher_fpt = 0
    for model, model_data in data.items():
        for prompt, prompt_data in model_data.items():
            for knowledge, knowledge_data in prompt_data.items():
                c_pre = knowledge_data["WithContextPrompt"]["precision"]
                c_rec = knowledge_data["WithContextPrompt"]["recall"]
                c_f1 = knowledge_data["WithContextPrompt"]["f1"]
                n_pre = knowledge_data["WithoutContextPrompt"]["precision"]
                n_rec = knowledge_data["WithoutContextPrompt"]["recall"]
                n_f1 = knowledge_data["WithoutContextPrompt"]["f1"]
                if c_pre > n_pre:
                    c_better_pre += 1
                if c_rec > n_rec:
                    c_better_rec += 1
                if c_f1 > n_f1:
                    c_better_f1 += 1
                c_tp = knowledge_data["WithContextPrompt"]["TP"]
                c_fp = knowledge_data["WithContextPrompt"]["FP"]
                c_fn = knowledge_data["WithContextPrompt"]["FN"]
                c_tn = knowledge_data["WithContextPrompt"]["TN"]
                c_fpt = knowledge_data["WithContextPrompt"]["FP_type"]
                n_tp = knowledge_data["WithoutContextPrompt"]["TP"]
                n_fp = knowledge_data["WithoutContextPrompt"]["FP"]
                n_fn = knowledge_data["WithoutContextPrompt"]["FN"]
                n_tn = knowledge_data["WithoutContextPrompt"]["TN"]
                n_fpt = knowledge_data["WithoutContextPrompt"]["FP_type"]
                if c_tp > n_tp:
                    c_higher_tp += 1
                if c_fp > n_fp:
                    c_higher_fp += 1
                if c_fn > n_fn:
                    c_higher_fn += 1
                if c_tn > n_tn:
                    c_higher_tn += 1
                if c_fpt > n_fpt:
                    n_higher_fpt += 1

                total += 1
    
    print(f"File: {json_file}")
    print(f"Better precision with context prompt: {c_better_pre}")
    print(f"Better recall with context prompt: {c_better_rec}")
    print(f"Better f1 with context prompt: {c_better_f1}")
    print(f"Higher TP with context prompt: {c_higher_tp}")
    print(f"Higher FP with context prompt: {c_higher_fp}")
    print(f"Higher FN with context prompt: {c_higher_fn}")
    print(f"Higher TN with context prompt: {c_higher_tn}")
    print(f"Higher FP_type with context prompt: {n_higher_fpt}")
    print(f"Total: {total}")


def run():
    run_on_json("new_java.json")
    run_on_json("new_solidity.json")
    run_on_json("new_cpp.json")
