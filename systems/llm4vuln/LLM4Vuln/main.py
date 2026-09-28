import argparse
import json
import os
import gc, torch
from config import all_supported_language # OPENAI_API_KEY, REPLICATE_API_TOKEN, 
import rich
from logging import WARNING
import richuru
from importlib import import_module
from models.utils_model import *
import logging
# logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

console = rich.get_console()
richuru.install(level=WARNING, rich_console=console)

# transfer OPENAI/REPLICATE implementation to open source one in llm4vuln/models/utils_model.py
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


def cli_parse():
    parser = argparse.ArgumentParser(description="LLM4Vuln")
    parser.add_argument("--model", type=str, nargs="+",
                        help="Specify one or more models to use for the evaluation (space-separated)")  # e.g. --model llama3 phi3 deepseek
    parser.add_argument("--summary", type=str,  
                        help="Specify the summary model to use for knowledge retrieval")
    parser.add_argument("--embedding", type=str, default="codebert-base",  
                        help="Specify the embedding model to use for knowledge retrieval")
    parser.add_argument("--gt", type=str, default="qwen2.5-7b-instruct",
                        help="Specify the ground truth model to use for evaluating the model responses")
    parser.add_argument("--all", action="store_true",
                        help="Run all the evaluation")
    parser.add_argument("--output", type=str,
                        help="Output the result to a file")
    parser.add_argument("--dataset-dir", type=str, default=None,
                        help="Optional dataset directory override for the evaluation")
    parser.add_argument("--language", type=str, choices=all_supported_language,
                        help="Optional single language to evaluate")
    parser.add_argument("--primevul", action="store_true",
                        help="Use the PrimeVul C++ dataset (dataset/cpp_primevul) and only cpp language")
    
    # parser.add_argument("--language", type=str,
    #                    help="Specify the language to use for the evaluation")
    # parser.add_argument("--latex-table", type=str,
    #                     help="Output the result to a latex table")
    # parser.add_argument("--script", type=str,
    #                     help="Specify the script to run before the evaluation")
    # parser.add_argument("--script-only", action="store_true",
    #                     help="Only run the script")
    # parser.add_argument("--regenerate-table", type=str, help="Regenerate the table from a given middle result json. Should be used with --latex-table for output and --output for json output and --language for language")

    return parser.parse_args()


def main():
    args = cli_parse()
    console.print(f"Model: {args.model}")
    if args.primevul:
        if args.language is not None and args.language != "cpp":
            raise ValueError("--primevul can only be used with cpp; do not pass --language java")
        args.language = "cpp"
        if args.dataset_dir is None:
            args.dataset_dir = os.path.join("dataset", "cpp_primevul")
        console.print("PrimeVul dataset enabled: dataset/cpp_primevul")

    if args.language is not None:
        console.print(f"Language: {args.language}")
        languages = [args.language]
    else:
        console.print(f"Language: Java, C++")
        languages = all_supported_language
    # if args.latex_table is not None:
    #     console.print(f"Latex Table: {args.latex_table}")

    # init registry
    from registry import _init
    _init() # inits _global_dict = { "dataloader": {}, "knowledgeloader": {} }
    # load all modules
    import dataloader
    import knowledge
    from evaluator import Evaluator

    from models.utils_model import _init as init_models
    init_models(args.summary, args.embedding, args.gt) # check duplicates; only one instance

    run_config = {
        "summary_model": args.summary,
        "gt_model": args.gt,
        "embedding_model": args.embedding
    }

    # if args.regenerate_table: # latex table with different format; not reproducible for us
    #     with open(args.regenerate_table, "r") as f:
    #         middle_result = json.load(f)
    #     evaluator = Evaluator(args.language)
    #     evaluator.regenerate_table(middle_result)
    #     if args.latex_table is not None:
    #         with open(args.latex_table, "w") as f:
    #             f.write(evaluator.result.to_latex_table_f1())
    #     if args.output is not None:
    #         with open(args.output, "w") as f:
    #             json.dump(evaluator.result.to_json(), f)

    # if args.script is not None:
    #     # run the script
    #     module = import_module("scripts." + args.script, "scripts")
    #     module.run()
    # if args.script_only:
    #     return

    if args.all:
        for language in languages:
            evaluator = Evaluator(language, run_config, dataset_base=args.dataset_dir)
            evaluator.evaluate({"models": args.model}) # ["gpt-35-turbo", "gpt-4-turbo", "phi3", "llama3"] 
            console.print_json(data=evaluator.result.to_json())
            run_id = evaluator.run_id

            if args.output is not None:
                with open(args.output+"_"+language+"_"+run_id+".json", "w") as f:
                    json.dump(evaluator.result.to_json(), f)
                with open(args.output+"_"+language+"_"+run_id+"_middle_result.json", "w") as f:
                    json.dump(evaluator.middle_result, f)
    else:
        for language in languages:
            evaluator = Evaluator(language, run_config, dataset_base=args.dataset_dir)
            evaluator.evaluate({"models": args.model,
                                "prompt_scheme": [
                                    "PreCoTSchemePrompt",
                                    "SummarizedKnowledgePrompt",
                                    "WithoutContextPrompt"
                                ] # "RawSchemePrompt", "NoKnowledgePrompt", "OriginalKnowledgePrompt", "WithContextPrompt"
            })
            console.print_json(data=evaluator.result.to_json())
            run_id = evaluator.run_id

            if args.output is not None:
                with open(args.output+"_"+language+"_"+run_id+".json", "w") as f:
                        json.dump(evaluator.result.to_json(), f)
                with open(args.output+"_"+language+"_"+run_id+"_middle_result.json", "w") as f:
                        json.dump(evaluator.middle_result, f)


if __name__ == '__main__':
    main()
