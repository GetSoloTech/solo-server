import typer
import requests
import json
from typing import Optional
from pathlib import Path
import subprocess
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from solo_server.config import CONFIG_PATH

BASE_URL = "https://api.starfishdata.ai/v1"

def get_starfish_api_key() -> str:
    """Get Starfish API key from environment or config file"""
    # First check environment variable
    api_key = os.getenv('STARFISH_API_KEY', '')

    if not api_key:  # If not in env, try config file
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                api_key = config.get('starfish', {}).get('api_key', '')

    if not api_key:
        if os.name in ["Linux", "Windows"]:
            typer.echo("Use Ctrl + Shift + V to paste your token.")
        api_key = typer.prompt("Please enter your Starfish API key")
        
        # Save token if provided
        if api_key:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config['starfish'] = {'api_key': api_key}
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)

    return api_key

def gen(
    prompt: str,
    num_records: Optional[int] = typer.Option(100, "--num-records", "-n", help="Number of records to generate"),
    model: Optional[str] = typer.Option("gpt-4o-mini-2024-07-18", "--model", "-m", help="Model to use for generation")
):
    """
    Generate synthetic data using StarfishData API.

    Example:
        solo finetune gen "Generate customer service conversations about product returns"
    """
    api_key = get_starfish_api_key()
    if not api_key:
        typer.echo("❌ Starfish API key is required", err=True)
        raise typer.Exit(1)

    data = {
        "prompt": prompt,
        "numOfRecords": num_records,
        "model": model
    }

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    try:
        response = requests.post(
            f'{BASE_URL}/generateData',
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status()
        
        result = response.json()
        console = Console()
        
        # Create a table
        table = Table(show_header=False, box=ROUNDED)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Job ID", result.get('jobId'))
        table.add_row("Project ID", result.get('projectId'))
        
        # Create a panel with success message and table
        content = [
            Text("✅ Successfully started data generation", style="bold green"),
            "",  # Empty line
            Text("Available commands:", style="yellow"),
            Text(f"• Check status:  solo finetune status {result.get('jobId')}", style="blue"),
            Text(f"• Download data: solo finetune download {result.get('projectId')}", style="blue")
        ]
        
        panel = Panel(
            "\n".join(str(item) for item in content),
            title="[bold magenta]Generation Details[/]",
            border_style="bright_blue"
        )
        console.print(panel)
    except requests.exceptions.RequestException as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)

def status(job_id: str):
    """
    Check the status of a data generation job.

    Example:
        solo finetune status "job-123-456"
    """
    api_key = get_starfish_api_key()
    if not api_key:
        typer.echo("❌ Starfish API key is required", err=True)
        raise typer.Exit(1)

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    data = {
        "jobId": job_id
    }

    try:
        response = requests.post(
            f'{BASE_URL}/jobStatus',
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status()
        
        result = response.json()
        status = result.get('status', 'UNKNOWN')
        typer.echo(f"📊 Data generation status: {status}")
        
        if status == "COMPLETE":
            typer.echo(f"✅ Data generation completed, Now you can download the data")
        elif status == "FAILED":
            typer.echo(f"❌ Error: {result.get('error')}")
    except requests.exceptions.RequestException as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)

def download(
    project_id: str,
    output: Optional[str] = typer.Option("data.json", "--output", "-o", help="Output file path")
):
    """
    Download generated data for a project.

    Example:
        solo finetune download "project-123-456" --output my_data.json
    """
    api_key = get_starfish_api_key()
    if not api_key:
        typer.echo("❌ Starfish API key is required", err=True)
        raise typer.Exit(1)

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    data = {
        "projectId": project_id
    }

    try:
        response = requests.post(
            f'{BASE_URL}/data',
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Save the data to a file
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
            
        typer.echo(f"✅ Successfully downloaded data to {output}")
        typer.echo(f"📊 Number of records: {len(result['data'])}")  
    except requests.exceptions.RequestException as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
    except IOError as e:
        typer.echo(f"❌ Error writing to file: {str(e)}", err=True)

def run(
    data_path: str = typer.Argument(..., help="Path to the JSON data file"),
    output_dir: str = typer.Option("./finetuned_model", "--output-dir", "-o", help="Directory to save the finetuned model"),
    batch_size: int = typer.Option(1, "--batch-size", "-b", help="Training batch size"),
    epochs: int = typer.Option(2, "--epochs", "-e", help="Number of training epochs"),
    learning_rate: float = typer.Option(2e-4, "--learning-rate", "-lr", help="Learning rate"),
    lora_r: int = typer.Option(8, "--lora-r", help="LoRA attention dimension"),
    lora_alpha: int = typer.Option(8, "--lora-alpha", help="LoRA alpha parameter"),
    lora_dropout: float = typer.Option(0.02, "--lora-dropout", help="LoRA dropout value"),
    rebuild_image: bool = typer.Option(False, "--rebuild-image", help="Force rebuild the Docker image"),
):
    """
    Finetune a model on generated data using unsloth with LoRA in a Docker container.

    Example:
        solo finetune run data.json --output-dir ./my_model --batch-size 8
    """
    try:
        # Convert paths to absolute paths
        data_path = os.path.abspath(data_path)
        output_dir = os.path.abspath(output_dir)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Check if container exists (running or stopped)
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", "name=solo-finetune"],
            capture_output=True,
            text=True
        ).stdout.strip()

        docker_finetune = "getsolo/finetune:latest"
        if container_exists:
            # Check if container is running
            is_running = subprocess.run(
                ["docker", "ps", "-q", "-f", "name=solo-finetune"],
                capture_output=True,
                text=True
            ).stdout.strip()
            
            if is_running:
                typer.echo("✅ Finetune is already running")
            else:
                subprocess.run(["docker", "start", "solo-finetune"], check=True)
        else:
            # Check if image exists
            image_exists = subprocess.run(
                ["docker", "images", "-q", docker_finetune],
                capture_output=True,
                text=True
            ).stdout.strip()

            if not image_exists or rebuild_image:
                typer.echo("📥 Pulling finetune image...")
                try:
                    subprocess.run(["docker", "pull", docker_finetune], check=True)
                except subprocess.CalledProcessError as e:
                    typer.echo(f"❌ Error: {str(e)}", err=True)
                    raise typer.Exit(1)

        # Prepare arguments for the training script
        training_args = {
            "data_path": "/app/data.json",
            "output_dir": "/app/output",
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "lora_dropout": lora_dropout,
        }
        
        # Convert arguments to command line format
        args_list = []
        for key, value in training_args.items():
            args_list.extend([f"--{key.replace('_', '-')}", str(value)])

        # Run the finetuning command in the container
        docker_cmd = [
            "docker", "run",
            "--name", "solo-finetune",
            "--gpus", "all",  # Enable GPU access
            "-v", f"{data_path}:/app/data.json:ro",  # Mount data file
            "-v", f"{output_dir}:/app/output",  # Mount output directory
            docker_finetune,
            "python", "./finetune_script.py",
            *args_list
        ]

        typer.echo("🚀 Starting finetuning process...")
        subprocess.run(docker_cmd, check=True)
        
        typer.echo("✅ Finetuning completed successfully!")
        typer.echo(f"📁 Model saved to: {output_dir}")
        typer.echo(f"📁 GGUF Model converted and saved to {os.path.join(output_dir, 'gguf_path')}")

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Error during Docker operation: {str(e)}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)