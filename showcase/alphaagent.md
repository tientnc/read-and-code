# AlphaAgent

- **Paper:** "AlphaAgent: LLM-Driven Alpha Mining with Regularized
  Exploration to Counteract Alpha Decay"
- **Official repo:** https://github.com/RndmVariableQ/AlphaAgent
- **Reproduction:** `~/AlphaAgent` (standalone repo, forked from upstream)
- **Path taken:** official code exists → fork, adapt, run locally.

Official code existed, so this followed what this framework now calls the
official-repo path: fork the upstream repo, adapt it to the local
environment (Python 3.12 venv, local Qlib CN daily data, local caches for
pip/Qlib/matplotlib), and run the CLI workflow (LLM proposes a hypothesis →
LLM turns it into factor expressions → factors run against Qlib → backtest →
feed results back into the next iteration).

Reproduced before this framework existed, so it stays as its own repo
instead of being retrofitted into `reproductions/`. See its
[README](../../AlphaAgent/README.md) for the actual setup notes.
