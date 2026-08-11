"""Pull a small ProofWriter sample from the HF datasets-server API (no
`datasets` library dependency needed for a handful of rows) and generate a
CoT for each with the executor model, mirroring what the paper's Section 3.3
"direct evaluation of VeriCoT" experiment verifies."""

import json
import urllib.request

from vericot.llm import complete

DATASETS_SERVER_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=renma/ProofWriter&config=default&split=validation&offset={offset}&length={length}"
)

COT_PROMPT = """Answer the question using the reference information below. Think step by step: write a numbered list of short reasoning steps (each step a single simple sentence), then end with a final line "Answer: True/False/Unknown".

Reference information: {context}

Question: {question}"""


def fetch_proofwriter_rows(n=5, offset=0):
    url = DATASETS_SERVER_URL.format(offset=offset, length=n)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    return [r["row"] for r in data["rows"]]


def generate_cot(context, question, provider="openrouter", model=None):
    out = complete(COT_PROMPT.format(context=context, question=question), provider=provider, model=model)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    steps, answer = [], None
    for line in lines:
        if line.lower().startswith("answer:"):
            answer = line.split(":", 1)[1].strip()
            continue
        # strip leading "1.", "1)", "- " list markers
        stripped = line.lstrip("0123456789.)- ").strip()
        if stripped:
            steps.append(stripped)
    return steps, answer
