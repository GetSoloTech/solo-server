import typer
import requests
from rich.console import Console
from rich.panel import Panel
from solo_server.commands import status, serve, stop, download_hf as download
from solo_server.commands import finetune
from solo_server.main import setup

console = Console()

app = typer.Typer()
finetune_app = typer.Typer()
app.add_typer(finetune_app, name="finetune")

# Commands
app.command()(stop.stop)
app.command()(status.status)
app.command()(download.download)
app.command()(setup)
app.command()(serve.serve)

# Finetune commands
finetune_app.command(name="gen")(finetune.gen)
finetune_app.command(name="status")(finetune.status)
finetune_app.command(name="download")(finetune.download)
finetune_app.command(name="run")(finetune.run)


@app.command(name="@@")
def send_prompt(
    prompt: list[str] = typer.Argument(
        ..., help="The prompt to send (can be multiple words)"
    )
):
    """
    Sends the given prompt to the core LLM and prints the response.
    
    This command replicates:
    curl -X POST http://127.0.0.1:5070/predict -H 'Content-Type: application/json' -d '{"prompt": "<prompt>"}'
    
    If the prompt exceeds 9000 characters, it returns a "Vegeta over 9000 error".
    """
    # Combine multiple words into a single string
    prompt_text = " ".join(prompt)
    
    # Check if the prompt length exceeds 9000 characters
    if len(prompt_text) > 9000:
        typer.echo("[red]Vegeta over 9000 error: input exceeds 9000 characters[/red]", err=True)
        raise typer.Exit(code=1)
    
    url = "http://127.0.0.1:5070/predict"
    headers = {"Content-Type": "application/json"}
    data = {"prompt": prompt_text}

    # Display a blue spinner while sending the request
    with console.status("[bold blue]Sending prompt to core LLM...[/bold blue]", spinner="dots"):
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            typer.echo(f"[red]Error sending prompt: {e}[/red]", err=True)
            raise typer.Exit(code=1)
    
    # Extract output from the JSON response
    output = response.json().get("output", "No output received.")
    
    # Display the output in a blue-bordered panel
    console.print(Panel(output, title="Solo Core Response", border_style="blue"))


if __name__ == "__main__":
    app()
