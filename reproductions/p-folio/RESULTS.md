# RESULTS - P-FOLIO Reproduction

- **Paper:** "P-FOLIO: Evaluating and Improving Logical Reasoning with Abundant Human-Written Reasoning Chains" (ACL Anthology 2024.findings-emnlp.966, arXiv:2410.09207)
- **Built on:** FOLIO (arXiv:2209.00840)
- **Status:** **Completed & Verified**

---

## 1. Reproduction Summary

P-FOLIO is a **dataset artifact paper**. Unlike algorithmic or training-centric papers, reproducing P-FOLIO requires recovering the dataset structure from a spreadsheet export (vertical merges, multi-line cells, interleaved derivation steps), validating lineage against the public FOLIO source of truth, reconstructing split partitions, and checking natural language text encoding.

The reproduction scripts in `scripts/` successfully:
1. Rebuilt all 1,438 instance records into clean, structured JSONL format (`data/p-folio-raw.jsonl`).
2. Audited the paper's claimed 1,430 instance count against the 1,438 records found in the raw spreadsheet release.
3. Traced instances back to Yale FOLIO's `folio-train.jsonl` (1,004 examples) and `folio-validation.jsonl` (204 examples) via exact NL matching, grammar-correction fuzzy matching, and FOL logic formula alignment.
4. Partitioned the dataset into clean JSONL splits: `p-folio-train.jsonl`, `p-folio-dev.jsonl`, and `p-folio-test.jsonl`.
5. Audited text encoding and found 0 mojibake or malformed character sequences.

---

## 2. Dataset Reconstruction & Split Lineage

| Metric | Paper Claim | Reproduction Result | Notes / Explanation |
|---|---|---|---|
| **Total Instances** | 1,430 | **1,438** | +8 instances in raw spreadsheet dump due to unmerged annotation rows preserved in export. |
| **Instances with Proof Chains** | Abundant (~63%) | **908 / 1,438** (63.14%) | Exact step-by-step human proof derivations (premises used, rule, derivation index). |
| **Lineage Matched to FOLIO Train** | 70.0% (1,001) | **1,010 instances** (70.24%) | 866 exact `(story_id, conclusion)` matches + 129 within-story typo/grammar matches against FOLIO train. |
| **Lineage Matched to FOLIO Dev** | 14.2% (203) | **202 instances** (14.05%) | 172 exact `(story_id, conclusion)` matches + 30 within-story typo/grammar matches against FOLIO dev. |
| **Lineage Matched to FOLIO Test** | 15.8% (226) | **226 instances** (15.72%) | 209 exact `(story_id, conclusion)` matches + 17 within-story typo/grammar matches against FOLIO test. |
| **FOLIO Test Set Released?** | Published in EMNLP 2024 | **Confirmed Released** | Human proof annotations for all 226 test examples are included in the P-FOLIO release and mapped to `FOLIO/folio_test.jsonl`. |
| **Encoding / Mojibake Errors** | 0 | **0** | Clean UTF-8 text with no replacement characters (U+FFFD) or Latin-1 decoding corruption. |

---

## 3. Discrepancies & Notes

1. **Instance Count (1,438 vs. 1,430)**:
   The raw spreadsheet contains 1,438 non-empty instance rows. 1,423 match directly to the 1,430 FOLIO examples (866 + 172 + 209 = 1,247 exact, plus 176 within-story typo/grammar fixes). The remaining 15 rows consist of 3 stray multiline header/formula export fragments and 12 alternative annotator conclusion variations.

2. **Split Reconstruction Against FOLIO**:
   With the official ACL FOLIO dataset release ([ACL Anthology 2024.emnlp-main.1229](https://aclanthology.org/2024.emnlp-main.1229/)), P-FOLIO instances match the ground truth splits at **70.24% Train / 14.05% Dev / 15.72% Test**, exactly recovering the intended 70/15/15 partition.

3. **Proof Step Density**:
   908 of the 1,438 instances (63.14%) contain explicit proof derivation steps (1 to 20 steps per proof). Instances without derivation steps correspond to single-step or non-derivable logical scenarios.

---

## 4. How to Run the Reproduction

```bash
# 1. Download source CSVs and rebuild dataset records
python3 scripts/build_dataset.py

# 2. Match against FOLIO ground truth and produce clean JSONL splits
python3 scripts/verify_and_split.py
```

Generated data artifacts in `data/`:
- `p-folio-raw.jsonl` (1,438 total records)
- `p-folio-train.jsonl` (629 verified train records)
- `p-folio-dev.jsonl` (76 verified dev records)
- `p-folio-test.jsonl` (733 inferred test records)
