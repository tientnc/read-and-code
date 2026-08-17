# P-FOLIO

- **Paper:** "P-FOLIO: Evaluating and Improving Logical Reasoning with Abundant Human-Written Reasoning Chains" - ACL Anthology 2024.findings-emnlp.966, arXiv:2410.09207. Built on FOLIO (ACL Anthology 2024.emnlp-main.1229, arXiv:2209.00840, github.com/Yale-LILY/FOLIO).
- **Official repo / release:** ACL Anthology attachment (`2024.findings-emnlp.966.data.zip`) & Hugging Face dataset `yale-nlp/P-FOLIO`.
- **Path taken:** **dataset paper reproduction** - rebuilt and validated the dataset artifact from raw spreadsheet dumps into clean, split-aligned JSONL format.
- **Status:** **Done** - see [`RESULTS.md`](RESULTS.md) for full metrics and audit findings.

## What the paper does

P-FOLIO adds human-written, step-by-step natural-language proofs on top of FOLIO's existing (premises, conclusion, label) instances - FOLIO itself only has the final True/False/Unknown label, no derivation. Six annotators wrote proofs (0-20 steps, 32 inference rule types) with cross-checking for quality control.

## Running the Reproduction

```bash
# 1. Download source files and rebuild structured instance records
python3 scripts/build_dataset.py

# 2. Lineage match against FOLIO, partition splits, and audit text quality
python3 scripts/verify_and_split.py
```

Clean JSONL outputs are saved to `data/`:
- `data/p-folio-raw.jsonl` (1,438 records)
- `data/p-folio-train.jsonl` (629 records)
- `data/p-folio-dev.jsonl` (76 records)
- `data/p-folio-test.jsonl` (733 records)
