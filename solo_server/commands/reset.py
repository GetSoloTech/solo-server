import typer
import subprocess
from rich.console import Console
import os
import shutil

console = Console()

def reset(
    download_dir: str = typer.Option("./downloaded_models", help="Directory where models are downloaded."),
    container_filter: str = typer.Option("solo", help="Filter string to match Docker container names (default: 'solo').")
) -> None:
    """
    Resets the Solo environment by removing all Docker containers matching the filter
    and deleting all downloaded models, resulting in a clean setup.
    """
    # Check if Docker is running
    try:
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        typer.echo("\n✅ Docker is not running, skipping container removal.\n")
    else:
        typer.echo("🛑 Removing all Solo Docker containers...")
        try:
            # List all containers (running or stopped) that match the container_filter
            container_ids = subprocess.run(
                ["docker", "ps", "-a", "-q", "-f", f"name={container_filter}"],
                check=True,
                capture_output=True,
                text=True
            ).stdout.strip()

            if container_ids:
                for container_id in container_ids.splitlines():
                    # Force remove container
                    subprocess.run(
                        ["docker", "rm", "-f", container_id],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                typer.echo("✅ All Solo Docker containers removed successfully.")
            else:
                typer.echo("✅ No Solo Docker containers found.")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to remove Solo Docker containers: {e.stderr if hasattr(e, 'stderr') else str(e)}", err=True)
        except Exception as e:
            typer.echo(f"⚠️ Unexpected error while removing Docker containers: {e}", err=True)
    
    # Remove the downloaded models directory
    typer.echo("🗑️ Removing downloaded models...")
    if os.path.exists(download_dir):
        try:
            shutil.rmtree(download_dir)
            typer.echo(f"✅ Downloaded models removed from {download_dir}")
        except Exception as e:
            typer.echo(f"❌ Failed to remove downloaded models: {e}", err=True)
    else:
        typer.echo("✅ No downloaded models directory found.")
    
    typer.echo("🔄 Reset complete. Clean setup is ready.")

app = typer.Typer()

@app.command("reset")
def reset_command(
    download_dir: str = typer.Option("./downloaded_models", help="Directory where models are downloaded."),
    container_filter: str = typer.Option("solo", help="Filter string to match Docker container names (default: 'solo').")
):
    reset(download_dir, container_filter)

if __name__ == "__main__":
    app()
