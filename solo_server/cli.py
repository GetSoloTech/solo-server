import typer
import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from solo_server.commands import status, serve, stop, download_hf as download
from solo_server.commands import finetune
from solo_server.main import setup

console = Console()

app = typer.Typer()
finetune_app = typer.Typer()
app.add_typer(finetune_app, name="finetune")

# Register commands
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
        ..., help="Provide a professional and concise prompt to send to the core LLM."
    )
):
    """
    Sends the provided prompt to the core LLM and streams only the parsed markdown output.

    This command replicates the following cURL request:
    
        curl -X POST http://127.0.0.1:5070/predict \
             -H 'Content-Type: application/json' \
             -d '{"prompt": "<prompt>"}'

    If the prompt exceeds 9000 characters, an error is returned.
    """
    # Combine multiple words into a single string and remove excess whitespace
    prompt_text = " ".join(prompt).strip()
    
    # Check if the prompt exceeds 9000 characters
    if len(prompt_text) > 9000:
        typer.echo("[red]Error: The provided prompt exceeds 9000 characters.[/red]", err=True)
        raise typer.Exit(code=1)
    
    url = "http://127.0.0.1:5070/predict"
    headers = {"Content-Type": "application/json"}
    data = {"prompt": prompt_text}

    # Display a blue spinner while sending the request to the core LLM
    with console.status("[bold blue]Sending prompt to the core LLM...[/bold blue]", spinner="dots"):
        try:
            response = requests.post(url, json=data, headers=headers, stream=True)
            response.raise_for_status()
        except requests.RequestException as e:
            typer.echo(f"[red]Error sending prompt: {e}[/red]", err=True)
            raise typer.Exit(code=1)
    
    # Stream the response, parsing the JSON to extract only the "output" markdown
    output_markdown = ""
    with Live(console=console, refresh_per_second=4) as live:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data_chunk = json.loads(line)
                    # Append the value from the "output" field
                    output_markdown += data_chunk.get("output", "")
                except json.JSONDecodeError:
                    # Fallback: if the line is not valid JSON, append it as-is
                    output_markdown += line
                live.update(Panel(output_markdown, title="Solo Core Response", border_style="blue"))

if __name__ == "__main__":
    app()
