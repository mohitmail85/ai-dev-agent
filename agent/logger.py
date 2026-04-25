"""Saves task logs so you have a history of everything the agent did."""
from pathlib import Path
from datetime import datetime


def save(repo_name: str, story: str, result: str):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{timestamp}_{repo_name}.md"

    log_file.write_text(
        f"# Task Log\n\n"
        f"**Repo:** {repo_name}  \n"
        f"**Time:** {timestamp}\n\n"
        f"---\n\n"
        f"## User Story\n\n{story}\n\n"
        f"---\n\n"
        f"## Result\n\n{result}\n",
        encoding="utf-8"
    )

    print(f"\n  Log saved -> {log_file}")
