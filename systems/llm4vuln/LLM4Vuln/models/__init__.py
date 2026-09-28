# from .openai import gpt_35_turbo_model, gpt_4_turbo_model, gpt_41_nano_model, gpt_41_nano_model_random, gpt_o4_mini, gpt_41
# from .replicate import codellama_13b_model, codellama_70b_model, phi3_mini_model, llama_3_model, qwq_model, deepseek_model
# # from .ollama import qwq_model, deepseek_model

# supported = {
#     "commercial": {
#         "gpt-35-turbo": gpt_35_turbo_model,
#         "gpt-4-turbo": gpt_4_turbo_model,
#         "gpt-4.1-nano": gpt_41_nano_model,
#         "o4-mini": gpt_o4_mini,
#         "gpt-4.1": gpt_41,
#     },
#     "open-source": {
#         # "codellama-13b": codellama_13b_model,
#         # "codellama-70b": codellama_70b_model,
#         "phi3": phi3_mini_model,
#         "llama3": llama_3_model,
#         "qwq": qwq_model,
#         "deepseek": deepseek_model,
#     }
# }


# _MODEL_DICT_LLM = {
#     'codeqwen1.5-7b': ('Qwen/CodeQwen1.5-7B', 65536),
#     'codeqwen1.5-7b-chat': ('Qwen/CodeQwen1.5-7B-Chat', 65536),
#     'deepseek-coder-6.7b-base': ('deepseek-ai/deepseek-coder-6.7b-base', 16384),
#     'deepseek-coder-6.7b-instruct': ('deepseek-ai/deepseek-coder-6.7b-instruct', 16384),
#     'deepseek-coder-v2-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Instruct', 16384),
#     'codegemma-7b': ('google/codegemma-7b', 8192),
#     'codegemma-7b-it': ('google/codegemma-7b-it', 8192),
#     'starcoder2-7b': ('bigcode/starcoder2-7b', 16384),
#     'codellama-7b': ('codellama/CodeLlama-7b-hf', 16384),
#     'codellama-7b-instruct': ('codellama/CodeLlama-7b-Instruct-hf', 16384),
#     'qwen2.5-coder-32b-instruct': ('Qwen/Qwen2.5-Coder-32B-Instruct', 32768),
#     'gpt-oss-20b': ('openai/gpt-oss-20b', 8192)
# }



# supported = {
#     "open-source": {
#         'codeqwen1.5-7b': get_llm_client('codeqwen1.5-7b'),
#         'codeqwen1.5-7b-chat': get_llm_client('codeqwen1.5-7b-chat'),
#         'deepseek-coder-6.7b-base': get_llm_client('deepseek-coder-6.7b-base'),
#         'deepseek-coder-6.7b-instruct': get_llm_client('deepseek-coder-6.7b-instruct'),
#         'deepseek-coder-v2-instruct': get_llm_client('deepseek-coder-v2-instruct'),
#         'codegemma-7b': get_llm_client('codegemma-7b'),
#         'codegemma-7b-it': get_llm_client('codegemma-7b-it'),
#         'starcoder2-7b': get_llm_client('starcoder2-7b'),
#         'codellama-7b': get_llm_client('codellama-7b'),
#         'codellama-7b-instruct': get_llm_client('codellama-7b-instruct'),
#         'qwen2.5-coder-32b-instruct': get_llm_client('qwen2.5-coder-32b-instruct'),
#         'gpt-oss-20b': get_llm_client('gpt-oss-20b')
#     }
# }

supported = {
    "open-source": [
        'codeqwen1.5-7b',
        'codeqwen1.5-7b-chat',
        'deepseek-coder-6.7b-base',
        'deepseek-coder-6.7b-instruct',
        'deepseek-coder-v2-instruct',
        'codegemma-7b',
        'codegemma-7b-it',
        'starcoder2-7b',
        'codellama-7b',
        'codellama-7b-instruct',
        'qwen2.5-coder-32b-instruct',
        'qwen2.5-coder-7b-instruct'
        'qwen2.5-7b-instruct',
        'qwen2.5-3b-instruct',
        'qwen2.5-14b-instruct',
        'gpt-oss-20b',
        'phi-3-mini-128k',
        'phi-3.5-mini-instruct',
        'qwq-32b',
        'deepseek-r1-8b',
        'llama3-8b-instruct',
        'llama3.1-8b-instruct',
        'gemma-4-E4B-it',
        'gemma-2-9b-it',
        'gemma-2-27b-it',
        'mistral-7b-instruct-v0.3'
    ]
}

