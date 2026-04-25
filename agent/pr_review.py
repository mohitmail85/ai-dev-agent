"""Fetches PR review comments and metadata from GitHub via the gh CLI."""
import json
import subprocess


def get_pr_info(pr_number: int, repo_path: str) -> dict:
    """
    Fetch PR title, branch name, review comments and general comments
    via the GitHub CLI. Requires `gh auth login` to be done.
    """
    result = subprocess.run(
        [
            "gh", "pr", "view", str(pr_number),
            "--json",
            "number,title,headRefName,body,reviews,comments,state",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh pr view failed. Is the PR number correct and gh authenticated?\n"
            f"{result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def format_feedback(pr_info: dict) -> str:
    """
    Format all review feedback from the PR into a readable block
    for injection into the agent task prompt.
    """
    lines = []

    lines.append(f"PR Number : #{pr_info.get('number', '?')}")
    lines.append(f"PR Title  : {pr_info.get('title', '')}")
    lines.append(f"Branch    : {pr_info.get('headRefName', '')}")
    lines.append(f"PR State  : {pr_info.get('state', '')}")
    lines.append("")

    # ── Inline review comments (line-level feedback) ──────────────────────────
    reviews = pr_info.get("reviews", [])
    substantive = [
        r for r in reviews
        if r.get("body", "").strip() or r.get("comments")
    ]

    if substantive:
        lines.append("## Review Comments")
        lines.append("")
        for review in substantive:
            reviewer = review.get("author", {}).get("login", "reviewer")
            state    = review.get("state", "")
            body     = review.get("body", "").strip()

            lines.append(f"### {reviewer}  [{state}]")
            if body:
                lines.append(body)
                lines.append("")

            # Line-level comments within the review
            for comment in review.get("comments", []):
                path = comment.get("path", "")
                line = comment.get("line", "")
                text = comment.get("body", "").strip()
                if text:
                    location = f"{path}:{line}" if line else path
                    lines.append(f"**{location}**")
                    lines.append(text)
                    lines.append("")

    # ── General PR comments ───────────────────────────────────────────────────
    comments = [
        c for c in pr_info.get("comments", [])
        if c.get("body", "").strip()
    ]

    if comments:
        lines.append("## General Comments")
        lines.append("")
        for comment in comments:
            author = comment.get("author", {}).get("login", "")
            text   = comment.get("body", "").strip()
            lines.append(f"**{author}:**")
            lines.append(text)
            lines.append("")

    if not substantive and not comments:
        lines.append("(No review comments found on this PR.)")

    return "\n".join(lines)
