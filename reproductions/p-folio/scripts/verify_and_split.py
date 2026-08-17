"""
P-FOLIO Verification and Split Reconstruction
Matches P-FOLIO instances against official FOLIO splits (train/dev) to reconstruct
lineage, assign splits (train, dev, test), perform text quality & encoding checks,
and generate clean partition files.
"""

import collections
import json
import os
import re
import unicodedata

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_FILE = os.path.join(DATA_DIR, "p-folio-raw.jsonl")
FOLIO_TRAIN_FILE = os.path.join(DATA_DIR, "folio-train.jsonl")
FOLIO_DEV_FILE = os.path.join(DATA_DIR, "folio-validation.jsonl")

TRAIN_OUT = os.path.join(DATA_DIR, "p-folio-train.jsonl")
DEV_OUT = os.path.join(DATA_DIR, "p-folio-dev.jsonl")
TEST_OUT = os.path.join(DATA_DIR, "p-folio-test.jsonl")


def normalize_text(text):
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t.strip()


def normalize_premises(premises_list):
    norm = [normalize_text(p) for p in premises_list if p.strip()]
    return tuple(sorted(norm))


def normalize_fol(fol_str):
    if not fol_str:
        return ""
    t = fol_str.replace("→", "->").replace("¬", "!").replace("∧", "&").replace("∨", "|").replace("⊕", "^")
    t = re.sub(r"\s+", "", t.lower())
    return t


def load_folio_set(filepath):
    dataset = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                dataset.append(json.loads(line))
    return dataset


def build_lookups(folio_train, folio_dev):
    exact_map = {}
    conc_map = collections.defaultdict(list)
    fol_map = {}

    for item in folio_train:
        p_key = normalize_premises(item.get("premises", []))
        c_key = normalize_text(item.get("conclusion", ""))
        lbl = item.get("label", "").strip().capitalize()
        p_fol_key = tuple(sorted(normalize_fol(p) for p in item.get("premises-FOL", [])))

        exact_map[(p_key, c_key, lbl)] = ("train", item.get("example_id"))
        conc_map[(c_key, lbl)].append(("train", item.get("example_id"), set(" ".join(p_key).split())))
        if p_fol_key:
            fol_map[(p_fol_key, lbl)] = ("train", item.get("example_id"))

    for item in folio_dev:
        p_key = normalize_premises(item.get("premises", []))
        c_key = normalize_text(item.get("conclusion", ""))
        lbl = item.get("label", "").strip().capitalize()
        p_fol_key = tuple(sorted(normalize_fol(p) for p in item.get("premises-FOL", [])))

        exact_map[(p_key, c_key, lbl)] = ("dev", item.get("example_id"))
        conc_map[(c_key, lbl)].append(("dev", item.get("example_id"), set(" ".join(p_key).split())))
        if p_fol_key:
            fol_map[(p_fol_key, lbl)] = ("dev", item.get("example_id"))

    return exact_map, conc_map, fol_map


def check_encoding_issues(text):
    issues = []
    if "\ufffd" in text:
        issues.append("contains_replacement_char_U+FFFD")
    if re.search(r"Ã[\x80-\xbf]", text):
        issues.append("mojibake_utf8_as_latin1")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text):
        issues.append("non_printable_control_char")
    return issues


def verify_and_split():
    print(f"[loading] raw P-FOLIO instances from {RAW_FILE}...")
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        pfolio_instances = [json.loads(line) for line in f if line.strip()]

    folio_train = load_folio_set(FOLIO_TRAIN_FILE)
    folio_dev = load_folio_set(FOLIO_DEV_FILE)
    print(f"[loaded] FOLIO train: {len(folio_train)} items, FOLIO dev: {len(folio_dev)} items")

    exact_map, conc_map, fol_map = build_lookups(folio_train, folio_dev)

    train_instances = []
    dev_instances = []
    test_instances = []

    text_encoding_flags = 0
    empty_proof_count = 0
    duplicate_instance_ids = set()
    seen_ids = set()

    match_exact_train = 0
    match_exact_dev = 0
    match_fuzzy_train = 0
    match_fuzzy_dev = 0
    match_fol_train = 0
    match_fol_dev = 0

    for inst in pfolio_instances:
        inst_id = inst["instance_id"]
        if inst_id in seen_ids:
            duplicate_instance_ids.add(inst_id)
        seen_ids.add(inst_id)

        if not inst["proof"]:
            empty_proof_count += 1

        all_nl_text = " ".join(inst["premises"]) + " " + inst["conclusion"] + " " + " ".join(
            step.get("derivation", "") for step in inst["proof"]
        )
        enc_issues = check_encoding_issues(all_nl_text)
        if enc_issues:
            text_encoding_flags += 1

        p_key = normalize_premises(inst["premises"])
        c_key = normalize_text(inst["conclusion"])
        lbl = inst["label"].strip().capitalize()

        matched_split = None
        folio_ref = None

        # 1. Exact NL matching
        if (p_key, c_key, lbl) in exact_map:
            matched_split, folio_ref = exact_map[(p_key, c_key, lbl)]
            if matched_split == "train":
                match_exact_train += 1
            else:
                match_exact_dev += 1

        # 2. Conclusion match + high premise overlap
        elif (c_key, lbl) in conc_map:
            p_words = set(" ".join(p_key).split())
            best_split, best_ref, best_score = None, None, 0.0
            for sp, ref, cand_words in conc_map[(c_key, lbl)]:
                score = len(p_words & cand_words) / max(1, len(p_words | cand_words))
                if score > best_score:
                    best_score = score
                    best_split = sp
                    best_ref = ref
            if best_score >= 0.5:
                matched_split = best_split
                folio_ref = best_ref
                if matched_split == "train":
                    match_fuzzy_train += 1
                else:
                    match_fuzzy_dev += 1

        # 3. FOL formula matching fallback
        if not matched_split and inst.get("premises_fol"):
            p_fol_key = tuple(sorted(normalize_fol(p) for p in inst["premises_fol"]))
            if (p_fol_key, lbl) in fol_map:
                matched_split, folio_ref = fol_map[(p_fol_key, lbl)]
                if matched_split == "train":
                    match_fol_train += 1
                else:
                    match_fol_dev += 1

        # 4. Inferred test partition
        if not matched_split:
            matched_split = "test"

        inst["split"] = matched_split
        inst["folio_matched_example_id"] = folio_ref

        if matched_split == "train":
            train_instances.append(inst)
        elif matched_split == "dev":
            dev_instances.append(inst)
        else:
            test_instances.append(inst)

    def write_jsonl(path, items):
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    write_jsonl(TRAIN_OUT, train_instances)
    write_jsonl(DEV_OUT, dev_instances)
    write_jsonl(TEST_OUT, test_instances)

    total = len(pfolio_instances)
    print("=" * 60)
    print("P-FOLIO VERIFICATION AND SPLIT AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total instances in raw dump: {total}")
    print(f"Paper claimed total: 1430 (Discrepancy: +{total - 1430} in spreadsheet dump)")
    print(f"Train split: {len(train_instances)} ({len(train_instances)/total*100:.2f}%) [Exact NL: {match_exact_train}, Fuzzy: {match_fuzzy_train}, FOL: {match_fol_train}]")
    print(f"Dev split:   {len(dev_instances)} ({len(dev_instances)/total*100:.2f}%) [Exact NL: {match_exact_dev}, Fuzzy: {match_fuzzy_dev}, FOL: {match_fol_dev}]")
    print(f"Test split:  {len(test_instances)} ({len(test_instances)/total*100:.2f}%) (Inferred unreleased test split)")
    print(f"Instances with proof steps: {total - empty_proof_count} / {total}")
    print(f"Instances with encoding issues: {text_encoding_flags}")
    print(f"Duplicate instance IDs: {len(duplicate_instance_ids)}")
    print("=" * 60)
    print(f"[written] {TRAIN_OUT} ({len(train_instances)} records)")
    print(f"[written] {DEV_OUT} ({len(dev_instances)} records)")
    print(f"[written] {TEST_OUT} ({len(test_instances)} records)")


if __name__ == "__main__":
    verify_and_split()
