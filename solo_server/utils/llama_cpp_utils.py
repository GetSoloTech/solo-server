import os
import sys
import json
import time
import typer
import shutil
import subprocess
from rich import print as rprint
from solo_server.config import CONFIG_PATH
from solo_server.utils.hf_utils import get_available_models

def is_uv_available():
    return shutil.which("uv") is not None

def preprocess_model_path(model_path: str) -> tuple[str, str]:
    """
    Preprocess the model path to determine if it's a repo ID or direct GGUF path.
    Returns tuple of (hf_repo_id, model_pattern).
    """
    if model_path.endswith('.gguf'):
        # Direct GGUF file path
        parts = model_path.split('/')
        repo_id = '/'.join(parts[:-1]) if '/' in model_path else None
        return repo_id, parts[-1] if parts else model_path
    else:
        # Repo ID format - auto-append quantization pattern
        return model_path, '*q4_0.gguf'

def start_llama_cpp_server(os_name: str = None):
    """start llama_cpp_python server using system config."""
    
    typer.echo("\n Starting llama_cpp server...")

    # Get HuggingFace token from environment variable or config file
    hf_token = os.getenv('HUGGING_FACE_TOKEN', '')

    if not hf_token:  # If not in env, try config file
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                hf_token = config.get('hugging_face', {}).get('token', '')

    # Ask if user wants to update the token
    if not hf_token:
        if os_name in ["Linux", "Windows"]:
            typer.echo("Use Ctrl + Shift + V to paste your token.")
        hf_token = typer.prompt("Please add your HuggingFace token")

        # Save token if provided 
        if hf_token:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            config['hugging_face'] = {'token': hf_token}
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            os.environ['HUGGING_FACE_TOKEN'] = hf_token

    # Get model path from user
    typer.echo("\nPlease add repo_id from HuggingFace Hub (e.g., bartowski/Llama-3.2-1B-Instruct-GGUF)")
    
    repo_id = typer.prompt("Model path", default="bartowski/Llama-3.2-1B-Instruct-GGUF")
    model_files = get_available_models(repo_id, suffix=".gguf")

    if len(model_files) == 0:
        typer.echo("No gguf models found in the repo. Please try another repository.")
        return False
    
    # Let user choose from available models
    if len(model_files) > 1:
        typer.echo("\nAvailable models:")
        for idx, file in enumerate(model_files, 1):
            typer.echo(f"{idx}. {file}")
        choice = typer.prompt(
            "Choose model number", 
            default="1", 
            type=int, 
            show_default=False
        )
        if 1 <= choice <= len(model_files):
            model_path = model_files[choice - 1]
        else:
            typer.echo("Invalid choice. Using first model.")
            model_path = model_files[0]
    else:
        model_path = model_files[0]

    # Build server command
    server_cmd = [sys.executable, "-m", "llama_cpp.server"]
    
    if repo_id:
        # Using HuggingFace repo
        server_cmd.extend(["--hf_model_repo_id", repo_id])
        server_cmd.extend(["--model", model_path])
    else:
        # Direct model path
        server_cmd.extend(["--model", model_path])

    try:
        typer.echo("\n🚀 Starting llama.cpp server...")
        typer.echo(f"Using model: {repo_id + '/' + model_path if repo_id else model_path}")
        
        try:
            subprocess.run(server_cmd, env=os.environ.copy())
        except Exception as e:
            typer.echo(f"❌ Failed to start llama.cpp server: {e}", err=True)
            return False
        
        # Wait for server to start
        time.sleep(5)  # Give the server some time to initialize
        typer.secho(
            "✅ llama.cpp server is running!\n",
            fg=typer.colors.BRIGHT_CYAN,
            bold=True
        )
        return True
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start llama.cpp server: {e}", err=True)
        return False
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        return False