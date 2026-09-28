import re
import importlib.util
from typing import Any, Dict, List, Union

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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

    'mistral-7B-Instruct-v0.3': ('mistralai/Mistral-7B-Instruct-v0.3', 32768),
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

_NO_REMOTE_CODE_MODELS = {"phi-4-mini-instruct"}

_FORCE_BFLOAT16_MODELS = {"nextcoder-32b"}


class TransformersClient:
    def __init__(self, llm_name: str):
        if llm_name not in _MODEL_DICT_LLM:
            supported = ", ".join(sorted(_MODEL_DICT_LLM.keys()))
            raise ValueError(f"Unknown llm_name '{llm_name}'. Supported: {supported}")

        model_name, model_max_length = _MODEL_DICT_LLM[llm_name]
        self.model_name = llm_name
        trust_remote_code = llm_name not in _NO_REMOTE_CODE_MODELS
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=trust_remote_code)

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.model_max_length = model_max_length
        self.tokenizer.padding_side = "left"

        if torch.cuda.is_available():
            self.device = "cuda"
            dtype = torch.bfloat16 if llm_name in _FORCE_BFLOAT16_MODELS else "auto"
        else:
            self.device = "cpu"
            dtype = torch.float32

        common_kwargs = {
            "trust_remote_code": trust_remote_code,
            "dtype": dtype,
            "attn_implementation": "sdpa",
        }

        has_accelerate = importlib.util.find_spec("accelerate") is not None
        if has_accelerate:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto" if self.device == "cuda" else "cpu",
                **common_kwargs,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                **common_kwargs,
            )
            self.model.to(self.device)
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id
        if getattr(self.model.generation_config, "do_sample", False) is False:
            for attr in ("temperature", "top_p", "top_k"):
                if hasattr(self.model.generation_config, attr):
                    setattr(self.model.generation_config, attr, None)

    def _build_prompt_text(self, messages_or_text: Union[str, List[Dict[str, str]]]) -> str:
        if isinstance(messages_or_text, str):
            return messages_or_text

        if getattr(self.tokenizer, "chat_template", None):
            return self.tokenizer.apply_chat_template(
                messages_or_text, tokenize=False, add_generation_prompt=True
            )

        parts = []
        for message in messages_or_text:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                parts.append(f"<<SYS>>\n{content}\n<</SYS>>")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)

    @torch.inference_mode()
    def generate_text(self, prompt: Union[str, List[Dict[str, str]]], model_settings: Dict[str, Any] = None) -> str:
        settings = dict(model_settings or {})
        text = self._build_prompt_text(prompt)

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                return_token_type_ids=False,
            )
        except TypeError:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        inputs.pop("token_type_ids", None)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        max_new_tokens = int(settings.pop("max_new_tokens", 256))
        temperature = settings.get("temperature", None)
        if temperature is not None and float(temperature) <= 0:
            settings.pop("temperature", None)
            settings.setdefault("do_sample", False)
        if settings.get("do_sample", False) is False:
            settings.pop("top_p", None)
            settings.pop("top_k", None)

        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            **settings,
        )
        gen_only = output_ids[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(
            gen_only,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ).strip()


def get_llm_client(llm_name: str) -> TransformersClient:
    return TransformersClient(llm_name)


def generate_simple_prompt(prompt: str) -> List[Dict[str, str]]:
    return [{"role": "user", "content": prompt}]


def parse_kv_string_to_dict(key_value_string: str, arg_sep: str = ";", kv_sep: str = "=") -> Dict[str, Any]:
    key_value_dict: Dict[str, Any] = {}
    if not key_value_string.strip():
        return key_value_dict
    for item in key_value_string.split(arg_sep):
        try:
            key, value_str = item.split(kv_sep, 1)
        except ValueError:
            continue
        key = key.strip()
        value_str = value_str.strip()
        try:
            value: Any = int(value_str)
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


def remove_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
