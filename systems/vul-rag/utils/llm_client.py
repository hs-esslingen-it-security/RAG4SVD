import os
import re
import torch
import accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from typing import List, Dict, Optional, Any, Union

_MODEL_DICT_LLM = {
    'qwen2.5-coder-14b-instruct': ('Qwen/Qwen2.5-Coder-14B-Instruct', 32768),
    'qwen2.5-coder-3b-instruct': ('Qwen/Qwen2.5-Coder-3B-Instruct', 32768),
    'qwen2.5-coder-0.5b-instruct': ('Qwen/Qwen2.5-Coder-0.5B-Instruct', 32768),

    'qwen3-8b-instruct': ('Qwen/Qwen3-8B', 131072),
    'nextcoder-7b': ('microsoft/NextCoder-7B', 32768),


    'codeqwen1.5-7b': ('Qwen/CodeQwen1.5-7B', 65536),
    'codeqwen1.5-7b-chat': ('Qwen/CodeQwen1.5-7B-Chat', 65536),

    'llama3.1-8b-instruct': ('meta-llama/Llama-3.1-8B-Instruct', 131072),

    'qwen2.5-7b-instruct': ('Qwen/Qwen2.5-7B-Instruct', 32768),
    'qwen2.5-coder-7b-instruct': ('Qwen/Qwen2.5-Coder-7B-Instruct', 32768),
    'deepseek-r1-7b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', 131072),
    'olympiccoder-7b': ('open-r1/OlympicCoder-7B', 32768),

    'qwen2.5-32b-instruct': ('Qwen/Qwen2.5-32B-Instruct', 32768),
    'qwen2.5-coder-32b-instruct': ('Qwen/Qwen2.5-Coder-32B-Instruct', 32768),
    'qwq-32b': ('Qwen/QwQ-32B', 131072),
    'olympiccoder-32b': ('open-r1/OlympicCoder-32B', 32768),

    'deepseek-coder-6.7b-base': ('deepseek-ai/deepseek-coder-6.7b-base', 16384),
    'deepseek-coder-6.7b-instruct': ('deepseek-ai/deepseek-coder-6.7b-instruct', 16384),
    'deepseek-coder-v2-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Instruct', 16384),
    'deepseek-coder-v2-lite-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct', 16384),
    'codegemma-7b': ('google/codegemma-7b', 32768),
    'codegemma-7b-it': ('google/codegemma-7b-it', 32768),
    'starcoder2-7b': ('bigcode/starcoder2-7b', 16384),
    'codellama-7b': ('codellama/CodeLlama-7b-hf', 16384),
    'codellama-7b-instruct': ('codellama/CodeLlama-7b-Instruct-hf', 16384),
    'gpt-oss-20b': ('openai/gpt-oss-20b', 8192),
    'openai/gpt-oss-120b': ('openai/gpt-oss-120b', 8192),
    "deepseek-r1-distill-qwen-32b": ("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", 32768), 

    'mistral-7B-instruct-v0.3': ('mistralai/Mistral-7B-Instruct-v0.3', 32768),
    'mistral-7b-instruct-v0.3': ('mistralai/Mistral-7B-Instruct-v0.3', 32768),
    'devstral-small-2-24b-instruct': ('mistralai/Devstral-Small-2-24B-Instruct-2512', 262144),

    'qwen2.5-3b-instruct': ('Qwen/Qwen2.5-3B-Instruct', 32768),
    'qwen3-4b-instruct': ('Qwen/Qwen3-4B', 32768),
    'llama3.2-3b-instruct': ('meta-llama/Llama-3.2-3B-Instruct', 131072),
    'phi-3-mini-128k': ('microsoft/Phi-3-mini-128k-instruct', 131072),
    'phi-3.5-mini-instruct': ('microsoft/Phi-3.5-mini-instruct', 131072),
    'phi-4-mini-instruct': ('microsoft/Phi-4-mini-instruct', 131072),
    'phi-4-mini-reasoning': ('microsoft/Phi-4-mini-reasoning', 131072),
    'mistral-3-3b-instruct': ('mistralai/Ministral-3-3B-Instruct-2512', 262144),
    'gemma-3-4b-it': ('google/gemma-3-4b-it', 131072),
    'gemma-4-e4b-it': ('google/gemma-4-E4B-it', 131072),
    't5gemma-2-4b': ('google/t5gemma-2-4b-4b', 131072),

    'qwen2.5-14b-instruct': ('Qwen/Qwen2.5-14B-Instruct', 32768),
    'qwen3.5-9b': ('Qwen/Qwen3.5-9B', 262144),
    'llama3-8b-instruct': ('meta-llama/Meta-Llama-3-8B-Instruct', 8192),
    'nextcoder-14b': ('microsoft/NextCoder-14B', 32768),
    'phi-4': ('microsoft/phi-4', 16384),
    'phi-4-reasoning': ('microsoft/Phi-4-reasoning', 32768),
    'mistral-3-8b-instruct': ('mistralai/Ministral-3-8B-Instruct-2512', 262144),
    'mistral-3-14b-instruct': ('mistralai/Ministral-3-14B-Instruct-2512', 262144),
    'gemma-2-9b-it': ('google/gemma-2-9b-it', 8192),
    'gemma-3-12b-it': ('google/gemma-3-12b-it', 131072),

    'deepseek-r1-7b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', 131072),
    'deepseek-r1-8b': ('deepseek-ai/DeepSeek-R1-Distill-Llama-8B', 131072),
    'deepseek-r1-14b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-14B', 131072),
    'deepseek-r1-32b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 131072),


    'qwen3-coder-30b-instruct': ('Qwen/Qwen3-Coder-30B-A3B-Instruct', 262144),
    'qwen3.5-27b': ('Qwen/Qwen3.5-27B', 262144),
    'qwen3.6-27b': ('Qwen/Qwen3.6-27B', 262144),
    'nextcoder-32b': ('microsoft/NextCoder-32B', 32768),
    'gemma-2-27b-it': ('google/gemma-2-27b-it', 8192),
    'gemma-3-27b-it': ('google/gemma-3-27b-it', 131072),
    'gemma-4-31b-it': ('google/gemma-4-31B-it', 262144)
}

_FORCE_BFLOAT16_MODELS = {"nextcoder-32b"}

_NO_REMOTE_CODE_MODELS = {"phi-4-mini-instruct"}


class TransformersClient:
    def __init__(self,llm_name):
        assert llm_name in _MODEL_DICT_LLM
        model_name, model_max_length = _MODEL_DICT_LLM[llm_name]
        local_files_only = os.environ.get("VULRAG_LOCAL_FILES_ONLY", "").lower() in {"1", "true", "yes"}
        trust_remote_code = llm_name not in _NO_REMOTE_CODE_MODELS

        self.model_name = llm_name
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=trust_remote_code,
            local_files_only=local_files_only,
        )
        if self.tokenizer.pad_token is None:
            # reuse eos as pad
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.model_max_length = model_max_length
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = 'left'

        force_cpu = os.environ.get("VULRAG_FORCE_CPU", "").lower() in {"1", "true", "yes"}

        # Wähle Device basierend auf CUDA-Verfügbarkeit
        if not force_cpu and torch.cuda.is_available():
            device_map = "auto"
            dtype = torch.bfloat16 if llm_name in _FORCE_BFLOAT16_MODELS else "auto"
            print(f"Lade Modell '{llm_name}' auf GPU")
        else:
            device_map = "cpu"
            dtype = torch.float32
            print(f"Lade Modell '{llm_name}' auf CPU")

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=trust_remote_code,
            local_files_only=local_files_only,
            device_map=device_map,
            torch_dtype=dtype,
            attn_implementation="sdpa"
        )
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id

    def _build_prompt_text(self, messages_or_text):
        # If already a string, just return it
        if isinstance(messages_or_text, str):
            return messages_or_text

        # If it's a chat message list, use chat template when defined
        if getattr(self.tokenizer, "chat_template", None):
            return self.tokenizer.apply_chat_template(
                messages_or_text, tokenize=False, add_generation_prompt=True
            )

        # Fallback formatting for base models without a template
        parts = []
        for m in messages_or_text:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"<<SYS>>\n{content}\n<</SYS>>")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)

    @torch.inference_mode()
    def generate_text(self, prompt, model_settings = None):
        model_settings = dict(model_settings or {})
        max_new_tokens = model_settings.pop("max_new_tokens", 4096)
        
        text = self._build_prompt_text(prompt)

        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, return_token_type_ids=False)
        except TypeError:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        inputs.pop("token_type_ids", None)
        # move to model.device / GPU
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            **model_settings
        )
        gen_only = output_ids[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(gen_only, skip_special_tokens=True, clean_up_tokenization_spaces=False).strip()



def get_llm_client(llm_name):
    return TransformersClient(llm_name)
                     
def push_prompt(prompt:list, role:str, content:str):
    prompt.append({"role": role, "content": content})
    return prompt

def remove_thinking(text:str):
    return re.sub(r"<think>.*?</think>", "", text)

def generate_simple_prompt(prompt:str):
    return [{"role": "user", "content": prompt}]

def parse_kv_string_to_dict(
        key_value_string: str, 
        arg_sep: str = ";",
        kv_sep: str = "="
    ) -> dict:
    """
    This function parses a key-value string argument into a dictionary.
    The input string should have key-value pairs separated by 'arg_sep' (default is ';')
    and keys and values separated by 'kv_sep' (default is '=').
    For example, the string "key1=value1;key2=value2" will be parsed into the dictionary
    {"key1": "value1", "key2": "value2"}.
    The function also attempts to convert the values to int, float, or boolean types if possible.
    """
    key_value_list = key_value_string.split(arg_sep)
    key_value_dict = {}
    for key_value in key_value_list:
        try:
            key, value_str = key_value.split(kv_sep, 1)
        except ValueError:
            # logging.warning(f"Skipping invalid key-value pair: {key_value}")
            print(f"Skipping invalid key-value pair: {key_value}")
            continue
        key = key.strip()
        value_str = value_str.strip()
        try:
            value = int(value_str)
        except ValueError:
            try:
                value = float(value_str)
            except ValueError:
                if value_str.lower() == "true":
                    value = True
                elif value_str.lower() == "false":
                    value = False
                else:
                    value = value_str
        key_value_dict[key] = value
    return key_value_dict

def extract_LLM_response_by_prefix(response: str, prefix: str) -> str:
    """
    This function extracts the response from the LLM output that is prefixed by a given string.
    """
    if prefix in response:
        return response.split(prefix)[1].strip()
    else:
        return response.strip()

if __name__ == "__main__":
    # print(remove_thinking("<think>thinking</think>Action"))
    # client = get_llm_client("deepseek-chat")
    # prompt = [{"role": "user", "content": "你好"}]
    # print(client.generate_text(prompt,model_settings={"temperature":0.2,"max_tokens":5}))
    # model_settings = parse_kv_string_to_dict("temperature=0.2;max_tokens=10")
    # print(model_settings)
    #pass

    client = TransformersClient("codeqwen1.5-7b")

    messages = [{"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hi in one short sentence."}]
    out = client.generate_text(messages)
    print(out)
