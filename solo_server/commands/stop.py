import typer
import subprocess
from rich.console import Console
import time

console = Console()

def stop(name: str = typer.Option("", help="Server type to stop (e.g., 'ollama', 'vllm', 'finetune')")):
    """
    Stops Solo Server containers. If a server type is specified (e.g., 'ollama', 'vllm', 'finetune'),
    only that specific container will be stopped. Otherwise, all Solo containers will be stopped.
    """

    # Check if docker is running
    try:
        subprocess.run(["docker", "info"], 
                      check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        typer.echo("\n✅ Solo server is already stopped (Docker is not running)\n")
        return

    typer.echo("🛑 Stopping Solo Server...")

    try:
        if name:
            # Map server type to container name pattern
            container_name = f"solo-{name}" if not name.startswith("solo-") else name
            
            # Check if the container exists
            container_exists = subprocess.run(
                ["docker", "ps", "-a", "-q", "-f", f"name={container_name}"],
                check=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            if not container_exists:
                typer.echo(f"❌ {name} server not found", err=True)
                return
            
            # Stop the specific container
            subprocess.run(
                ["docker", "stop", container_name],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            typer.echo(f"✅ {name} server stopped successfully.")
        else:
            # Find all solo containers
            containers = subprocess.run(
                ["docker", "ps", "-q", "-f", "name=solo"],
                check=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            if not containers:
                typer.echo("✅ No running Solo server found.")
                return
            
            # Stop all solo containers
            for container_id in containers.split('\n'):
                if container_id:
                    subprocess.run(
                        ["docker", "stop", container_id],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
            
            typer.echo("✅ All Solo server containers stopped successfully.")

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to stop Solo Server: {e.stderr if hasattr(e, 'stderr') else str(e)}", err=True)
    except Exception as e:
        typer.echo(f"⚠️ Unexpected error: {e}", err=True)
