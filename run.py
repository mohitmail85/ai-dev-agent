#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
"""
Dev Agent — Personal AI Engineering Assistant
═══════════════════════════════════════════════

Usage:
  python run.py                                    # interactive: pick repo + type story
  python run.py <repo>                             # pick repo, type story interactively
  python run.py <repo> <story-file.txt>            # read story from file
  python run.py <repo> --review <pr-number>        # fix PR review comments (fetch from GitHub)
  python run.py <repo> --review <feedback.txt>     # fix PR review comments (from text file)

Examples:
  python run.py
  python run.py example-backend
  python run.py example-backend story.txt
  python run.py example-backend --review 42
  python run.py example-backend --review review_feedback.txt
"""
import sys
import yaml
import anyio
from pathlib import Path

from agent.core import run
from agent.review import run_review


# ── Repo Selection ────────────────────────────────────────────────────────────

def pick_repo(config: dict) -> str:
    repos = list(config["repos"].keys())

    # Passed as argument
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        name = sys.argv[1]
        if name not in repos:
            print(f"\nRepo '{name}' not found in config.yaml")
            print(f"Available: {repos}")
            sys.exit(1)
        return name

    # Interactive selection
    print("\nAvailable repos:")
    for i, name in enumerate(repos, 1):
        print(f"  {i}. {name}")

    choice = input("\nSelect repo (number or name): ").strip()

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(repos):
            return repos[idx]
    elif choice in repos:
        return choice

    print(f"Invalid selection: '{choice}'")
    sys.exit(1)


# ── Story Input ───────────────────────────────────────────────────────────────

def get_story() -> str:
    # From command-line file argument (position 2, when not --review mode)
    if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        story_file = Path(sys.argv[2])
        if story_file.exists():
            print(f"\n  Reading story from: {story_file}")
            return story_file.read_text(encoding="utf-8").strip()
        else:
            print(f"\nFile not found: {story_file}")
            sys.exit(1)

    # From story.txt in current directory (convenience shortcut)
    if Path("story.txt").exists():
        print("\n  Found story.txt — using it.")
        print("     (Delete story.txt to type manually instead)\n")
        return Path("story.txt").read_text(encoding="utf-8").strip()

    # Interactive input
    print("\n  Paste your user story below.")
    print("  Press Enter twice when done.\n")
    print("  " + "-" * 48)

    lines = []
    consecutive_blanks = 0

    while consecutive_blanks < 1:
        try:
            line = input()
        except EOFError:
            break

        if line.strip() == "":
            consecutive_blanks += 1
        else:
            consecutive_blanks = 0
            lines.append(line)

    story = "\n".join(lines).strip()

    if not story:
        print("\nNo story provided. Exiting.")
        sys.exit(1)

    return story


# ── Review Mode Detection ─────────────────────────────────────────────────────

def get_review_source() -> str | None:
    """
    Detect --review flag and return the feedback source (PR number or file path).
    Returns None if not in review mode.
    """
    args = sys.argv[1:]
    if "--review" in args:
        idx = args.index("--review")
        if idx + 1 >= len(args):
            print("\nUsage: python run.py <repo> --review <pr-number-or-file>")
            sys.exit(1)
        return args[idx + 1]
    return None


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    print(__doc__)

    # Load config
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("config.yaml not found.")
        print("Make sure you're running from the dev-agent directory.")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    repo = pick_repo(config)

    # Check for review mode
    review_source = get_review_source()

    if review_source is not None:
        # PR review fix mode
        print(f"\n  Mode  : PR Review Fix")
        print(f"  Repo  : {repo}")
        print(f"  Source: {review_source}")
        print()
        anyio.run(run_review, repo, review_source)
    else:
        # Normal story mode
        story = get_story()
        print(f"\n  Repo  : {repo}")
        print(f"  Story : {story[:80]}{'...' if len(story) > 80 else ''}")
        print()
        anyio.run(run, repo, story)


if __name__ == "__main__":
    main()
