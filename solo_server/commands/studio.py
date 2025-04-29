import typer
from rich.console import Console
import webbrowser

console = Console()

def studio() -> None:
    """
    Opens the studio page in a web browser.
    """
    url = "https://studio.getsolo.tech"
    console.print(f"🚀 Opening Studio: [bold]{url}[/bold]...")
    try:
        webbrowser.open(url)
        console.print("✅ Studio opened successfully.")
    except Exception as e:
        console.print(f"❌ Failed to open Studio: {e}", style="bold red")
    except KeyboardInterrupt:
        console.print("❌ Operation cancelled by user.", style="bold red")

if __name__ == "__main__":
    studio()
