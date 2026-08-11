---
name: llm-call
description: Which LLM provider/model to call for a reproduction that needs LLM API calls, using the free-tier keys already configured in this repo's .env.
---

# LLM call

Two providers are available via `.env` at the repo root
(`OPEN_ROUTER_API_KEY`, `AI_STUDIO_API_KEY`). Both have free tiers with
rate limits (RPM/RPD) - pick the smallest model that can do the job, and
spread load across both providers rather than hammering one.

## Verified free models (checked 2026-08-09 - re-verify before relying on
this if it's been a while, these lists change)

**OpenRouter** (`https://openrouter.ai/api/v1/models`, filter for
`pricing.prompt == "0"` or an `:free` id suffix):
- `openai/gpt-oss-20b:free` - confirmed free. Good default for small/cheap
  steps (formatting, simple extraction, per-step judging).
- `openai/gpt-oss-120b:free` - **does not exist as a free slug right now**.
  Calling it gets an explicit error back: `"This model is unavailable for
  free. The paid version is available now - use this slug instead:
  openai/gpt-oss-120b"`. Confirmed by calling the endpoint directly, not
  just reading the models list - if you've seen someone claim it's free
  (a post, older docs, a different account/region), it either changed or
  was never true for this key; trust a live call over any written claim,
  including this one after enough time has passed. Paid `gpt-oss-120b` is
  cheap regardless (~$0.04/M prompt, $0.17/M completion).
- `google/gemma-4-26b-a4b-it:free`, `google/gemma-4-31b-it:free` - also
  confirmed free. **Still count against OpenRouter's account-wide 50/day
  cap below** - no separate quota just for using a different `:free` model
  on OpenRouter. If you want a quota pool that's actually separate from
  Gemini, call Gemma directly against AI Studio instead (see below).
- Other confirmed free large-weight models worth knowing about:
  `nvidia/nemotron-3-ultra-550b-a55b:free`,
  `nvidia/nemotron-3-super-120b-a12b:free` - free frontier-scale weight if
  a task needs more capability than gpt-oss-20b can reliably provide.
- Always re-check `pricing` in the live models list before assuming
  something is still free - OpenRouter's free roster changes. Better yet,
  make one real call to the exact model slug you intend to use before
  building anything on top of it - the models-list endpoint and the
  actual completions endpoint have disagreed before (or will, or already
  did elsewhere) about what's free.

**Google AI Studio** (Gemini): use `gemini-flash-lite-latest` as the
default free-tier-friendly alias - it always points at the current
lite-flash model rather than a version that will eventually be retired.
List live models with `GET
https://generativelanguage.googleapis.com/v1beta/models?key=$AI_STUDIO_API_KEY`
if you need to confirm what's currently available to this key. Confirmed
free-tier limit as of 2026-08-09: **15 requests/minute** for
`gemini-3.5-flash-lite` (what `gemini-flash-lite-latest` currently
resolves to) - a 429 in this range includes a `retryDelay` in the body
(e.g. `"42s"`), and it's RPM not RPD, so it clears on its own within a
minute or so, unlike OpenRouter's daily cap below.

**Gemma models called directly against AI Studio get their own quota,
separate from Gemini's.** `models/gemma-4-26b-a4b-it` and
`models/gemma-4-31b-it` are both callable through the exact same
`generateContent` endpoint used for Gemini - confirmed working with this
key. Google's own published free-tier limits for Gemma on AI Studio are
reportedly far more generous than Gemini's (on the order of 30 RPM /
14,400 RPD per the current docs at
https://ai.google.dev/gemini-api/docs/rate-limits) - **not independently
verified against this key's actual ceiling** (would require deliberately
exhausting it), so confirm current numbers there before depending on the
exact figures. Practical upshot: calling Gemma via AI Studio directly is
effectively a *third* rate-limit pool, distinct from both
Gemini-via-AI-Studio (15 RPM) and anything-via-OpenRouter (50/day
account-wide) - useful to route high-volume steps to when the other two
are tight.

One implementation gotcha: Gemma's `generateContent` responses include a
leading part with `"thought": true` holding its reasoning trace before
the actual answer part - grab the non-thought part(s), not
`parts[0]["text"]` blindly, or you'll return the scratch-work instead of
the answer. `llm.py`'s `call_gemini` already filters this out. Rarer but
real: sometimes the model spends its **entire** response budget thinking
and never emits a non-thought part at all - handle that as an error
(`call_gemini` raises `LLMError`), don't assume a thought-only response
means "empty string."

**Reliability, not just quota, varies a lot between Gemma variants** -
confirmed empirically during the VeriCoT reproduction (2026-08-09):
`gemma-4-26b-a4b-it` (the MoE variant) was essentially unusable that day,
failing on all 8/8 attempted calls in one run with internal 500s or
timeouts, even with retries and a 120s timeout. Switching to
`gemma-4-31b-it` (the dense variant, same free quota class) fixed nearly
all of it - 4/5 examples completed normally in the same workload, only
one timeout. If a model is failing repeatedly despite being within quota,
try a sibling model in the same family before assuming your code is
broken or the quota numbers above are wrong - MoE/preview variants seem
more prone to backend instability than dense/stable ones.

## Model size selection

- Structured/simple sub-tasks (translate one sentence to a fixed schema,
  classify, extract) -> small model (`gpt-oss-20b:free` or
  `gemini-flash-lite-latest`).
- Need volume rather than peak quality (e.g. many small formalization
  calls in a loop) and the usual pool is tight -> route to Gemma directly
  via AI Studio (`complete(prompt, provider="gemini", model="gemma-4-31b-it")`)
  for its separate, more generous quota - see the rate limits section.
  Prefer the dense `gemma-4-31b-it` over the MoE `gemma-4-26b-a4b-it`:
  same free quota class, but the MoE variant was unreliable (see below).
- Anything requiring the paper's original frontier-model-level reasoning
  quality to be meaningfully reproduced (the paper used GPT-4/Claude/o1-class
  models for a step) -> reach for a free large-weight model
  (`nemotron-3-super-120b-a12b:free` or Gemini's non-lite tier) rather than
  silently downgrading and reporting a worse number as if it were
  comparable.
- Note this substitution explicitly in the reproduction's `README.md` /
  `RESULTS.md` - swapping the paper's frontier model for a free small one
  is a real deviation that affects how results should be read.

## Rate limits

Free tiers are RPM/RPD-limited, not just token-limited. For anything
looping over many examples: keep batch sizes small, add retry-with-backoff
on 429s, and don't parallelize aggressively against a single free-tier key.

**OpenRouter free-tier daily cap is much tighter than it looks**: without
ever having purchased credits, the `:free` models are capped at **50
requests/day total** (not per-model) - confirmed by hitting
`Rate limit exceeded: free-models-per-day` on 2026-08-09 after a modest
amount of pipeline testing (a handful of CoT verifications, each making
several calls for autoformalization retries + premise generation). Adding
**10 credits once** raises this to **1000 free requests/day** - a one-time
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
