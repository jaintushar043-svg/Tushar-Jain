# 12. Suggested Open-Source Models for the SLM

Selection criteria, in priority order: (1) permissive commercial license, (2) strong reasoning over dense, long-form text (regulatory prose), (3) good multilingual support (many target jurisdictions — India, EU, Southeast Asia — need more than English), (4) active community/ecosystem support for quantization and fine-tuning tooling, (5) a size range (3B–14B) that is cheaply fine-tunable and servable in-VPC, including on modest single-GPU footprints for smaller silo tenants.

## 12.1 Base / instruction-tuned model candidates (the proprietary SLM's foundation)

| Model | Size | License | Why it's a strong candidate |
|---|---|---|---|
| **Llama 3.1 / 3.2** (Meta) | 8B (3.1), 3B (3.2) | Llama Community License (permissive, commercial use allowed under usage terms) | Best-in-class reasoning-per-parameter at 8B, huge fine-tuning/tooling ecosystem, strong long-context support (128K) useful for whole-document regulatory analysis |
| **Mistral 7B / Mixtral 8x7B** | 7B dense / 47B MoE (13B active) | Apache 2.0 (fully permissive) | Cleanest license of the major families — no usage-tier restrictions at all; Mixtral's MoE gives strong quality at moderate serving cost if GPU budget allows |
| **Qwen 2.5 / Qwen 3** (Alibaba) | 7B / 8B / 14B | Apache 2.0 | Excellent multilingual coverage (strong for APAC jurisdictions), strong instruction-following and structured-output (JSON) reliability, competitive with Llama at same size |
| **Phi-3.5-mini / Phi-4-mini** (Microsoft) | 3.8B | MIT | Remarkable reasoning density for its size — good default for cost-sensitive silo tenants needing CPU or single small-GPU deployment |
| **Gemma 2 / Gemma 3** (Google) | 9B / 2B–12B | Gemma license (permissive, some usage restrictions) | Strong safety-tuning baseline out of the box, useful head start on guardrails work |

**Recommendation**: standardize the shared base on **Llama 3.1 8B or Qwen 2.5 7B** for the primary jurisdictions (best balance of reasoning quality, context length, and tooling maturity), with **Mistral 7B (Apache 2.0)** as the fallback choice if license simplicity for enterprise procurement/legal review becomes a blocker — Apache 2.0 avoids any usage-tier negotiation with large bank legal teams. Offer **Phi-3.5/4-mini** as a lightweight silo-tenant option for customers wanting on-prem CPU-only deployment.

## 12.2 Domain-pretrained starting points (optional, jurisdiction/task-specific)

| Model | Domain | Use |
|---|---|---|
| **FinBERT** | Financial sentiment/NLP | Useful as a component/auxiliary classifier (e.g., news/adverse-media sentiment) rather than the generative core |
| **Legal-BERT / InLegalBERT** | Legal & Indian legal text | Strong prior for clause segmentation and legal-language NER when building the regulation-clause extraction pipeline for Indian regulators |
| **SEC-BERT** | US financial filings | Reference architecture for domain-adapting BERT-class encoders — informs how to build encoder-side classifiers even though the generative SLM is decoder-based |

These are encoder models best used as **auxiliary classifiers/extractors** feeding the pipeline (document classification, NER, clause segmentation) rather than as the generative SLM itself — the generative core should be a decoder-only instruction-tuned model from §12.1.

## 12.3 Embedding models (for RAG retrieval)

| Model | Notes |
|---|---|
| **BGE-large / BGE-M3** (BAAI) | Strong general-purpose retrieval quality, BGE-M3 adds native multilingual + multi-granularity (dense + sparse + ColBERT-style) retrieval in one model — good fit for the hybrid retrieval design in [§7.3](07-slm-rag-architecture.md) |
| **E5-mistral-7b-instruct** | Very strong retrieval quality, heavier to serve; consider for the highest-value/enterprise tier where retrieval precision matters most |
| **Nomic Embed** | Fully open (weights + training data + code), good quality/cost tradeoff, easy to self-host |
| **multilingual-e5-large** | Best default where jurisdiction coverage requires non-English regulatory text (many EU/APAC circulars) |

**Recommendation**: **BGE-M3** as the default embedding model (multilingual, hybrid-retrieval-native, right-sized for cost), with **bge-reranker-large** as the cross-encoder reranker referenced in [§7.3](07-slm-rag-architecture.md).

## 12.4 OCR / document layout models

| Model | Use |
|---|---|
| **DocTR** | Open-source OCR, good default for both printed and scanned documents |
| **LayoutLMv3** | Layout-aware document understanding — key-value extraction from structured forms (KYC IDs, application forms) where spatial position carries meaning |
| **Tesseract** | Battle-tested fallback OCR for edge cases DocTR struggles with |
| Cloud fallback (AWS Textract / GCP Document AI) | For the long tail of unusual document formats where a fully open pipeline underperforms — used selectively, with the same PII-redaction boundary applied before any downstream AI step |

## 12.5 NER / structured extraction

- Fine-tune a compact token-classification head (e.g., on top of a **DeBERTa-v3-base** or **XLM-RoBERTa** encoder for multilingual coverage) for PII detection and compliance-entity extraction — encoder models remain the right tool for token-level tagging tasks, faster and cheaper than asking the generative SLM to do span extraction.
- **spaCy** (with a fine-tuned `en_core_web_trf`-class pipeline) as the production serving framework wrapping the fine-tuned NER model — mature tooling for high-throughput, low-latency entity extraction at ingestion scale.

## 12.6 Summary: recommended default stack

| Function | Model |
|---|---|
| Generative SLM (core) | Llama 3.1 8B or Qwen 2.5 7B, LoRA/QLoRA + DPO fine-tuned per jurisdiction |
| Lightweight/on-prem SLM option | Phi-3.5/4-mini (3.8B) |
| Embeddings | BGE-M3 |
| Reranker | bge-reranker-large |
| OCR | DocTR (+ LayoutLMv3 for structured forms, Tesseract fallback) |
| NER / PII detection | Fine-tuned DeBERTa-v3-base served via spaCy |
| Auxiliary sentiment/domain classifiers | FinBERT (financial text), InLegalBERT (Indian regulatory text) |

This stack is entirely open-weight and self-hostable — no generative inference is contractually dependent on a third-party API, which is the whole point of the proprietary-SLM strategy in [§7](07-slm-rag-architecture.md): every component that touches customer PII stays inside the tenant's security boundary, permanently.
