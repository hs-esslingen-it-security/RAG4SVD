import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import torch
import torch.nn as nn
import transformers
from datasets import Dataset, DatasetDict
from trl import SFTTrainer
from transformers import (TrainingArguments)
from utils.data_preprocessing import load_and_preprocess_dataset, plot_tsne
from utils.modeling import (
    load_model_tokenizer_instruct,
    predict_generative,
    evaluate_generative,
)
from config import get_config

DEBUG = False

output_dir = "llama_instruct_finetuned_bigvul"

# Fetch config
config = get_config()
db_name = config['db_name']

# Load model and tokenizer
base_model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
model, tokenizer, peft_config = load_model_tokenizer_instruct(base_model_name)

# Load and preprocess dataset
print("\n\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)

# Define the prompt generation functions

def generate_prompt(data_point):
    return f"""Classify the source code into Vulnerable or Safe, and return the answer as the corresponding label.
Code: {data_point['code']}
Label: {data_point['label_text']}""".strip()

def generate_test_prompt(i):
    row = df_test.iloc[i]
    return f"""Classify the source code into Vulnerable or Safe, and return the answer as the corresponding label.
Code: {row['code']}
Label: """.strip()


# Generate prompts for training and evaluation data
df_train['text'] = df_train.apply(generate_prompt, axis=1)
df_eval['text'] = df_eval.apply(generate_prompt, axis=1)

# Convert to datasets
train_data = Dataset.from_pandas(df_train[["text", "label_text"]])
eval_data = Dataset.from_pandas(df_eval[["text", "label_text"]])

y_true = df_test['label_text']

# Combine them into a single DatasetDict
dataset = DatasetDict({
    'train': train_data,
    'val': eval_data,
})

# Model training 
print("\n\n***  Model finetuning  ***\n")
print("\n Model training ...")

training_arguments = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=4,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    gradient_checkpointing=True,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    weight_decay=0.001,
    fp16=True,
    bf16=False,
    max_grad_norm=0.3,
    max_steps=-1,
    warmup_ratio=0.03,
    group_by_length=False,
    lr_scheduler_type="cosine",
    report_to="wandb",
    eval_strategy="steps",
    eval_steps = 0.2,
    save_steps = 0.2,
    load_best_model_at_end = True,
    save_total_limit=1,
)

trainer = SFTTrainer(
    model=model,
    args=training_arguments,
    train_dataset=train_data,
    eval_dataset=eval_data,
    peft_config=peft_config,
    dataset_text_field="text",
    tokenizer=tokenizer,
    max_seq_length=512,
    packing=False,
    dataset_kwargs={
    "add_special_tokens": False,
    "append_concat_token": False,
    }
) 

# Launch training
trainer.train()

model.save_pretrained(f"instruct_finetuned_{db_name}")
tokenizer.save_pretrained(f"instruct_finetuned_{db_name}")

# Testing
print("\n Model testing ...")

y_pred, y_true_pred, embeddings, nbr_weird_preds, prompt_1 = predict_generative(
    df_test, model, tokenizer, prompt_fn=generate_test_prompt
)
print(y_pred[:2])

evaluate_generative(y_true_pred, y_pred)
print("\n nbr_weird_preds : ", nbr_weird_preds)

plot_tsne(embeddings, y_true_pred, f"plots/tSNE_instruct_tuning_{db_name}.png", "text")

model.config.use_cache = True