import typer
from solo_server.commands import run, stop, status, benchmark, download_hf as download  
from solo_server.main import setup

app = typer.Typer()

# Commands
app.command()(run.run)
app.command()(stop.stop)
app.command()(status.status)
app.command()(download.download)
app.command()(benchmark.benchmark)
app.command()(setup)


if __name__ == "__main__":
    app()
