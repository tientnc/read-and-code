"""
P-FOLIO Dataset Rebuilder
Downloads P-FOLIO (ACL Anthology source & Hugging Face dataset) and FOLIO ground truth,
processes vertical merges and spreadsheet layout, normalizes records to target JSONL schema.
"""

import csv
import io
import json
import os
import re
import urllib.request
import zipfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "p-folio-raw.jsonl")
ACL_ZIP_URL = "https://aclanthology.org/attachments/2024.findings-emnlp.966.data.zip"
FOLIO_ACL_ZIP_URL = "https://aclanthology.org/attachments/2024.emnlp-main.1229.data.zip"
FOLIO_TRAIN_URL = "https://raw.githubusercontent.com/Yale-LILY/FOLIO/main/data/v0.0/folio-train.jsonl"
FOLIO_DEV_URL = "https://raw.githubusercontent.com/Yale-LILY/FOLIO/main/data/v0.0/folio-validation.jsonl"


def download_file(url, target_path, headers=None, timeout=20):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        print(f"[skip] {target_path} already exists ({os.path.getsize(target_path)} bytes)")
        return
    print(f"[downloading] {url} -> {target_path}...")
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read()
    with open(target_path, "wb") as f:
        f.write(content)
    print(f"[saved] {target_path} ({len(content)} bytes)")


def ensure_acl_dataset():
    csv_target = os.path.join(DATA_DIR, "LogicSpider Manual Annotation Collection - V1 - Proof Collection - All.csv")
    if os.path.exists(csv_target) and os.path.getsize(csv_target) > 0:
        return csv_target

    zip_path = os.path.join(DATA_DIR, "pfolio_acl_data.zip")
    download_file(ACL_ZIP_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA_DIR)
    return csv_target


def normalize_truth_value(raw_val):
    v = (raw_val or "").strip().upper()
    if v in ("T", "TRUE", "1"):
        return "True"
    elif v in ("F", "FALSE", "0"):
        return "False"
    elif v in ("U", "UNKNOWN", "?"):
        return "Unknown"
    return v


def clean_header_key(k):
    return re.sub(r"\s+", " ", k.replace("\n", " ")).strip()


def parse_unified_csv(csv_path):
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        raw_header = next(reader, None)
        if not raw_header:
            raise ValueError("Empty CSV file")

        col_map = {}
        for idx, col in enumerate(raw_header):
            cleaned = clean_header_key(col)
            col_map[cleaned] = idx

        def get_val(row, *aliases):
            for alias in aliases:
                idx = col_map.get(clean_header_key(alias))
                if idx is not None and idx < len(row):
                    val = row[idx].strip()
                    if val:
                        return val
            return ""

        current_story_id = None
        current_premises_nl = []
        current_premises_raw = ""
        current_premises_fol = []
        current_instance = None
        instances = []

        for row_idx, row in enumerate(reader):
            if not any(cell.strip() for cell in row):
                continue

            raw_story_id = get_val(row, "story_id")
            if raw_story_id:
                if raw_story_id == "(":
                    continue
                if raw_story_id != current_story_id:
                    current_story_id = raw_story_id
                    current_premises_nl = []
                    current_premises_raw = ""
                    current_premises_fol = []

            # Premises updates
            p_nl_corr = get_val(row, "Corrected Premises - NL")
            p_nl_raw = get_val(row, "Premises - NL")
            p_nl = p_nl_corr if p_nl_corr else p_nl_raw
            if p_nl:
                current_premises_nl = [p.strip() for p in p_nl.split("\n") if p.strip()]
                current_premises_raw = p_nl

            p_fol_opt = get_val(row, "Premises - FOL - corrected - optimized")
            p_fol_corr = get_val(row, "Premises - FOL - corrected")
            p_fol_raw = get_val(row, "Premises - FOL")
            p_fol = p_fol_opt or p_fol_corr or p_fol_raw
            if p_fol:
                current_premises_fol = [p.strip() for p in p_fol.split("\n") if p.strip()]

            raw_tv = get_val(row, "Truth Value")
            if raw_tv:
                if current_instance is not None:
                    current_instance["num_proof_steps"] = len(current_instance["proof"])
                    instances.append(current_instance)
                    current_instance = None

                c_nl_corr = get_val(row, "Corrected Conclusions - NL")
                c_nl_raw = get_val(row, "Conclusions - NL")
                conclusion = c_nl_corr if c_nl_corr else c_nl_raw

                c_fol_opt = get_val(row, "Corrected Conclusions - FOL - optimized")
                c_fol_corr = get_val(row, "Corrected Conclusion - FOL")
                c_fol_raw = get_val(row, "Conclusion - FOL")
                conclusion_fol = c_fol_opt or c_fol_corr or c_fol_raw

                story_inst_count = sum(1 for inst in instances if inst["story_id"] == current_story_id)
                instance_id = f"pfolio-{current_story_id}-{story_inst_count}"

                current_instance = {
                    "instance_id": instance_id,
                    "story_id": str(current_story_id),
                    "premises": list(current_premises_nl),
                    "premises_raw_unsplit": current_premises_raw,
                    "premises_fol": list(current_premises_fol),
                    "conclusion": conclusion,
                    "conclusion_raw": c_nl_raw or c_nl_corr,
                    "conclusion_fol": conclusion_fol,
                    "label": normalize_truth_value(raw_tv),
                    "raw_truth_value": raw_tv,
                    "proof": [],
                    "qc_flags": {
                        "factuality": get_val(row, "factuality"),
                        "bias": get_val(row, "bias"),
                        "nl_grammar_mechanics_check": get_val(row, "NL_grammar_mechanics_check"),
                        "fol": get_val(row, "FOL"),
                        "proof_correctness": get_val(row, "proof_correctness"),
                        "comment_on_fol": get_val(row, "comment on FOL"),
                        "comment_on_bias": get_val(row, "comment on Bias")
                    }
                }

                derivation = get_val(row, "Derivation - Corrected", "Derivation")
                inf_rule = get_val(row, "Inference rule")
                if derivation or inf_rule:
                    current_instance["proof"].append({
                        "premises_used": get_val(row, "Premises used", "Premises \nused"),
                        "derivation": derivation,
                        "derivation_index": get_val(row, "Derivation index", "Derivation \nindex"),
                        "inference_rule": inf_rule
                    })
            else:
                if current_instance is not None:
                    derivation = get_val(row, "Derivation - Corrected", "Derivation")
                    inf_rule = get_val(row, "Inference rule")
                    if derivation or inf_rule:
                        current_instance["proof"].append({
                            "premises_used": get_val(row, "Premises used", "Premises \nused"),
                            "derivation": derivation,
                            "derivation_index": get_val(row, "Derivation index", "Derivation \nindex"),
                            "inference_rule": inf_rule
                        })

        if current_instance is not None:
            current_instance["num_proof_steps"] = len(current_instance["proof"])
            instances.append(current_instance)

    return instances


def ensure_folio_acl():
    acl_dir = os.path.join(DATA_DIR, "folio_acl")
    test_file = os.path.join(acl_dir, "FOLIO", "folio_test.jsonl")
    if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
        return acl_dir
    
    zip_path = os.path.join(DATA_DIR, "folio_acl_data.zip")
    download_file(FOLIO_ACL_ZIP_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(acl_dir)
    return acl_dir


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    download_file(FOLIO_TRAIN_URL, os.path.join(DATA_DIR, "folio-train.jsonl"))
    download_file(FOLIO_DEV_URL, os.path.join(DATA_DIR, "folio-validation.jsonl"))
    ensure_folio_acl()

    csv_path = ensure_acl_dataset()
    print(f"[parsing] {csv_path}...")
    instances = parse_unified_csv(csv_path)
    print(f"[parsed] Total rebuilt instances: {len(instances)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for inst in instances:
            f.write(json.dumps(inst, ensure_ascii=False) + "\n")
    print(f"[written] {OUTPUT_FILE} ({len(instances)} records)")


if __name__ == "__main__":
    main()
