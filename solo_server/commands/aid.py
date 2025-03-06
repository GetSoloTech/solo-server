import sys
import subprocess
import typer

def aid (query: str):
    # Check if docker is running
    try:
        subprocess.run(["docker", "ps"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        typer.echo("Solo server not running. Please start solo-server first.")
        return
    
    # Execute the query in the solo-ollama container.
    try:
        result = subprocess.run(
            ["docker", "exec", "solo-ollama", "ollama", "ask", query],
            capture_output=True, text=True, check=True
        )
        typer.echo(result.stdout)
    except subprocess.CalledProcessError:
        typer.echo("Failed to get response from the LLM.")

if __name__ == "__main__":
    # If invoked with ">>" as the first argument, join the remaining tokens as the query.
    if len(sys.argv) > 1 and sys.argv[1] == ">>":
        query_text = " ".join(sys.argv[2:])
        aid(query_text)
    else:
        typer.echo("Usage: solo >> <your query>")
