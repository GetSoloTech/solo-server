"""
Dataset utilities for LeRobot
"""

import typer
from pathlib import Path
from typing import Optional, Tuple
from rich.prompt import Prompt, Confirm


def check_dataset_exists(repo_id: str, root: Optional[str] = None) -> bool:
    """
    Check if a dataset already exists by looking for the dataset directory
    """
    if root is not None:
        dataset_path = Path(root)
    else:
        # Import
        from lerobot.constants import HF_LEROBOT_HOME
        dataset_path = HF_LEROBOT_HOME / repo_id
    
    return dataset_path.exists() and dataset_path.is_dir()


def handle_existing_dataset(repo_id: str, root: Optional[str] = None) -> Tuple[str, bool]:
    """
    Handle the case when a dataset already exists
    Returns (final_repo_id, should_resume)
    """
    while True:
        if not check_dataset_exists(repo_id, root):
            # Dataset doesn't exist, we can proceed with creation
            return repo_id, False
        
        # Dataset exists, ask user what to do
        typer.echo(f"\n⚠️  Dataset already exists: {repo_id}")
        
        choice = Confirm.ask("Resume recording?", default=True)
        
        if choice:
            # User wants to resume
            return repo_id, True
        else:
            # User wants a different name
            typer.echo(f"\nCurrent repository: {repo_id}")
            repo_id = Prompt.ask("Enter a new repository ID", default=repo_id)


def normalize_repo_id(repo_id: str, hf_username: Optional[str] = None) -> str:
    """
    Ensure repo_id follows the expected 'owner/name' format used by LeRobot.
    If no owner namespace is provided, default to:
      - '{hf_username}/<name>' when a HuggingFace username is known
      - 'local/<name>' otherwise (purely local namespace)
    """
    if "/" in repo_id and len(repo_id.split("/")) == 2:
        return repo_id
    name_only = repo_id.split("/")[-1].strip()
    if hf_username:
        owner = hf_username.strip()
        if owner:
            return f"{owner}/{name_only}"
    return f"local/{name_only}"
