import typer
from huggingface_hub import snapshot_download
from rich.console import Console
import os
import json
from solo_server.config import CONFIG_PATH
import subprocess

console = Console()

def download(model: str) -> None:
    """
    Downloads a Hugging Face model.
    """
    console.print(f"🚀 Downloading model: [bold]{model}[/bold]...")
    try:
        model_path = snapshot_download(repo_id=model)
        console.print(f"✅ Model downloaded successfully: [bold]{model_path}[/bold]")
    except Exception as e:
        console.print(f"❌ Failed to download model: {e}", style="bold red")
    except KeyboardInterrupt:
        console.print("❌ Download cancelled by user.", style="bold red")
