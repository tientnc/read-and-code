---
name: llm-call
description: Which LLM provider/model to call for a reproduction that needs LLM API calls, using the free-tier keys already configured in this repo's .env.
---

# LLM call

Two providers are available via `.env` at the repo root
(`OPEN_ROUTER_API_KEY`, `AI_STUDIO_API_KEY`). Both have free tiers with
rate limits (RPM/RPD) — pick the smallest model that can do the job, and
spread load across both providers rather than hammering one.

## Verified free models (checked 2026-08-09 — re-verify before relying on
this if it's been a while, these lists change)

**OpenRouter** (`https://openrouter.ai/api/v1/models`, filter for
`pricing.prompt == "0"` or an `:free` id suffix):
- `openai/gpt-oss-20b:free` — confirmed free. Good default for small/cheap
  steps (formatting, simple extraction, per-step judging).
- `openai/gpt-oss-120b` — **not free**, despite what you might assume from
  gpt-oss-20b having a free variant. Cheap either way (~$0.04/M prompt,
  $0.17/M completion) but don't treat it as free-tier.
- Other confirmed free large-weight models worth knowing about:
  `nvidia/nemotron-3-ultra-550b-a55b:free`,
  `nvidia/nemotron-3-super-120b-a12b:free` — free frontier-scale weight if
  a task needs more capability than gpt-oss-20b can reliably provide.
- Always re-check `pricing` in the live models list before assuming
  something is still free — OpenRouter's free roster changes.

**Google AI Studio** (Gemini): use `gemini-flash-lite-latest` as the
default free-tier-friendly alias — it always points at the current
lite-flash model rather than a version that will eventually be retired.
List live models with `GET
https://generativelanguage.googleapis.com/v1beta/models?key=$AI_STUDIO_API_KEY`
if you need to confirm what's currently available to this key. Confirmed
free-tier limit as of 2026-08-09: **15 requests/minute** for
`gemini-3.5-flash-lite` (what `gemini-flash-lite-latest` currently
resolves to) — a 429 in this range includes a `retryDelay` in the body
(e.g. `"42s"`), and it's RPM not RPD, so it clears on its own within a
minute or so, unlike OpenRouter's daily cap below.

## Model size selection

- Structured/simple sub-tasks (translate one sentence to a fixed schema,
  classify, extract) → small model (`gpt-oss-20b:free` or
  `gemini-flash-lite-latest`).
- Anything requiring the paper's original frontier-model-level reasoning
  quality to be meaningfully reproduced (the paper used GPT-4/Claude/o1-class
  models for a step) → reach for a free large-weight model
  (`nemotron-3-super-120b-a12b:free` or Gemini's non-lite tier) rather than
  silently downgrading and reporting a worse number as if it were
  comparable.
- Note this substitution explicitly in the reproduction's `README.md` /
  `RESULTS.md` — swapping the paper's frontier model for a free small one
  is a real deviation that affects how results should be read.

## Rate limits

Free tiers are RPM/RPD-limited, not just token-limited. For anything
looping over many examples: keep batch sizes small, add retry-with-backoff
on 429s, and don't parallelize aggressively against a single free-tier key.

**OpenRouter free-tier daily cap is much tighter than it looks**: without
ever having purchased credits, the `:free` models are capped at **50
requests/day total** (not per-model) — confirmed by hitting
`Rate limit exceeded: free-models-per-day` on 2026-08-09 after a modest
amount of pipeline testing (a handful of CoT verifications, each making
several calls for autoformalization retries + premise generation). Adding
**10 credits once** raises this to **1000 free requests/day** — a one-time
top-up, not a subscription, and worth doing before any real run rather
than mid-run. Reset is midnight UTC (`X-RateLimit-Reset` header on the 429).
Check current key status any time with:
`curl -s https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer $OPEN_ROUTER_API_KEY"`
(`usage_daily`, `is_free_tier` fields).

Any pipeline that autoformalizes multiple CoT steps, each potentially
retrying autoformalization up to 3x and generating multiple candidate
premises (each itself autoformalized), burns through 50 requests in a
single multi-step example. **Practical consequence**: for anything beyond
trivial smoke-testing, either add the $10 OpenRouter credit, or spread
calls across both providers (AI Studio has a separate quota from
OpenRouter, so alternating providers roughly doubles the effective daily
budget), or budget your test runs assuming ~50/day and batch accordingly.
