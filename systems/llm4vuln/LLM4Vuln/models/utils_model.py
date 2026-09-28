import torch
import torch.cuda

# # --- FIX FOR MXFP4 KERNELS ON PYTORCH 2.6 ---
# _original_get_properties = torch.cuda.get_device_properties

# class DevicePropertiesWrapper:
#     def __init__(self, properties):
#         self._properties = properties
#         # On L40S (Ada), the opt-in shared memory is 99,328 bytes (approx 97KB).
#         # We provide this attribute which the kernels library is looking for.
#         self.shared_memory_per_block_optin = getattr(properties, 'shared_memory_per_block', 49152)
        
#     def __getattr__(self, name):
#         return getattr(self._properties, name)

# # Overwrite the global function so the 'kernels' library uses our wrapper
# torch.cuda.get_device_properties = lambda device: DevicePropertiesWrapper(_original_get_properties(device))
# --------------------------------------------

import os
# os.environ["TORCH_COMPILE_DISABLE"] = "1" # to avoid issues with Triton kernels
import re
import triton
import transformers
import accelerate
import warnings
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_huggingface import HuggingFaceEmbeddings
from config import seed

MAX_NEW_TOKEN = 4096
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

    'gpt-oss-20b': ('openai/gpt-oss-20b', 131072),
    'gpt-oss-120b': ('openai/gpt-oss-120b', 131072),
}

_EMB_DICT = {
    'codebert-base': 'microsoft/codebert-base',
    'codet5-base': 'Salesforce/codet5-base',
    'codet5p-770m': 'Salesforce/codet5p-770m',
    'graphcodebert-base': 'microsoft/graphcodebert-base',
    'qwen3-embedding-0.6B': 'Qwen/Qwen3-Embedding-0.6B',
    'qwen3-embedding-4B': 'Qwen/Qwen3-Embedding-4B',
    'bge-m3' : 'BAAI/bge-m3',
}


# Global variables
SUMMARY_MODEL = None
EMBEDDING_MODEL = None
GT_MODEL = None
# Dictionary to cache instantiated models by name to avoid duplicates
_CLIENT_CACHE = {}

def _init(summary_model_name, embedding_model_name, ground_truth_model_name):
    global SUMMARY_MODEL
    global EMBEDDING_MODEL
    global GT_MODEL
    
    EMBEDDING_MODEL = create_embedding_client(embedding_model_name)
    print(f"Embedding model: {embedding_model_name}")

    # Assign (cached) instances to global variables
    # Initialize LLMs using the cached getter
    # This ensures they are added to _CLIENT_CACHE immediately
    SUMMARY_MODEL = get_llm_client(summary_model_name)
    print(f"Summary model: {summary_model_name}")
    GT_MODEL = get_llm_client(ground_truth_model_name)
    print(f"Ground truth model: {ground_truth_model_name}")



def get_GT_MODEL():
    return GT_MODEL

def get_SUMMARY_MODEL():
    return SUMMARY_MODEL

def get_EMBEDDING_MODEL():
    return EMBEDDING_MODEL

### huggingface embedding client
def create_embedding_client(emb_name):
    """
    Returns a HuggingFaceEmbeddings instance directly.
    FAISS requires the object to have .embed_documents() and .embed_query().
    """
    assert emb_name in _EMB_DICT, f"Embedding model {emb_name} not found in _EMB_DICT"
    model_name = _EMB_DICT[emb_name]
    
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cuda", "trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True},
    )

### Client for LLMs based on transformers
class TransformersClient:
    def __init__(self,llm_name):
        assert llm_name in _MODEL_DICT_LLM
        model_name, model_max_length = _MODEL_DICT_LLM[llm_name]

        self.model_name = llm_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
        if self.tokenizer.pad_token is None:
            # reuse eos as pad
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.model_max_length = model_max_length
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = 'left'

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=False,
            device_map="auto",
            dtype="auto"
        )
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id

    def __call__(self, prompt):
        """
        Makes the class callable so it works with LangChain LCEL syntax (chain = prompt | model | parser)
        Usage: chain = prompt | model | parser
        """
        # If the input is a LangChain PromptValue, convert it to string
        if hasattr(prompt, "to_string"):
            text = prompt.to_string()
        else:
            text = str(prompt)
            
        return self.generate_text(text)

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
        model_settings = model_settings or {}

        if "temperature" not in model_settings:
            model_settings["temperature"] = 0.01 
        
        text = self._build_prompt_text(prompt)

        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, return_token_type_ids=False)
        except TypeError:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        inputs.pop("token_type_ids", None)
        # move to model.device / GPU
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        output_ids = self.model.generate(**inputs, max_new_tokens=MAX_NEW_TOKEN, eos_token_id=self.tokenizer.eos_token_id, pad_token_id=self.tokenizer.pad_token_id, **model_settings)
        gen_only = output_ids[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(gen_only, skip_special_tokens=True, clean_up_tokenization_spaces=False).strip()

def get_llm_client(llm_name):
    # Check if we already loaded this model
    if llm_name in _CLIENT_CACHE:
        return _CLIENT_CACHE[llm_name]
    
    # If not, load it and save it to the cache
    print(f"Loading model: {llm_name} ...")
    client = TransformersClient(llm_name)
    _CLIENT_CACHE[llm_name] = client
    return client

if __name__ == "__main__":
    print(f"PyTorch version:     {torch.__version__}")
    print(f"Transformers version: {transformers.__version__}")
    print(f"Triton version:       {triton.__version__}")
    client = TransformersClient("gpt-oss-20b")

    messages = [
    {"role": "user", "content": "Explain in one sentence what MXFP4 quantization is."},]
    out = client.generate_text(messages)
    print(out)