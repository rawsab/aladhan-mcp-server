---
name: verify
description: Verify the aladhan-mcp server works end to end. Runs pytest, then starts the server over stdio and calls every tool against the live Aladhan API. Use after changing tools, dependencies, or before a release.
---

1. Create a fresh venv in the scratchpad (or reuse one from this session) and install the package:
   `uv venv -q --python 3.12 <venv> && VIRTUAL_ENV=<venv> uv pip install -q -e ".[dev]"`
2. Run `<venv>/bin/python -m pytest -q`. Report failures with their output.
3. Run `<venv>/bin/python .claude/skills/verify/e2e.py`. It lists the server's tools and calls each one over stdio.
   - Every line should start with `OK`. Investigate any `ERR`, `EXC`, or `MISSING` lines.
   - If a tool was added, renamed, or had its params changed, update the `CALLS` list in `e2e.py` first. Tool params are `lat`/`lon`, and dates are `DD-MM-YYYY`.
   - The second `convert_gregorian_to_hijri` call passes `YYYY-MM-DD` on purpose and is expected to `ERR` with a 404.
4. Report a one-line verdict, then list any failures with the root cause.
