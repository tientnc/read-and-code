# CI Checks

`.github/workflows/ci.yml` is configured to run commands from `Makefile` lines 91-103 on each commit. Adjust the executed commands there if needed.

Set `USE_CHAT_CACHE=True` in `.env` to make a second repair pass faster.

## Ruff

Global ignored rules are configured in `pyproject.toml`.

Ruff rules are generally easy to fix, and many can be auto-fixed.

For selected rules, add a local inline suppression such as `# noqa E234,ANN001`.

Rules that are harder to fix:

- Exception handlers should handle each exception type specifically instead of catching all `Exception`.
- `subprogress()` should check whether a command is safe before calling it.

Rule list: [ruff rules](https://docs.astral.sh/ruff/rules/)

## Mypy

Mypy checks Python type annotations. It often requires structural changes or edits across multiple files, so automatic fixes are less effective.

Local suppression: `# type: ignore`

Rule list: [mypy rules](https://mypy.readthedocs.io/en/stable/error_code_list.html)

## Possible Improvements

- Add support for checking a specific folder.
- Add an edit option that opens `vim` so the user can directly modify this part of the code.
- When displaying fixes, remove the `Original Code` section and mark the edited diff lines with `^^^^^^` underneath the code so the repair location is easier to inspect.
- The current flow repairs everything linearly before returning control to the user. It could be changed to process repairs in background threads/processes and stream completed repairs to the terminal for user review.
