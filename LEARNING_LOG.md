# Learning Log

A journal of what I learn as I build this project. Written in my own words, updated after each session.

Format: `## YYYY-MM-DD — Session Title`

---

## 2026-07-09 — Project Foundation Setup

**What I did today:**
- Set up the project folder at `~/dev/kairo-marketplace-analytics`
- Initialized Git repository
- Created `.gitignore`, `README.md`, `PROJECT_CHARTER.md`, and this learning log
- Opened the project in VS Code with integrated terminal

**What I learned:**
- Professional projects live in `~/dev/` or similar, not on the Desktop
- Folder names should be lowercase-with-hyphens for GitHub compatibility
- Git must be initialized before adding files, or the first commit gets messy
- `.gitignore` prevents polluting the repo with cache files, secrets, and data
- VS Code's integrated terminal keeps the workflow in one window

**What surprised me / was confusing:**
- (Fill this in — this section matters most)

**What I want to understand better:**
- (Fill this in)

**Next session:**
- Set up Python virtual environment with `uv`
- Install first Python packages
- Make first Git commit

## 2026-07-09 (evening) — Python Environment & Data Stack Wired Up

**What I did:**
- Initialized Python project with `uv init` pinned to 3.11
- Created and activated virtual environment
- Installed Polars, DuckDB, Pandas, PyArrow
- Wrote a smoke test that ran a SQL query via DuckDB against a Polars DataFrame
- Made second Git commit with proper conventional-commit message

**What I learned:**
- `uv init` + `uv venv` + `uv add` is the modern Python setup flow
- Virtual environments must be activated (`source .venv/bin/activate`) to use them
- `git add` and `git commit` are two separate steps — I confused this once
- Empty files (0 bytes) run silently in Python — always verify file size after creating
- REPL (`python`) vs script (`python file.py`) are different modes
- DuckDB can SQL-query a Polars DataFrame directly, no conversion needed

**What confused me:**
- (write your honest answer — one sentence is fine)

**What I want to understand better next time:**
- (write your honest answer)

**Next session:**
- Build the proper project folder structure
- Start business context documentation
- Begin the metric catalog