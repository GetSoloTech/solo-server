import sys
import typer
import requests
from litgpt import LLM
from rich.console import Console

console = Console()

CORE_SERVER_PORT = 5070  # Change this if your core server runs on a different port
CORE_SERVER_URL = f"http://localhost:{CORE_SERVER_PORT}/generate"

def redirect_to_core_server(query: str, port: int = CORE_SERVER_PORT) -> None:
    """
    Redirect the given query to the core server via an HTTP POST request.
    """
    url = f"http://localhost:{port}/generate"
    try:
        response = requests.post(url, json={"prompt": query})
        response.raise_for_status()
        console.print("[success]Response from core server:[/success]")
        console.print(response.text)
    except Exception as e:
        console.print(f"[warning]Error redirecting to core server: {e}[/warning]")

def query_llm(query: str) -> None:
    """
    If the query exceeds 9000 characters, show an error.
    Otherwise, load the model and generate a response.
    """
    if len(query) > 9000:
        typer.echo("Error: Your query exceeds the maximum allowed length of 9000 characters. It's over 9000!")
        raise typer.Exit(1)
    
    # Load the model and generate a response while showing a spinner
    llm = LLM.load("Qwen/Qwen2.5-1.5B-Instruct")
    with console.status("Generating response...", spinner="dots"):
        response = llm.generate(query)
    typer.echo(response)

def interactive_mode():
    console.print("Interactive Mode (type 'exit' or 'quit' to end):", style="bold green")
    while True:
        query_text = input(">> ").strip()
        if query_text.lower() in ("exit", "quit"):
            break
        # If the query starts with "solo @@", redirect to the core server
        if query_text.startswith("solo @@"):
            # Remove the "solo @@" prefix before sending the query
            core_query = query_text[len("solo @@"):].strip()
            redirect_to_core_server(core_query)
        else:
            query_llm(query_text)

if __name__ == "__main__":
    # If invoked with "@@" as the first argument, treat the rest as the query.
    # Otherwise, launch interactive mode.
    if len(sys.argv) > 1 and sys.argv[1] == "@@":
        if len(sys.argv) > 2:
            query_text = " ".join(sys.argv[2:]).strip()
        else:
            typer.echo("Enter your query (end with EOF / Ctrl-D):")
            query_text = sys.stdin.read().strip()
        # If the query starts with "solo @@", remove that prefix.
        if query_text.startswith("solo @@"):
            query_text = query_text[len("solo @@"):].strip()
        redirect_to_core_server(query_text)
    else:
        interactive_mode()
