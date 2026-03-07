<div align="center">

# 🤖 OSSTriage

**AI-driven Pull Request review & Issue triaging for Open Source maintainers.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built with DSPy](https://img.shields.io/badge/built%20with-DSPy-purple.svg)](https://dspy.ai)
[![Package Manager: uv](https://img.shields.io/badge/pkg-uv-orange.svg)](https://docs.astral.sh/uv/)

*Stop drowning in PRs. Let AI handle the first pass.*

</div>

---

## 🔥 The Problem

Open-source maintainer burnout is real. Popular repositories get flooded with pull requests and issues that need review, triaging, and labeling — and most of that work is repetitive. **60% of OSS maintainers report burnout**, and the #1 cause is the sheer volume of contributions needing review.

## 💡 The Solution

**OSSTriage** is a CLI tool and GitHub Action that uses AI (via [DSPy](https://dspy.ai)) to:

- 🔍 **Review Pull Requests** — Automatically analyse diffs for security risks, performance issues, logic flaws, and code quality
- 🏷️ **Triage Issues** — Suggest labels, assign priority scores, and summarise issue content
- 🤝 **Reduce Toil** — Let maintainers focus on the decisions that matter, not the first-pass review drudgery

OSSTriage doesn't replace humans — it gives maintainers a structured, AI-generated *starting point* for every PR and issue.

---

## 🏗️ Architecture

```
osstriage/
├── src/osstriage/
│   ├── cli.py                  # Typer CLI entry points
│   ├── github_client.py        # GitHub API wrapper (PyGithub)
│   ├── core/
│   │   ├── config.py           # Settings from env / .env
│   │   ├── logging.py          # Rich-powered structured logging
│   │   └── exceptions.py       # Custom exception hierarchy
│   └── dspy_modules/
│       ├── signatures.py       # DSPy I/O signatures
│       ├── review_pr.py        # ReviewPRModule (ChainOfThought)
│       └── triage_issue.py     # TriageIssueModule (ChainOfThought)
├── .github/workflows/
│   └── osstriage-ci.yml        # Ready-to-use GitHub Action
├── action.yml                  # Composite action for marketplace
├── pyproject.toml              # uv-compatible project manifest
└── README.md
```

**Why DSPy?** Unlike LangChain's prompt-centric approach, DSPy uses *programmatic logic compilation* — you define typed signatures and let the framework optimise the prompts. This makes the AI modules testable, composable, and reliable.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (modern Python package manager)
- A GitHub Personal Access Token
- An OpenAI API key

### Install

```bash
# Install as a CLI tool (recommended)
uv tool install osstriage

# Or clone and install locally for development
git clone https://github.com/your-org/osstriage.git
cd osstriage
uv sync
```

### Configure

Create a `.env` file (or export the variables in your shell):

```bash
cp .env.example .env
# Edit .env with your actual tokens
```

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | ✅ | GitHub PAT with `repo` scope |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `OSSTRIAGE_LOG_LEVEL` | ❌ | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |
| `OSSTRIAGE_MODEL` | ❌ | LLM model (default: `gpt-4o`) |

---

## 📖 Usage

### Review a Pull Request

```bash
# Full review with GitHub comment
osstriage review-pr https://github.com/owner/repo/pull/42

# Dry run (only show results locally, don't post to GitHub)
osstriage review-pr https://github.com/owner/repo/pull/42 --dry-run

# Use a specific model
osstriage review-pr https://github.com/owner/repo/pull/42 --model gpt-4o-mini

# Verbose output for debugging
osstriage review-pr https://github.com/owner/repo/pull/42 -v
```

#### What it analyses:
- 🔒 **Security risks** — injection, exposed secrets, unsafe deserialization
- ⚡ **Performance issues** — N+1 queries, unnecessary allocations, blocking calls
- 🐛 **Logic flaws** — off-by-one errors, missing edge cases, race conditions
- 💡 **Suggestions** — naming, structure, documentation, best practices

### Triage an Issue

```bash
# Triage and display results
osstriage triage-issue https://github.com/owner/repo/issues/7

# Triage and automatically apply labels
osstriage triage-issue https://github.com/owner/repo/issues/7 --apply-labels

# Dry run
osstriage triage-issue https://github.com/owner/repo/issues/7 --dry-run
```

#### What it produces:
- 🏷️ **Suggested labels** — `bug`, `feature`, `docs`, `security`, `good-first-issue`, etc.
- 📊 **Priority score** — 1 (low) to 5 (critical) with justification
- 📋 **Summary** — Concise 1-2 sentence description
- 👤 **Ideal expertise** — What skills are needed to address the issue

### Set Up GitHub Action

```bash
# Scaffold the workflow file into .github/workflows/
osstriage setup-action
```

---

## ⚙️ GitHub Action

### Option 1: Use the provided workflow (recommended)

Copy `.github/workflows/osstriage-ci.yml` to your repository, then add these secrets:

| Secret | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |

> `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### Option 2: Use as a composite action

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: your-org/osstriage@main
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          model: "gpt-4o"
          command: "review-pr"
```

---

## 🛠️ Development

```bash
# Clone and set up dev environment
git clone https://github.com/your-org/osstriage.git
cd osstriage
uv sync

# Run the CLI during development
uv run osstriage --help

# Run tests
uv run pytest

# Lint with ruff
uv run ruff check src/
uv run ruff format src/
```

---

## 🗺️ Roadmap

- [ ] **DSPy optimisation** — Compile review modules with labelled examples for higher accuracy
- [ ] **Multi-LLM support** — Anthropic Claude, Google Gemini, local Ollama models
- [ ] **Inline comments** — Post review feedback as inline PR comments on specific lines
- [ ] **Custom rules** — Allow repos to define `.osstriage.yml` with project-specific review guidelines
- [ ] **Batch mode** — Triage all open issues in a repository at once
- [ ] **Metrics dashboard** — Track review accuracy and time saved

---

## 🤝 Contributing

Contributions are welcome! This project exists to help the OSS community, and we'd love your help making it better.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`uv run pytest && uv run ruff check src/`)
5. Commit and push (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for the open-source community.**

*Because maintainers deserve sleep too.*

</div>
