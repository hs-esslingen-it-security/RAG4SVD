import argparse
import json

# map from "shortcut" model names to full model identifiers
_MODEL_DICT_LLM = {
    'phi-3-mini-128k': ('microsoft/Phi-3-mini-128k-instruct', 131072),
    'phi-3.5-mini-instruct': ('microsoft/Phi-3.5-mini-instruct', 131072),
    'phi-4': ('microsoft/phi-4', 16384),
    'phi-4-mini-instruct': ('microsoft/Phi-4-mini-instruct', 131072),
    'phi-4-reasoning': ('microsoft/Phi-4-reasoning', 32768),
    'phi-4-mini-reasoning': ('microsoft/Phi-4-mini-reasoning', 131072),
    'nextcoder-7b': ('microsoft/NextCoder-7B', 32768),
    'nextcoder-14b': ('microsoft/NextCoder-14B', 32768),
    'nextcoder-32b': ('microsoft/NextCoder-32B', 32768),
    
    'qwen2.5-coder-32b-instruct': ('Qwen/Qwen2.5-Coder-32B-Instruct', 32768),
    'qwen2.5-coder-14b-instruct': ('Qwen/Qwen2.5-Coder-14B-Instruct', 32768),
    'qwen2.5-coder-7b-instruct': ('Qwen/Qwen2.5-Coder-7B-Instruct', 32768),
    'qwen2.5-coder-3b-instruct': ('Qwen/Qwen2.5-Coder-3B-Instruct', 32768),
    'qwen2.5-32b-instruct': ('Qwen/Qwen2.5-32B-Instruct', 32768),
    'qwen2.5-14b-instruct': ('Qwen/Qwen2.5-14B-Instruct', 32768),
    'qwen2.5-7b-instruct': ('Qwen/Qwen2.5-7B-Instruct', 32768),
    'qwen2.5-3b-instruct': ('Qwen/Qwen2.5-3B-Instruct', 32768),
    'qwq-32b': ('Qwen/QwQ-32B', 131072),
    'qwen3-coder-30b-instruct': ('Qwen/Qwen3-Coder-30B-A3B-Instruct', 262144),
    'qwen3-30b-instruct': ('Qwen/Qwen3-30B-A3B-Instruct-2507', 131072),
    'qwen3-14b-instruct': ('Qwen/Qwen3-14B', 32768),
    'qwen3-8b-instruct': ('Qwen/Qwen3-8B', 131072),
    'qwen3-4b-instruct': ('Qwen/Qwen3-4B', 32768),
    'qwen3.5-9b': ('Qwen/Qwen3.5-9B', 262144),
    'qwen3.5-27b': ('Qwen/Qwen3.5-27B', 262144),
    'qwen3.6-27b': ('Qwen/Qwen3.6-27B', 262144),

    'deepseek-coder-v2-16b-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct', 128000),
    'deepseek-coder-6.7b-instruct': ('deepseek-ai/deepseek-coder-6.7b-instruct', 16384),
    'deepseek-coder-33b-instruct': ('deepseek-ai/deepseek-coder-33b-instruct', 16384),
    'deepseek-v2-16b': ('deepseek-ai/DeepSeek-V2-Lite', 32768),
    'deepseek-r1-7b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', 131072),
    'deepseek-r1-8b': ('deepseek-ai/DeepSeek-R1-Distill-Llama-8B', 131072),
    'deepseek-r1-14b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-14B', 131072),
    'deepseek-r1-32b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 131072),

    'codellama-7b-instruct': ('codellama/CodeLlama-7b-Instruct-hf', 16384),
    'codellama-13b-instruct': ('codellama/CodeLlama-13b-Instruct-hf', 16384),
    'codellama-34b-instruct': ('codellama/CodeLlama-34b-Instruct-hf', 16384),
    'llama3.2-1b-instruct': ('meta-llama/Llama-3.2-1B-Instruct', 131072),
    'llama3.2-3b-instruct': ('meta-llama/Llama-3.2-3B-Instruct', 131072),
    'llama3.1-8b-instruct': ('meta-llama/Llama-3.1-8B-Instruct', 131072),
    'llama3-8b-instruct': ('meta-llama/Meta-Llama-3-8B-Instruct', 8192),

    'gemma-2-2b-it': ('google/gemma-2-2b-it', 8192),
    'gemma-2-9b-it': ('google/gemma-2-9b-it', 8192),
    'gemma-2-27b-it': ('google/gemma-2-27b-it', 8192),
    'gemma-3-4b-it': ('google/gemma-3-4b-it', 131072),
    'gemma-3-12b-it': ('google/gemma-3-12b-it', 131072),
    'gemma-3-27b-it': ('google/gemma-3-27b-it', 131072),
    'gemma-4-31b-it': ('google/gemma-4-31B-it', 262144),
    't5gemma-2-4b': ('google/t5gemma-2-4b-4b', 131072),

    'mistral-7b-instruct-v0.3': ('mistralai/Mistral-7B-Instruct-v0.3', 32768),
    'devstral-small-2-24b-instruct': ('mistralai/Devstral-Small-2-24B-Instruct-2512', 262144),
    'mistral-3-8b-instruct': ('mistralai/Ministral-3-8B-Instruct-2512', 262144),
    'mistral-3-14b-instruct': ('mistralai/Ministral-3-14B-Instruct-2512', 262144),
    'mistral-3-3b-instruct': ('mistralai/Ministral-3-3B-Instruct-2512', 262144),
}

def get_config(args):
    """
    Parses command-line arguments and loads configuration from a JSON file.
    Returns a dictionary with configuration values.
    """
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--config', type=str, default='config.json', help='Path to config file')
    # parser.add_argument('--db_name', type=str, help='Database name to use (overrides config)')
    # args = parser.parse_args()

    # Load config file
    with open(args.config, 'r') as f:
        config = json.load(f)

    # override with command-line argument if provided
    if args.db_name:
        config['db_name'] = args.db_name
    elif 'db_name' not in config:
        config['db_name'] = 'bigvul' # Default fallback

    # select model
    selected_model = args.model if args.model else config.get('model', 'llama3.1-8b-instruct')
    # translate short name to full identifier using the dictionary
    if selected_model in _MODEL_DICT_LLM:
        full_identifier, context_length = _MODEL_DICT_LLM[selected_model]
        print(selected_model, " ", full_identifier)
        config['model'] = full_identifier
        #config['model_max_context'] = context_length  
        #config['model_short_name'] = selected_model   
    else:
        # If not in dictionary, assume the user passed a full HF path directly
        config['model'] = selected_model

    return config

# def get_config():
#     """
#     Parses command-line arguments and loads configuration from a JSON file.
#     Returns a dictionary with configuration values.
#     """
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--config', type=str, default='config.json', help='Path to config file')
#     parser.add_argument('--db_name', type=str, help='Database name to use (overrides config)')
#     args = parser.parse_args()

#     # Load config file
#     with open(args.config, 'r') as f:
#         config = json.load(f)

#     # Override with command-line argument if provided
#     if args.db_name:
#         config['db_name'] = args.db_name
#     else:
#         config['db_name'] = config.get('db_name', 'bigvul')

#     return config
