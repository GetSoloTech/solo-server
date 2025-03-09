import typer
import subprocess
from rich.console import Console
from pyngrok import ngrok

console = Console()
app = typer.Typer()

@app.command(name="deploy")
def deploy(
    image: str = typer.Option("solo_core_image", help="Docker image name for Solo Core")
):
    """
    Deploy Solo Core so that its endpoint on port 5070 is exposed via an ngrok tunnel.

    This command will:
      - Start the Solo Core Docker container (exposing port 5070).
      - Create an ngrok tunnel for port 5070.
      - Print the public URL for accessing the Solo Core endpoint.
    
    Ensure that Docker is running and that you have the pyngrok package installed.
    """
    # Step 1: Deploy the Solo Core container
    docker_cmd = [
        "docker", "run", "-d",
        "-p", "5070:5070",
        "--name", "solo_core",
        image
    ]
    console.print("[bold blue]Deploying Solo Core container...[/bold blue]")
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        console.print("[bold green]Solo Core container deployed successfully.[/bold green]")
        console.print(f"[blue]Container ID: {container_id}[/blue]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Deployment failed: {e.stderr}[/red]")
        raise typer.Exit(code=1)

    # Step 2: Start an ngrok tunnel for port 5070
    console.print("[bold blue]Starting ngrok tunnel on port 5070...[/bold blue]")
    try:
        tunnel = ngrok.connect(5070, "http")
        public_url = tunnel.public_url
        console.print(f"[bold green]Ngrok tunnel established:[/bold green] [blue]{public_url}[/blue]")
    except Exception as e:
        console.print(f"[red]Ngrok tunnel failed: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
