---
title: "RAG4SVD Study Selection"
source: "https://github.com/hs-esslingen-it-security/Awesome-LLM4SVD/tree/main/taxonomy"
source_artifact: "Awesome-LLM4SVD Taxonomy"
source_publication: S. Kaniewski, F. Schmidt, M. Enzweiler, M. Menth, and T. Heer. 2026. A Systematic Literature Review on Detecting Software Vulnerabilities with Large Language Models. ACM Transactions on Software Engineering and Methodology (TOSEM) (2026). doi:10.1145/3815425
retrieved: "2026-08-13"
---

<br>

# RAG4SVD Study Screening and Selection 📊


This document records the screening and selection process used to identify the representative RAG4SVD systems evaluated. The study list is based on the RAG category of the continuously maintained **Awesome-LLM4SVD Taxonomy** (source above), retrieved on **13 August 2026**.

The taxonomy snapshot contains **34 RAG-category entries**. Three entries are explicitly excluded as outside the RAG4SVD scope adopted in the paper (two agentic approaches and one SAST-based approach), leaving **31 in-scope studies**. 
12 of these studies provide publicly accessible code or artifacts, 6 provide a sufficiently complete and documented setup for reproducibility.

## Selection Procedure

The screening process follows three stages:

1. RAG4SVD scope.
2. **Publicly accessible** implementation code or equivalent executable artifacts must be available.
3. The released artifacts must contain a **sufficiently complete** pipeline, required data, and enough setup information to permit reproduction.


## Selected Representative Systems

- **Vul-RAG: Enhancing LLM-based Vulnerability Detection via Knowledge-level RAG.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2406.11147)] [[Code](https://github.com/knowledgerag4llmvuld/knowledgerag4llmvuld)]  

- **GRACE: Empowering LLM-based Software Vulnerability Detection with Graph Structure and In-Context Learning.** **`JSS 2024`** [[Paper](https://www.sciencedirect.com/science/article/pii/S0164121224000748)] [[Code](https://github.com/P-E-Vul/GRACE)]  

- **Llama-Based Source Code Vulnerability Detection: Prompt Engineering vs Fine Tuning.** **`ESORICS 2025`** [[Paper](https://link.springer.com/chapter/10.1007/978-3-032-07884-1_15)] [[Code](https://github.com/DynaSoumhaneOuchebara/Llama-based-vulnerability-detection)]  

- **LLM4Vuln: A Unified Evaluation Framework for Decoupling and Enhancing LLMs' Vulnerability Reasoning.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2401.16185)] [[Code](https://anonymous.4open.science/r/LLM4Vuln/README.md)]  

- **Benchmarking Large Language Models for Multi-Language Software Vulnerability Detection.** **`arXiv 2025`** [[Paper](https://arxiv.org/abs/2503.01449)] [[Code](https://github.com/soarsmu/SVD-Bench)]

- **VulTriage: Triple-Path Context Augmentation for LLM-Based Vulnerability Detection.** **`arXiv 2026`** [[Paper](https://arxiv.org/abs/2605.09461v2)] [[Code](https://github.com/vinsontang1/VulTriage)]


## In-Scope Studies with Public Artifacts but Reproducibility Limitations

- **LLM-CloudSec: Large Language Model Empowered Automatic and Deep Vulnerability Analysis for Intelligent Clouds.** **`INFOCOM 2024`** [[Paper](https://ieeexplore.ieee.org/abstract/document/10620804)] [[Code](https://github.com/DPCa0/LLM-CloudSec)]  
  **Note:** Insufficient artifacts, i.e., missing clear performance results

- **Real-VulLLM: An LLM Based Assessment Framework in the Wild.** **`arXiv 2025`** [[Paper](https://arxiv.org/abs/2510.04056)]  
  **Note:** Repository/archive appears to be available, but no README or sufficient documentation was found.

- **An Empirical Evaluation of LLM-Based Approaches for Code Vulnerability Detection: RAG, SFT, and Dual-Agent Systems.** **`CASCON 2025`** [[Paper](https://ieeexplore.ieee.org/document/11344502)]  
  **Note:** Repository was newly added at screening time; no README or sufficient documentation was available.

- **Software Vulnerability Detection Using LLM: Does Additional Information Help?** **`ACSAC 2024`** [[Paper](https://ieeexplore.ieee.org/abstract/document/10917361)] [[Code](https://github.com/research7485/vulnerability_detection)]  
  **Note:** No README or documented setup sufficient for reproduction.

- **RAG-Enhanced Multi-Model Ensemble for Automated Vulnerability Detection Using SLMs.** **`ICECTE 2026`** [[Paper](https://ieeexplore.ieee.org/abstract/document/11429262)] [[Code](https://github.com/rafi79/RAG-Enhanced-Multi-Model-Ensemble-for-Automated-Vulnerability-Detection-Using-SLMs)]  
  **Note:** No README or documentation; repository consists primarily of two notebooks.

- **To Err is Machine: Vulnerability Detection Challenges LLM Reasoning.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2403.17218)] [[Code](https://figshare.com/articles/dataset/Data_Package_for_LLM_Vulnerability_Detection_Study/27368025)]  
  **Note:** Full code but benchmark focusing on LLM reasoning evaluation, less focus on RAG system itself

## In-Scope Studies with Restricted, Incomplete, or No Artifact Access

- **DeepVulHunter: Enhancing the Code Vulnerability Detection Capability of LLMs through Multi-Round Analysis.** **`JIIS 2025`** [[Paper](https://link.springer.com/article/10.1007/s10844-025-00982-0)]  
  **Note:** Artifacts available on request only.

- **Assessing the Effectiveness of LLMs in Android Application Vulnerability Analysis.** **`ADIoT 2024`** [[Paper](https://link.springer.com/chapter/10.1007/978-3-031-85593-1_9)]  
  **Note:** Only dataset available on request.

- **Evaluating Retrieval-Augmented Generation for LLM-Based Vulnerability Detection: An Empirical Study on Real-World Java Vulnerabilities.** **`IEEE Access 2026`** [[Paper](https://ieeexplore.ieee.org/abstract/document/11450344)]  
  **Note:** Public links provide datasets only; no repository was obtained on request.

- **Retrieval-Augmented Semantic Mapping for Vulnerability Detection via Multi-View Code Similarity.** **`Electronics 2026`** [[Paper](https://www.mdpi.com/2079-9292/15/3/612)]  
  **Note:** Dataset available; code stated to be available on request, but no response was received.

- **Boosting Cybersecurity Vulnerability Scanning based on LLM-supported Static Application Security Testing.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2409.15735)]
- **CryptoScope: Utilizing Large Language Models for Automated Cryptographic Logic Vulnerability Detection.** **`arXiv 2025`** [[Paper](https://arxiv.org/abs/2508.11599)]
- **Exploration On Prompting LLM With Code-Specific Information For Vulnerability Detection.** **`SSE 2024`** [[Paper](https://ieeexplore.ieee.org/abstract/document/10664399)]
- **Software Vulnerability Detection with GPT and In-Context Learning.** **`DSC 2023`** [[Paper](https://ieeexplore.ieee.org/abstract/document/10381286)]
- **LLbezpeky: Leveraging Large Language Models for Vulnerability Detection.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2401.01269)]
- **Automated Software Vulnerability Static Code Analysis Using Generative Pre-Trained Transformer Models.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2408.00197)]
- **Research on the LLM-Driven Vulnerability Detection System Using LProtector.** **`ICDSCA 2024`** [[Paper](https://ieeexplore.ieee.org/abstract/document/10859408)]
- **Retrieval-Augmented Few-Shot Prompting Versus Fine-Tuning for Code Vulnerability Detection.** **`FLLM 2025`** [[Paper](https://ieeexplore.ieee.org/document/11391248)]
- **A Sequential Multi-Stage Approach for Code Vulnerability Detection via Confidence- and Collaboration-based Decision Making.** **`EMNLP 2025`** [[Paper](https://aclanthology.org/2025.emnlp-main.1071/)]
- **VulEval: Towards Repository-Level Evaluation of Software Vulnerability Detection.** **`arXiv 2024`** [[Paper](https://arxiv.org/abs/2404.15596)]
- **MulVul: Retrieval-augmented Multi-Agent Code Vulnerability Detection via Cross-Model Prompt Evolution.** **`arXiv 2026`** [[Paper](https://arxiv.org/abs/2601.18847)]
- **SSRFSeek: An LLM-based Static Analysis Framework for Detecting SSRF Vulnerabilities in PHP Applications.** **`AINIT 2025`** [[Paper](https://ieeexplore.ieee.org/abstract/document/11035424)]
- **Specification-Guided Vulnerability Detection with Large Language Models.** **`arXiv 2025`** [[Paper](https://arxiv.org/abs/2511.04014)] [[Code](https://github.com/zhuhaopku/VulInstruct-temp)]
- **VulKnow: Enhancing Vulnerability Detection with Structured Knowledge and Large Language Models.** **`IEEE Internet of Things Journal 2026`** [[Paper](https://ieeexplore.ieee.org/document/11535732)]
- **Prompting Matters: Evaluating Strategies for LLM-based Vulnerability Detection.** **`ISCTIS 2026`** [[Paper](https://ieeexplore.ieee.org/document/11572319/)]




## Explicitly Out-of-Scope Studies

- **Think Broad, Act Narrow: CWE Identification with Multi-Agent Large Language Models.** **`arXiv 2025`** [[Paper](https://arxiv.org/abs/2508.01451)] [[Code](https://zenodo.org/records/15871507)]  
  **Exclusion rationale:** Agentic approach; outside the RAG4SVD scope adopted in the paper.

- **Leveraging Intra-and Inter-References in Vulnerability Detection using Multi-Agent Collaboration Based on LLMs.** **`Cluster Computing 2025`** [[Paper](https://link.springer.com/article/10.1007/s10586-025-05721-2)]  
  **Exclusion rationale:** Agentic approach; outside the RAG4SVD scope adopted in the paper.

- **DLAP: A Deep Learning Augmented Large Language Model Prompting Framework for Software Vulnerability Detection.** **`JSS 2024`** [[Code](https://github.com/Yang-Yanjing/DLAP)]  
  **Exclusion rationale:** SAST-based augmentation; outside the RAG4SVD scope adopted in the paper.

