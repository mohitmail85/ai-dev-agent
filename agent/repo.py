"""Validates the local repo path exists and returns it ready for use."""
from pathlib import Path


def prepare(repo_config: dict) -> str:
    """
    Verify the local repo exists and return its path.
    No cloning or pulling — the agent handles git operations itself.
    """
    path = repo_config["local_path"]

    if not Path(path).exists():
        raise FileNotFoundError(
            f"\n❌ Repo not found at: {path}\n"
            f"   Check the local_path in config.yaml is correct."
        )

    return path
