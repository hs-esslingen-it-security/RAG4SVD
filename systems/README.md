# RAG4SVD Systems

This directory contains the reproduced and adapted implementations of the six RAG-based software vulnerability detection systems considered in this study:

- `svd-bench/`
- `llama-vd/`
- `grace/`
- `llm4vuln/`
- `vul-rag/`
- `vul-triage/`

Each subdirectory contains the corresponding implementation, system-specific setup instructions, and notes on adaptations made for reproduction and benchmarking.

> **Note:** The six systems have heterogeneous original dependencies. We therefore preserve system-specific environments where necessary rather than enforcing a single global environment. Please refer to the README inside each system directory for installation and execution instructions.

## System Adaptations
Where required, we adapted the original implementations to support the unified evaluation setup used in this study. These adaptations include, depending on the system:

- support for additional open-weight Hugging Face models,
- support for the PrimeVul Paired benchmark,
- replacement of proprietary-model dependencies where required,
- parser and output-format handling,
- checkpointing and resume functionality.

We preserve the original system logic, prompts, retrieval settings, and hyperparameters where possible. System-specific changes are documented in the respective subdirectory.

## Hardware
The experiments were executed on a high-performance computing environment using NVIDIA GPUs (NVIDIA L40S, H100).

## Licenses
The systems contained in this directory originate from different research projects and are subject to their respective original licenses.
Please consult the license information provided inside each system directory and, where applicable, the corresponding upstream repository before using or redistributing the code.
The license of this replication package does **not** override the licenses of the included or adapted third-party systems.