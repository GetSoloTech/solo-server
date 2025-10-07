import typer
from huggingface_hub import snapshot_download
from rich.console import Console
import os
import json
from solo_server.config import CONFIG_PATH
import subprocess

console = Console()

def download(
    model_arg: str = typer.Argument(None, help="Model name or repo ID (positional)"),
    model_opt: str = typer.Option(None, "--model", "-m", help="Model name or repo ID (option)"),
) -> None:
    """
    Downloads a Hugging Face model using the huggingface repo id.
    """
    # Prefer the option if provided, otherwise fallback to positional
    model = model_opt or model_arg

    if not model:
        console.print("❌ Please provide a model name (e.g., -m meta-llama/Llama-3.2-1B-Instruct)", style="bold red")
        raise typer.Exit(code=1)
    
    console.print(f"🚀 Downloading model: [bold]{model}[/bold]...")
    try:
        model_path = snapshot_download(repo_id=model)
        console.print(f"✅ Model downloaded successfully: [bold]{model_path}[/bold]")
    except Exception as e:
        console.print(f"❌ Failed to download model: {e}", style="bold red")
    except KeyboardInterrupt:
        console.print("❌ Download cancelled by user.", style="bold red")
