"""PR review feedback runner — checks out the existing feature branch and fixes review comments."""
import anyio
from pathlib import Path

from dotenv import load_dotenv
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    SystemMessage,
)

from .core import (
    load_config,
    resolve_repo,
    load_prompt,
    read_repo_context,
    build_quality_checks,
    build_repo_settings,
)
from . import repo as repo_manager
from . import logger
from .pr_review import get_pr_info, format_feedback

load_dotenv()


async def run_review(repo_name: str, feedback_source: str):
    """
    Fix PR review comments on an existing feature branch.

    feedback_source: either a PR number (e.g. "42") or a path to a text file
                     containing manually written review feedback.
    """
    config = load_config()

    if repo_name not in config["repos"]:
        available = list(config["repos"].keys())
        print(f"\nUnknown repo: '{repo_name}'")
        print(f"Available   : {available}")
        return

    repo = resolve_repo(config, repo_name)

    print(f"\n{'=' * 52}")
    print(f"  Dev Agent  |  PR Review Mode  |  {repo_name}")
    print(f"{'=' * 52}")

    print("\n[1/4] Locating repo...")
    repo_path = repo_manager.prepare(repo)
    print(f"  {repo_path}")

    # ── Resolve feedback ───────────────────────────────────────────────────────
    print("[2/4] Loading review feedback...")

    pr_number = None
    branch_name = None

    if feedback_source.isdigit():
        # PR number — fetch from GitHub
        pr_number = int(feedback_source)
        print(f"  Fetching PR #{pr_number} from GitHub...")
        pr_info = get_pr_info(pr_number, repo_path)
        branch_name = pr_info.get("headRefName", "")
        feedback_block = format_feedback(pr_info)
        print(f"  Branch : {branch_name}")
        print(f"  Title  : {pr_info.get('title', '')}")
    else:
        # Text file — manually written feedback
        feedback_file = Path(feedback_source)
        if not feedback_file.exists():
            print(f"\n  File not found: {feedback_source}")
            print("  Pass a PR number or a path to a feedback .txt file.")
            return
        feedback_block = feedback_file.read_text(encoding="utf-8").strip()
        print(f"  Reading feedback from: {feedback_file}")

    print("[3/4] Reading repo context (README + CLAUDE.md)...")
    repo_context = read_repo_context(repo_path)

    print("[4/4] Launching agent...\n")

    main_branch    = repo.get("main_branch", "main")
    personal_ctx   = config.get("personal_context", "")
    quality_checks = build_quality_checks(repo)
    repo_settings  = build_repo_settings(repo_name, repo, repo_path)

    # Build branch instruction
    if branch_name:
        branch_instruction = (
            f"The PR is on branch `{branch_name}`.\n"
            f"Checkout that branch: `git checkout {branch_name}`\n"
            f"Do NOT create a new branch."
        )
    else:
        branch_instruction = (
            "Identify the feature branch from the PR or feedback above.\n"
            "Check it out: `git checkout <branch-name>`\n"
            "Do NOT create a new branch."
        )

    task_prompt = f"""\
{personal_ctx}

---

{repo_context}

---

PR REVIEW FEEDBACK TO ADDRESS:

{feedback_block}

---

{branch_instruction}

---

REPO SETTINGS:
{repo_settings}

---

QUALITY CHECKS — Run all of these after making fixes:
{quality_checks}

---

INSTRUCTIONS:
- Work fully autonomously — do not ask for permission at any point
- Checkout the existing feature branch — do NOT create a new branch
- Read every review comment carefully and fix each one
- Read the relevant source files before making changes — never guess
- Never push directly to `{main_branch}`
- All quality checks above must pass after your fixes
- Commit your fixes and push to the existing branch (PR auto-updates)
- Do NOT raise a new PR — the existing PR will update automatically
"""

    # Load prompts
    pr_fixer_prompt    = load_prompt("pr_fixer")
    code_writer_prompt = load_prompt("code_writer")
    reviewer_prompt    = load_prompt("reviewer")
    tester_prompt      = load_prompt("tester")

    result_text = ""

    async for message in query(
        prompt=task_prompt,
        options=ClaudeAgentOptions(
            cwd=repo_path,
            model=config.get("model", "claude-opus-4-6"),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent"],
            permission_mode="bypassPermissions",
            system_prompt=pr_fixer_prompt,
            max_turns=config.get("max_turns", 80),
            agents={
                "code-writer": AgentDefinition(
                    description=(
                        "Senior TypeScript engineer. Reads the codebase, implements "
                        "fixes for review comments following all CLAUDE.md rules."
                    ),
                    prompt=code_writer_prompt,
                    tools=["Read", "Write", "Edit", "Glob", "Grep"],
                ),
                "code-reviewer": AgentDefinition(
                    description=(
                        "Staff engineer. Reviews that all PR feedback points have been "
                        "addressed correctly. Returns APPROVED or lists any remaining issues."
                    ),
                    prompt=reviewer_prompt,
                    tools=["Read", "Glob", "Grep", "Bash"],
                ),
                "test-runner": AgentDefinition(
                    description=(
                        "QA engineer. Runs all quality checks (typecheck, lint, prettier, "
                        "tests) using the commands provided in the task. Reports pass/fail "
                        "with exact error details."
                    ),
                    prompt=tester_prompt,
                    tools=["Read", "Bash", "Glob"],
                ),
            },
        ),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
            print("\n[DONE] All review points addressed!\n")
            print(result_text)

        elif isinstance(message, SystemMessage) and message.subtype == "init":
            session_id = message.data.get("session_id", "unknown")
            print(f"  Session: {session_id}\n")

    summary = f"PR REVIEW FIX\nSource: {feedback_source}\n\n{result_text}"
    logger.save(repo_name, summary, result_text)
