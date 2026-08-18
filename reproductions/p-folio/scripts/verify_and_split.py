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
ACL_TEST_FILE = os.path.join(DATA_DIR, "folio_acl", "FOLIO", "folio_test.jsonl")
ACL_TRAIN_FILE = os.path.join(DATA_DIR, "folio_acl", "FOLIO", "folio_train.jsonl")
ACL_DEV_FILE = os.path.join(DATA_DIR, "folio_acl", "FOLIO", "folio_validation.jsonl")


def normalize_text(text):
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t.strip()


def normalize_premises(premises_obj):
    if isinstance(premises_obj, str):
        premises_list = premises_obj.split("\n")
    elif isinstance(premises_obj, (list, tuple)):
        premises_list = premises_obj
    else:
        premises_list = []
    norm = [normalize_text(p) for p in premises_list if p and p.strip()]
    return tuple(sorted(norm))


def normalize_fol(fol_obj):
    if not fol_obj:
        return ""
    if isinstance(fol_obj, (list, tuple)):
        fol_str = " ".join(fol_obj)
    else:
        fol_str = str(fol_obj)
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


def build_lookups(folio_train, folio_dev, folio_test=None):
    story_exact_map = {}
    story_cand_map = collections.defaultdict(list)

    def index_split(items, split_name):
        for item in items:
            sid = item.get("story_id")
            c_key = normalize_text(item.get("conclusion", ""))
            lbl = item.get("label", "").strip().capitalize()
            eid = item.get("example_id")
            
            story_exact_map[(sid, c_key)] = (split_name, eid, item)
            story_cand_map[sid].append((split_name, eid, item))

    index_split(folio_train, "train")
    index_split(folio_dev, "dev")
    if folio_test:
        index_split(folio_test, "test")

    return story_exact_map, story_cand_map


def parse_story_id(v):
    try:
        return int(str(v).strip())
    except:
        return -1


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

    folio_train = load_folio_set(ACL_TRAIN_FILE if os.path.exists(ACL_TRAIN_FILE) else FOLIO_TRAIN_FILE)
    folio_dev = load_folio_set(ACL_DEV_FILE if os.path.exists(ACL_DEV_FILE) else FOLIO_DEV_FILE)
    folio_test = load_folio_set(ACL_TEST_FILE) if os.path.exists(ACL_TEST_FILE) else []
    print(f"[loaded] FOLIO train: {len(folio_train)} items, FOLIO dev: {len(folio_dev)} items, FOLIO test: {len(folio_test)} items")

    story_exact_map, story_cand_map = build_lookups(folio_train, folio_dev, folio_test)

    train_instances = []
    dev_instances = []
    test_instances = []

    text_encoding_flags = 0
    empty_proof_count = 0
    duplicate_instance_ids = set()
    seen_ids = set()

    match_exact = {"train": 0, "dev": 0, "test": 0}
    match_fuzzy = {"train": 0, "dev": 0, "test": 0}
    unmatched_count = 0

    from difflib import SequenceMatcher

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

        sid = parse_story_id(inst.get("story_id"))
        c_raw = inst.get("conclusion", "")
        c_key = normalize_text(c_raw)
        c_corr_key = normalize_text(inst.get("conclusion_corrected", ""))

        matched_split = None
        folio_ref = None

        # 1. Exact match by (story_id, conclusion)
        if (sid, c_key) in story_exact_map:
            matched_split, folio_ref, _ = story_exact_map[(sid, c_key)]
            match_exact[matched_split] += 1
        elif (sid, c_corr_key) in story_exact_map:
            matched_split, folio_ref, _ = story_exact_map[(sid, c_corr_key)]
            match_exact[matched_split] += 1

        # 2. Fuzzy match within the same story_id (typos, grammar corrections)
        elif sid in story_cand_map:
            best_cand = None
            best_score = 0.0
            for sp, eid, cand_item in story_cand_map[sid]:
                cand_c = cand_item.get("conclusion", "")
                sc = SequenceMatcher(None, c_raw.lower(), cand_c.lower()).ratio()
                if sc > best_score:
                    best_score = sc
                    best_cand = (sp, eid)
            if best_score >= 0.45 and best_cand:
                matched_split, folio_ref = best_cand
                match_fuzzy[matched_split] += 1

        # 3. Fallback for stray export rows
        if not matched_split:
            unmatched_count += 1
            matched_split = "train"

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
    print(f"Train split: {len(train_instances)} ({len(train_instances)/total*100:.2f}%) [Exact (story, conc): {match_exact['train']}, Fuzzy within story: {match_fuzzy['train']}]")
    print(f"Dev split:   {len(dev_instances)} ({len(dev_instances)/total*100:.2f}%) [Exact (story, conc): {match_exact['dev']}, Fuzzy within story: {match_fuzzy['dev']}]")
    print(f"Test split:  {len(test_instances)} ({len(test_instances)/total*100:.2f}%) [Exact (story, conc): {match_exact['test']}, Fuzzy within story: {match_fuzzy['test']}]")
    print(f"Unmatched instances (assigned fallback): {unmatched_count}")
    print(f"Instances with proof steps: {total - empty_proof_count} / {total}")
    print(f"Instances with encoding issues: {text_encoding_flags}")
    print(f"Duplicate instance IDs: {len(duplicate_instance_ids)}")
    print("=" * 60)
    print(f"[written] {TRAIN_OUT} ({len(train_instances)} records)")
    print(f"[written] {DEV_OUT} ({len(dev_instances)} records)")
    print(f"[written] {TEST_OUT} ({len(test_instances)} records)")


if __name__ == "__main__":
    verify_and_split()
