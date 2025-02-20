import typer
import subprocess
from solo_server.utils.hardware import display_hardware_info
from rich.console import Console
from rich.table import Table
import json

console = Console()

def status():
    """Check running models and system status."""
    display_hardware_info(typer)
    
    # First check if docker is running
    try:
        subprocess.run(["docker", "ps"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        typer.echo("\n❌ Solo server not running. Please start solo-server first.")
        return
    
    # Check for running solo containers
    container_result = subprocess.run(["docker", "ps", "-f", "name=solo*", "--format", "{{json .}}"],
                                    capture_output=True, text=True, check=True)
    
    # if container_result.stdout.strip():
    #     # Container is running, show available models
    #     typer.echo("\n🔍 Available Models:")
    #     models_result = subprocess.run(["docker", "exec", "solo-ollama", "ollama", "list"], 
    #                                  capture_output=True, text=True, check=True)
    #     models = []
    #     for line in models_result.stdout.strip().split('\n'):
    #         parts = line.split()
    #         if len(parts) >= 7:
    #             size = f"{parts[2]} {parts[3]}"
    #             modified = f"{parts[4]} {parts[5]} {parts[6]}"
    #             models.append([parts[0], parts[1], size, modified])

    #     if models:
    #         table = Table(title="Available Models")
    #         table.add_column("NAME", justify="left")
    #         table.add_column("ID", justify="left")
    #         table.add_column("SIZE", justify="left")
    #         table.add_column("MODIFIED", justify="left")
            
    #         for model in models:
    #             table.add_row(*model)
    #         console.print(table)
    
    # Show running containers section (will be empty if none running)
    typer.echo("\n🔍 Running Containers:")
    containers = []
    if container_result.stdout.strip():
        for line in container_result.stdout.strip().split('\n'):
            container = json.loads(line)
            containers.append([
                container['Names'],
                container['Status'],
                container['Ports']
            ])
    
    if containers:
        table = Table(title="Running Containers")
        table.add_column("NAME", justify="left")
        table.add_column("STATUS", justify="left")
        table.add_column("PORTS", justify="left")
        for container in containers:
            table.add_row(*container)
        console.print(table)
