import os
import typer
from rich.console import Console

console = Console()

def list_downloaded_models(download_dir: str = "./downloaded_models") -> None:
    """
    Lists the models that have been downloaded by checking the given directory.
    """
    console.print("[bold cyan]Downloaded Models:[/bold cyan]")
    if not os.path.exists(download_dir):
        console.print("No downloaded models directory found.", style="bold red")
        return
    models = os.listdir(download_dir)
    if not models:
        console.print("No downloaded models found.", style="yellow")
    else:
        for model in models:
            console.print(f" - {model}")

def list_available_models() -> None:
    """
    Lists models available for download.
    """
    # This is a placeholder list. Replace with an API call or file read if needed.
    available_models = [
        "model-A",
        "model-B",
        "model-C",
    ]
    console.print("[bold cyan]Available Models for Download:[/bold cyan]")
    for model in available_models:
        console.print(f" - {model}")

def solo_list(download_dir: str = "./downloaded_models") -> None:
    """
    Lists both downloaded models and available models.
    """
    console.print("[bold green]Solo List of Models[/bold green]\n")
    list_downloaded_models(download_dir)
    console.print("")  # Blank line between sections
    list_available_models()

app = typer.Typer()

@app.command("list")
def list_models(
    download_dir: str = typer.Option("./downloaded_models", help="Directory where models are downloaded.")
):
    """
    Command to list downloaded models and available models for download.
    """
    solo_list(download_dir)

if __name__ == "__main__":
    app()
