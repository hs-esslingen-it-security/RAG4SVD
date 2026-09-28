import os
import re
import json
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, AutoModelForSequenceClassification
from peft import AutoPeftModelForCausalLM, LoraConfig, get_peft_model
from accelerate import PartialState
from trl import SFTTrainer


def setup_chat_format(model, tokenizer):
    """Adds ChatML special tokens and resizes the model's embeddings accordingly.
    Ported locally since trl>=1.0 dropped this helper from its public API."""
    bos_token, eos_token = '<|im_start|>', '<|im_end|>'
    tokenizer.eos_token = eos_token
    tokenizer.pad_token = eos_token
    tokenizer.bos_token = bos_token
    tokenizer.add_special_tokens({'additional_special_tokens': [bos_token, eos_token]})
    tokenizer.chat_template = (
        "{% for message in messages %}"
        f"{{{{'{bos_token}' + message['role'] + '\\n' + message['content'] + '{eos_token}' + '\\n'}}}}"
        "{% endfor %}"
        "{% if add_generation_prompt %}"
        f"{{{{ '{bos_token}assistant\\n' }}}}"
        "{% endif %}"
    )
    model.resize_token_embeddings(len(tokenizer))
    return model, tokenizer


model_dict_llm = {
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

# Repos whose bundled remote code (auto_map) is stale/incompatible with the
# installed transformers version, but whose architecture is natively supported
# anyway (e.g. phi-4-mini-instruct's remote modeling code imports
# transformers.utils.LossKwargs, which no longer exists there; transformers
# already ships a native "phi3" implementation).
_NO_REMOTE_CODE_MODELS = {"phi-4-mini-instruct"}

# Repos whose published checkpoint is natively float32 instead of the usual
# bfloat16 (e.g. microsoft/NextCoder-32B ships ~122GiB of fp32 weights vs.
# ~64GiB for same-size bf16 checkpoints like Qwen2.5-32B), so torch_dtype='auto'
# picks fp32 and doesn't fit on a single GPU. Force bf16 for these instead.
_FORCE_BFLOAT16_MODELS = {"nextcoder-32b"}


def _resolve_dtype(model_alias):
    return torch.bfloat16 if model_alias in _FORCE_BFLOAT16_MODELS else 'auto'


model_dict_slm = {
    'codebert-base': 'microsoft/codebert-base',
    'graphcodebert-base': 'microsoft/graphcodebert-base',
    'unixcoder-base': 'microsoft/unixcoder-base',
    'codet5-base': 'Salesforce/codet5-base',
    'codet5p-base': 'Salesforce/codet5p-220m',
}

model_dict_embedding = {
    'simcse-bert-base': 'princeton-nlp/sup-simcse-bert-base-uncased',
    'simcse-roberta-base': 'princeton-nlp/sup-simcse-roberta-base',
    'codebert-base': 'microsoft/codebert-base',
    'jina-v2-base-code': 'jinaai/jina-embeddings-v2-base-code',
}


NUM_LABELS = 2
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)


def load_tokenizer_and_model_slm(args):
    assert args.model in model_dict_slm
    model_name = model_dict_slm[args.model]
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.model_max_length = min(tokenizer.model_max_length, args.max_seq_length)

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=NUM_LABELS,
        trust_remote_code=True
    )
    return tokenizer, model


def load_tokenizer_llm(args):
    assert args.model in model_dict_llm
    model_name, model_max_length = model_dict_llm[args.model]
    # use small max_seq_len to avoid GPU OOM
    model_max_length = min(model_max_length, args.max_seq_length)
    trust_remote_code = args.model not in _NO_REMOTE_CODE_MODELS

    try:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint or model_name, trust_remote_code=trust_remote_code)
    except OSError:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=trust_remote_code)
    tokenizer.model_max_length = model_max_length
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'left'
    # truncate from the left: prompts that overflow model_max_length must keep
    # the trailing "### Response:" marker (and, for training, the label after
    # it) intact, or the model/collator loses the actual query it's asked about
    tokenizer.truncation_side = 'left'

    return tokenizer


def setup_peft_model(args, model):
    task_type = {
        'classification': 'SEQ_CLS',
        'generation': 'CAUSAL_LM',
    }[args.task_type]

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias='none',
        task_type=task_type,
        target_modules='all-linear',
    )
    model = get_peft_model(model, lora_config)

    return model


def load_tokenizer_and_model_llm_seq_cls(args):
    tokenizer = load_tokenizer_llm(args)

    # Ensure that the model is placed on the correct device for multi-GPU training
    # https://huggingface.co/docs/trl/v0.9.6/en/sft_trainer#multi-gpu-training
    device_string = PartialState().process_index
    device_map = {'': device_string}

    if args.checkpoint:
        model = AutoModelForSequenceClassification.from_pretrained(
            args.checkpoint,
            device_map=device_map,
        )
        return tokenizer, model

    assert args.model in model_dict_llm
    model_name, _ = model_dict_llm[args.model]
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=NUM_LABELS,
        torch_dtype=_resolve_dtype(args.model),
        device_map=device_map,
        trust_remote_code=True,
        quantization_config=bnb_config,
    )
    model.config.pad_token_id = model.config.eos_token_id
    model = setup_peft_model(args, model)

    return tokenizer, model


def load_tokenizer_and_model_llm_causal_lm(args):
    tokenizer = load_tokenizer_llm(args)

    # Ensure that the model is placed on the correct device for multi-GPU training
    # https://huggingface.co/docs/trl/v0.9.6/en/sft_trainer#multi-gpu-training
    device_string = PartialState().process_index
    device_map = {'': device_string}

    if args.checkpoint:
        model = AutoPeftModelForCausalLM.from_pretrained(
            args.checkpoint,
            device_map=device_map,
        )
        return tokenizer, model

    assert args.model in model_dict_llm
    model_name, _ = model_dict_llm[args.model]
    if args.eval_only:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=_resolve_dtype(args.model),
            device_map=device_map,
            trust_remote_code=args.model not in _NO_REMOTE_CODE_MODELS,
        )
        return tokenizer, model

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=_resolve_dtype(args.model),
        device_map=device_map,
        trust_remote_code=True,
        quantization_config=bnb_config,
    )

    if args.use_chat_format:
        model, tokenizer = setup_chat_format(model, tokenizer)
    model = setup_peft_model(args, model)

    return tokenizer, model


class CustomSFTTrainer(SFTTrainer):
    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        """
        Return: A tuple with the loss, logits and labels.
        """
        inputs = self._prepare_inputs(inputs)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                do_sample=False,
                top_p=None,  # set top_p to None to avoid warning
                max_new_tokens=2048,
                # self.processing_class can be a ProcessorMixin (e.g. Gemma3Processor)
                # for VLM-capable configs, which has no eos_token_id of its own; TRL's
                # own SFTTrainer.__init__ already unwraps this into self._tokenizer for
                # exactly this reason, so use that instead of processing_class directly.
                pad_token_id=self._tokenizer.eos_token_id,
                use_cache=True,
            )

        loss = None
        # to compute metrics, labels should not be None, set as placeholders instead
        labels = [-1 for _ in range(len(inputs['input_ids']))]
        labels = torch.tensor(labels).to(model.device)

        return loss, outputs, labels


def calculate_pairwise_accuracy(y_true, y_pred, pair_ids):
    """Calculate pairwise accuracy: both elements of a pair must be correctly classified."""
    if pair_ids is None or len(pair_ids) == 0:
        return {}
    
    pairs = {}
    for idx, pair_id in enumerate(pair_ids):
        if pair_id is None:
            continue
        pairs.setdefault(pair_id, []).append((y_true[idx], y_pred[idx]))
    
    complete_pairs = 0
    correct_pairs = 0
    incomplete_pair_groups = 0
    
    for samples in pairs.values():
        if len(samples) != 2:
            incomplete_pair_groups += 1
            continue

        labels = {y_t for y_t, _ in samples}
        if labels != {0, 1}:
            incomplete_pair_groups += 1
            continue
        
        complete_pairs += 1
        if all(y_t == y_p for y_t, y_p in samples):
            correct_pairs += 1
    
    pairwise_accuracy = correct_pairs / complete_pairs if complete_pairs > 0 else 0
    return {
        'pairwise_accuracy': pairwise_accuracy,
        'pairwise_correct_pairs': correct_pairs,
        'pairwise_complete_pairs': complete_pairs,
        'pairwise_incomplete_pair_groups': incomplete_pair_groups,
    }


def compute_metrics_lm(eval_prediction, response_template, tokenizer, y_true, output_dir=None, beta=.3, pair_ids=None):
    outputs = eval_prediction.predictions
    # Trainer pads outputs with -100, replace them with pad_token first
    # https://github.com/huggingface/transformers/issues/22634
    outputs = np.where(outputs != -100, outputs, tokenizer.pad_token_id)
    outputs = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    responses = []
    for output in outputs:
        if response_template in output:
            response = output.split(response_template)[-1].strip()
        else:
            # the response part can be truncated if the input function is too long, but this is rare
            response = output
        responses.append(response)

    # convert response to binary label
    y_pred = []
    for response in responses:
        # only the model's first line is the actual answer; anything after it
        # is either free-running generation or (if the prompt got truncated
        # and lost its trailing "### Response:" marker) echoed/hallucinated
        # prompt text, so scanning the full response for loose substrings like
        # '0'/'1'/'no' picks up unrelated numbers and code and misclassifies
        first_line = response.strip().split('\n', 1)[0].lower()
        if re.search(r'\bnon-vulnerable\b|\bnon\b|\bfalse\b|\bno\b|\b0\b', first_line):
            y_pred.append(0)
        elif re.search(r'\bvulnerable\b|\btrue\b|\byes\b|\b1\b', first_line):
            y_pred.append(1)
        else:
            # -1 as null label
            y_pred.append(-1)

    y_pred = np.array(y_pred)
    null_pred_ratio = np.mean(y_pred == -1)
    # treat null label as negative label (non-vulnerable)
    y_pred = np.where(y_pred == -1, 0, y_pred)
    y_pred = y_pred.tolist()
    assert len(y_pred) == len(y_true)

    accuracy = accuracy_score(y_true, y_pred)
    # compute precision, recall and fscore
    precision, recall, fscore, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', beta=beta)
    metrics = {
        'null_pred_ratio': null_pred_ratio,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'fscore': fscore,
    }
    
    # compute pairwise accuracy if pair_ids provided
    if pair_ids is not None:
        pairwise_metrics = calculate_pairwise_accuracy(y_true, y_pred, pair_ids)
        metrics.update(pairwise_metrics)

    # save labels, outputs, responses and predictions
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        metrics.update(y_true=y_true, y_pred=y_pred, responses=responses, outputs=outputs)
        for field in ['y_true', 'y_pred', 'responses', 'outputs']:
            with open(f'{output_dir}/{field}.json', 'w') as f:
                json.dump(metrics.pop(field), f, indent=4)

    return metrics


def compute_metrics_cls(eval_prediction, output_dir=None, beta=.3, pair_ids=None):
    y_true = eval_prediction.label_ids
    logits = eval_prediction.predictions
    # T5 return tuple as result
    if isinstance(logits, tuple):
        logits = logits[0]
    y_pred = np.argmax(logits, axis=-1)

    accuracy = accuracy_score(y_true, y_pred)
    # compute precision, recall and fscore
    precision, recall, fscore, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', beta=beta)
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'fscore': fscore,
    }
    
    # compute pairwise accuracy if pair_ids provided
    if pair_ids is not None:
        pairwise_metrics = calculate_pairwise_accuracy(y_true, y_pred, pair_ids)
        metrics.update(pairwise_metrics)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        with open(f'{output_dir}/y_true.json', 'w') as f:
            json.dump(y_true.tolist(), f, indent=4)
        with open(f'{output_dir}/y_pred.json', 'w') as f:
            json.dump(y_pred.tolist(), f, indent=4)

    return metrics
