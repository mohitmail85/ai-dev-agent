# Dev Agent — Autonomous AI Engineering Assistant

A local Python application that acts as an autonomous software engineer, powered by Claude Agent SDK.
Give it a user story — it reads your codebase, writes code, runs all quality
checks, and raises a Pull Request without interrupting you.

---

## How It Works

1. Reads `README.md` and `.claude/CLAUDE.md` from the repo before touching anything
2. Creates `feature/<name>` or `fix/<name>` branch from latest main
3. Delegates to specialist subagents: code-writer, reviewer, test-runner
4. Runs all quality checks defined for that repo type (typecheck, lint, prettier, tests)
5. Fixes failures autonomously and retries
6. Commits with conventional commit format and raises a PR

---

## Project Structure

```
dev-agent/
├── run.py                  ← Entry point
├── config.yaml             ← Repos, types, and personal preferences
├── story.txt               ← Put your user story here (optional)
├── .env                    ← ANTHROPIC_API_KEY
├── requirements.txt
│
├── agent/
│   ├── core.py             ← Resolves config, builds prompts, runs agent
│   ├── repo.py             ← Validates local repo path
│   └── logger.py           ← Saves task history to logs/
│
├── prompts/
│   ├── orchestrator.md     ← Main workflow (generic — works for any repo)
│   ├── code_writer.md      ← How code gets written
│   ├── reviewer.md         ← Code review standards
│   └── tester.md           ← Quality check runner
│
└── logs/                   ← Auto-created, one .md per task run
```

---

## Setup

### Prerequisites

```bash
node --version      # Node / npm required to run repo scripts
gh --version        # GitHub CLI required for PR creation
gh auth login       # Authenticate if not already done
```

### Install

```bash
git clone https://github.com/mohitmail85/ai-dev-agent.git
cd ai-dev-agent
pip install -r requirements.txt
```

### API Key

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-full-key-here
```

Get your key: https://console.anthropic.com → API Keys

---

## Running the Agent

### Interactive
```bash
python run.py
```
Prompts you to pick a repo and type your story.

### Story from a file
```bash
python run.py taxi-product story.txt
python run.py broker-portal story.txt
```

### Specify repo only
```bash
python run.py taxi-product
# Then paste your story interactively
```

---

## PR Review Fix Mode

After you review a PR and add comments on GitHub, the agent can read those
comments, fix every issue on the existing feature branch, and push — the open
PR updates automatically.

### Fix by PR number (fetches comments from GitHub)
```bash
python run.py taxi-product --review 42
python run.py broker-portal --review 17
```
Requires `gh auth login`. The agent fetches all inline and general review
comments for that PR, checks out the feature branch, and fixes everything.

### Fix from a feedback file (manual review notes)
```bash
python run.py taxi-product --review review_feedback.txt
```
Write your review comments in a plain text file and pass it as the source.
Useful when you want to describe issues without raising a formal GitHub review,
or when working offline.

### What it does
1. Fetches PR info (branch name, review comments, inline line-level feedback)
2. Checks out the existing feature branch — never creates a new one
3. Reads and fixes every review comment
4. Runs all quality checks (typecheck, lint, prettier, tests)
5. Commits with `fix: address PR review feedback`
6. Pushes to the feature branch — the open PR updates automatically

---

## Writing a Good User Story

Include enough for the agent to work without interrupting you:

```
Title: Add driver licence validation

As an underwriter, I want driver licences validated against DVLA format
rules so that invalid licences are rejected at quote time.

Acceptance Criteria:
- UK licences must match the DVLA format regex
- Validation runs when a quote is submitted
- Invalid licence returns a descriptive error message
- Valid licences pass through unchanged

Additional context:
- See src/domain/quote/people/driver/ for existing driver logic
- Use existing Zod schema patterns in that folder
- Error messages follow the pattern in src/domain/errors.ts
```

The more context you give, the less the agent has to guess.

---

## Adding a New Repo

**Editing `config.yaml` is all you need to do.**

### Step 1 — Choose or create a type

If the new repo is similar to an existing one, reuse its type:

| Repo kind | Type to use |
|-----------|-------------|
| Root SDK backend (Taxi, Van, etc.) | `root-sdk-module` |
| Next.js broker portal | `nextjs-portal` |
| New kind | Add a new type under `repo_types:` |

### Step 2 — Add the repo (5 lines)

```yaml
repos:

  van-product:
    type: root-sdk-module
    local_path: D:/Work/root/Van-Dev/van-product-module
    github_url: https://github.com/Admiral-Business/van-product-module.git
    main_branch: main
```

That's it. The agent inherits all commands from the type:
- typecheck, lint, format check, test commands
- test file patterns, path aliases, protected files

### Step 3 — Override anything if needed

```yaml
  van-product:
    type: root-sdk-module
    local_path: D:/Work/root/Van-Dev/van-product-module
    github_url: https://github.com/Admiral-Business/van-product-module.git
    main_branch: main
    # Override just what's different:
    test_command: npm run test:unit -- --reporter=verbose
```

### Adding a New Repo Type

If a new module is genuinely different (e.g. a migration tool, a Python service):

```yaml
repo_types:

  migration-module:
    language: TypeScript
    framework: Node.js
    test_command: npm test
    typecheck_command: npm run typecheck
    lint_command: npm run lint
    format_check_command: npm run prettier:check
    format_fix_command: npm run prettier:write
```

Then reference it in repos as `type: migration-module`.

---

## Configured Repo Types

### `root-sdk-module`
Root Platform insurance product module.
- TypeScript, Vitest, Node environment
- Tests: `npm run test:unit` (`.spec.ts` colocated next to source)
- Zod: always `import z from '@/z'` — never from `'zod'`
- Protected files: `src/bundle-tests/`, `src/root.d.ts`
- Auto-generated (do not edit): `payloads/`, `code/`, `workflows/`

### `nextjs-portal`
Next.js 14 App Router broker portal.
- TypeScript, Jest, jsdom environment
- Tests: `npm test` (`.test.ts` or `__tests__/` folders)
- TDD required, 90% coverage target
- Update Storybook for new/changed components

---

## Configured Repos

| Name | Type | Path |
|------|------|------|
| `my-backend` | root-sdk-module | /path/to/your/backend-module |
| `my-frontend` | nextjs-portal | /path/to/your/frontend-app |

---

## Branch Conventions

| Situation | Branch |
|-----------|--------|
| New feature | `feature/<short-description>` |
| Bug fix | `fix/<short-description>` |

The agent **never pushes to `main` directly**.

---

## Customising

| To change... | Edit this |
|-------------|-----------|
| Your coding style and commit format | `config.yaml` → `personal_context` |
| Quality check commands for a repo type | `config.yaml` → `repo_types` |
| Agent workflow steps | `prompts/orchestrator.md` |
| PR review fix workflow | `prompts/pr_fixer.md` |
| How code gets written | `prompts/code_writer.md` |
| Review strictness | `prompts/reviewer.md` |
| How checks are reported | `prompts/tester.md` |
| Claude model or max turns | `config.yaml` → `model` / `max_turns` |

---

## Logs

Every task is saved to `logs/`:
```
logs/
├── 20260318_143022_taxi-product.md
├── 20260318_162541_broker-portal.md
```

Each log contains the user story and the agent's final result summary.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `config.yaml not found` | Run from `dev-agent/` directory |
| `ANTHROPIC_API_KEY not set` | Check `.env` has the full key |
| `Repo not found at path` | Check `local_path` in `config.yaml` |
| `gh: command not found` | Install GitHub CLI and run `gh auth login` |
| `gh pr view failed` | Check PR number is correct and `gh auth login` done |
| `Repo type 'x' not found` | Add the type under `repo_types:` in `config.yaml` |
| Agent stops before PR | Check `logs/` — increase `max_turns` if needed |
