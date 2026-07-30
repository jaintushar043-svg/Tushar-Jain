# 10. Cost Estimation

All figures in USD, order-of-magnitude estimates for planning purposes, not vendor quotes.

## 10.1 Team cost by phase (fully-loaded, blended annual)

| Phase | Headcount | Blended fully-loaded cost/head/yr | Annualized team cost |
|---|---|---|---|
| Phase 0–1 (MVP) | 8 | $130K | ~$1.04M/yr (run ~6 months → ~$520K) |
| Phase 2 (Growth) | 18 | $135K | ~$2.4M/yr |
| Phase 3 (Scale) | 35 | $140K | ~$4.9M/yr |
| Phase 4 (Enterprise) | 70 | $145K | ~$10.2M/yr |

(Blended rate accounts for a mix of engineering, AI/ML, compliance SME, and GTM hires; SME/compliance content roles are typically cheaper per-head than senior AI/ML, engineering skews the blend up.)

## 10.2 Infrastructure cost by phase (monthly, AWS list pricing, pool-tier baseline)

| Item | MVP (Phase 1) | Growth (Phase 2) | Scale (Phase 3) |
|---|---|---|---|
| EKS control plane + app nodes | $800 | $2,500 | $8,000 |
| GPU inference (SLM serving)* | $2,200 (1× g5.2xlarge on-demand-equivalent, reserved) | $6,500 (2–3 GPU nodes, mixed reserved/spot) | $22,000 (multi-region GPU pools) |
| Aurora PostgreSQL (+ pgvector) | $600 | $2,200 | $7,500 |
| OpenSearch | $300 | $900 | $2,800 |
| MSK (Kafka) | $400 | $1,200 | $3,500 |
| S3 + Object Lock (WORM audit) | $150 | $500 | $1,800 |
| Redis (ElastiCache) | $150 | $400 | $1,200 |
| Data transfer, CDN, WAF | $200 | $700 | $2,200 |
| Observability stack | $250 | $700 | $2,000 |
| **Monthly total** | **~$5,050** | **~$15,600** | **~$51,000** |
| **Annualized** | **~$60K** | **~$187K** | **~$612K** |

\*GPU inference is the dominant variable cost and scales with tenant count × document/query volume, not linearly with headcount — this is the line item to model most carefully per deal.

Silo-tier tenants are typically **billed cost-plus** (dedicated infra passed through + margin) rather than absorbed into shared platform cost, since a dedicated EKS cluster + GPU pool per silo tenant runs roughly $8K–$25K/month depending on volume and is priced into that tenant's enterprise contract.

## 10.3 Fine-tuning & model development cost

| Item | Estimate |
|---|---|
| LoRA/QLoRA fine-tuning run (single adapter, 7–8B model, A100/H100 spot cluster) | $500–$2,000 per run |
| Full DPO fine-tuning cycle (data curation + training + eval) | $3,000–$8,000 per cycle |
| Continued pre-training on regulatory corpus (one-time, per base-model refresh) | $15,000–$40,000 |
| Human annotation / preference labeling (compliance SME review, ongoing) | $8,000–$15,000/month at scale |

Because fine-tuning uses parameter-efficient methods (LoRA/QLoRA/DPO on 7–8B models) rather than full pre-training, per-cycle training cost is a rounding error next to team and inference-serving cost — the real ongoing cost center is **human-reviewed training data curation**, which is also the moat.

## 10.4 Third-party/data licensing (recurring)

| Vendor category | Typical cost |
|---|---|
| ID verification / liveness (per check) | $1–$3/check |
| Sanctions/PEP/adverse-media screening (per screen or platform fee) | $0.50–$2/screen, or $3K–$15K/month platform license depending on tenant volume |
| Regulatory content feeds (where not free/public) | $2K–$10K/month per jurisdiction, tier-dependent |

These are typically passed through to the tenant (metered) rather than absorbed, since screening volume scales with the tenant's own customer base.

## 10.5 Unit economics (illustrative, mid-market pool tenant)

| Metric | Estimate |
|---|---|
| Avg GPU inference cost per KYC case (ingest + classify + risk rec) | $0.03–$0.08 |
| Avg cost per AML alert processed (scoring + explanation) | $0.02–$0.05 |
| Avg cost per RAG Q&A query | $0.01–$0.03 |
| Target gross margin at scale (Phase 3+) | 75–82% (SaaS-typical, achievable once shared GPU pools amortize across tenants and fine-tuning cost is spread over adapter reuse) |

## 10.6 Illustrative cumulative burn (24 months)

| Phase | Duration | Team | Infra | Total (period) |
|---|---|---|---|---|
| 0–1 (MVP) | 6 mo | $520K | $30K | ~$550K |
| 2 (Growth) | 6 mo | $1.2M | $94K | ~$1.3M |
| 3 (Scale) | 6 mo | $2.45M | $306K | ~$2.75M |
| 4 (Enterprise, first 6mo) | 6 mo | $5.1M | $500K+ | ~$5.6M |
| **Total, 24 months** | | | | **~$10.2M** |

This is broadly consistent with a Seed → Series A raise (~$3–5M) covering Phases 0–2, and a Series A/B (~$10–20M) funding Phases 3–4 — typical for a vertical AI SaaS company targeting regulated enterprise from day one.
