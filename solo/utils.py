import subprocess
import typer

def handle_error(func):
    """Decorator for handling errors in CLI commands."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Error: {e}", err=True)
        except Exception as e:
            typer.echo(f"⚠️ Unexpected error: {e}", err=True)
    return wrapper

def run_command(command):
    """Executes shell commands safely."""
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise typer.Exit(code=1)
