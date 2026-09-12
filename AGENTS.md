# AGENTS.md — rent_in_armenia

Guidance for AI agents working in this repository.

## What this project is

Django dashboard + list.am scrapers for:

- Yerevan flat **rent** (`REAL_ESTATE`, category 56)
- Tavush house **sales** (`HOUSES`, category 1386)
- Dilijan long-term **rent** apartments + houses (`DILIJAN_RENT`, categories 56 / 1377)

Layout is a **flat Python/Django tree** (not a multi-service monorepo). Prefer small, focused modules next to existing patterns (`scraper.py`, `house_scraper.py`, `dilijan_rent_scraper.py`, `dashboard/`).

Use the project venv: `.\venv\Scripts\python.exe`.

## How to work

- Search the repo before inventing new patterns.
- Prefer the simplest change that matches existing code style.
- Ship the complete fix for the request: code + tests when behavior changes. Do not leave half-done threads when a few more minutes closes them.
- Understand failure modes before calling work done. Tests passing is evidence, not understanding.
- Do **not** commit, push, or open a PR unless the user explicitly asks.
- Do **not** rewrite git history or force-push unless the user explicitly asks.

## Task sizing

State size briefly at the start of non-trivial work:

| Size | Examples | Verification |
|------|----------|--------------|
| **small** | Copy, CSS, rename, config, 1–2 file mechanical edits | Lint / touch only what changed; no new test if behavior unchanged |
| **medium** | Bug fix or localized behavior in one module | Touched module tests + regression test for bugs |
| **large** | New scrape pipeline, schema/contract change, new dashboard page | Full relevant suites (`manage.py test`), smoke scrape if list.am involved |

When unsure, pick the **smaller** size; escalate if blast radius grows.

## Testing

- Behavior change → ship a test in the same change when practical (`dashboard/tests.py` or a focused module test).
- Bug fix → regression test that would have caught it.
- Default: run the tests that cover what you touched, e.g.  
  `.\venv\Scripts\python.exe manage.py test dashboard.tests`
- After scraper/parser changes, prefer a small live smoke parse against list.am when the network allows; say so if rate-limited (403).

## Scraping / list.am

- Respect delays (`REQUEST_DELAY_SEC`); avoid hammering the site.
- Canonicalize item URLs (strip `?ld_src=…`) via `listam_links.normalize_listam_link`.
- Sale vs rent use different price plausibility bands — do not mix them.
- Keep Yerevan rent charts free of Dilijan rows (Dilijan rent lives in `DILIJAN_RENT`).

## Safety

- Never commit secrets (`.env`, credentials). Check `.gitignore` if env files are touched.
- No destructive git/DB ops (`reset --hard`, `DROP TABLE`, etc.) without explicit user confirmation.
- Never skip hooks with `--no-verify` unless the user asks.
- Production deploys: state the plan and wait for confirmation.

## Talking to the user

- Direct. Short. Concrete. File names and symbols when relevant.
- No filler, no fake “next steps” recap.
- If blocked (rate limit, missing decision, ambiguous architecture), say so plainly and ask.

## Out of scope for this file

No Claude Code worktree ritual, no mandatory multi-agent fan-out, no `services/` architecture requirement. Use Cursor’s normal checkout; one agent session at a time in this folder unless the user says otherwise.
