## Model Lineup

We evaluate **22 open-weight models** spanning multiple model families, parameter scales, and specializations:

| Family | Model (Paper Abbreviation) | Scale | Specialization | Hugging Face Checkpoint (Link) | Context Size |
|---|---|---:|---|---|---:|
| Qwen | Qwen2.5-3B | 3.1B | General | [`Qwen/Qwen2.5-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | 32K |
|  | Qwen2.5-14B | 14.7B | General | [`Qwen/Qwen2.5-14B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct) | 32K |
|  | Qwen2.5-32B | 32.5B | General | [`Qwen/Qwen2.5-32B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct) | 32K |
|  | Qwen2.5-Coder-3B | 3.1B | Code | [`Qwen/Qwen2.5-Coder-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | 32K |
|  | Qwen2.5-Coder-14B | 14B | Code | [`Qwen/Qwen2.5-Coder-14B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct) | 32K |
|  | Qwen2.5-Coder-32B | 32B | Code | [`Qwen/Qwen2.5-Coder-32B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) | 32K |
|  | Qwen3-4B | 4.0B | General | [`Qwen/Qwen3-4B`](https://huggingface.co/Qwen/Qwen3-4B) | 32K |
|  | Qwen3.5-9B | 9.0B | General | [`Qwen/Qwen3.5-9B`](https://huggingface.co/Qwen/Qwen3.5-9B) | 256K |
|  | Qwen3.6-27B | 27.0B | General | [`Qwen/Qwen3.6-27B`](https://huggingface.co/Qwen/Qwen3.6-27B) | 256K |
|  | QwQ-32B | 32.5B | General | [`Qwen/QwQ-32B`](https://huggingface.co/Qwen/QwQ-32B) | 128K |
| Llama | Llama-3.2-3B | 3.2B | General | [`meta-llama/Llama-3.2-3B-Instruct`](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) | 128K |
|  | Llama-3.1-8B | 8.0B | General | [`meta-llama/Llama-3.1-8B-Instruct`](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 128K |
| Phi | Phi-4-Mini | 3.8B | General | [`microsoft/Phi-4-mini-instruct`](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 128K |
|  | Phi-4 | 14.7B | General | [`microsoft/phi-4`](https://huggingface.co/microsoft/phi-4) | 16K |
| Gemma | Gemma-3-4B | 4.0B | General | [`google/gemma-3-4b-it`](https://huggingface.co/google/gemma-3-4b-it) | 128K |
|  | Gemma-3-12B | 12.0B | General | [`google/gemma-3-12b-it`](https://huggingface.co/google/gemma-3-12b-it) | 128K |
|  | Gemma-3-27B | 27.0B | General | [`google/gemma-3-27b-it`](https://huggingface.co/google/gemma-3-27b-it) | 128K |
| NextCoder | NextCoder-14B | 14.7B | Code | [`microsoft/NextCoder-14B`](https://huggingface.co/microsoft/NextCoder-14B) | 32K |
|  | NextCoder-32B | 32.5B | Code | [`microsoft/NextCoder-32B`](https://huggingface.co/microsoft/NextCoder-32B) | 32K |
| DeepSeek | DeepSeek-R1-8B | 8.0B | General | [`deepseek-ai/DeepSeek-R1-Distill-Llama-8B`](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) | 128K |
|  | DeepSeek-R1-32B | 32.5B | General | [`deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) | 128K |
| Mistral | Mistral-7B | 7.3B | General | [`mistralai/Mistral-7B-Instruct-v0.3`](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | 32K |
