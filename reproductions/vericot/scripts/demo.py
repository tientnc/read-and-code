"""Run VeriCoT's core loop on a handful of ProofWriter examples: generate a
CoT with the executor model, verify it, report per-example pass/fail and
whether the verified answer matches the gold answer (mirrors the paper's
pass rate / verifier precision / VCAR / task accuracy, at tiny sample
size -- see RESULTS.md for the actual numbers and caveats)."""

import argparse
import sys

from vericot.autoformalize import UntranslatableError
from vericot.data import fetch_proofwriter_rows, generate_cot
from vericot.pipeline import verify_cot

OPTION_TO_BOOL = {"A": "True", "B": "False", "C": "Unknown"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--provider", default="openrouter", choices=["openrouter", "gemini"])
    parser.add_argument("--model", default=None, help="override the provider's default model, e.g. gemma-4-26b-a4b-it")
    args = parser.parse_args()

    rows = fetch_proofwriter_rows(n=args.n, offset=args.offset)
    n_pass = 0
    n_verified_correct = 0
    n_task_correct = 0

    for row in rows:
        gold = OPTION_TO_BOOL.get(row["answer"], row["answer"])
        print(f"\n=== {row['id']} ===")
        print("Q:", row["question"])
        print("Gold:", gold)

        try:
            steps, model_answer = generate_cot(
                row["context"], row["question"], provider=args.provider, model=args.model
            )
        except Exception as e:  # noqa: BLE001 -- demo script, surface and move on
            print("  CoT generation failed:", e)
            continue

        print("Model answer:", model_answer)
        task_correct = (model_answer or "").strip().lower() == gold.lower()
        n_task_correct += int(task_correct)

        try:
            result = verify_cot(row["context"], steps, provider=args.provider, model=args.model)
        except Exception as e:  # noqa: BLE001
            print("  verification crashed:", e)
            continue

        for r in result.steps:
            print(f"  [{r.status}] {r.step_text}")
            if r.premise:
                print("     premise used:", r.premise)
            if r.detail:
                print("     detail:", r.detail)

        print("VeriCoT verdict: VALID" if result.valid else "VeriCoT verdict: INVALID")
        n_pass += int(result.valid)
        if result.valid and task_correct:
            n_verified_correct += 1

    n = len(rows)
    if n == 0:
        print("No rows fetched.")
        return
    print("\n=== Summary ===")
    print(f"n = {n}")
    print(f"pass rate         = {100 * n_pass / n:.1f}%  ({n_pass}/{n})")
    print(f"task accuracy     = {100 * n_task_correct / n:.1f}%  ({n_task_correct}/{n})")
    if n_pass:
        print(f"verifier precision = {100 * n_verified_correct / n_pass:.1f}%  ({n_verified_correct}/{n_pass})")
    print(f"VCAR              = {100 * n_verified_correct / n:.1f}%  ({n_verified_correct}/{n})")


if __name__ == "__main__":
    sys.exit(main())
