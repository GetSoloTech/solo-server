import typer
import requests
import json
from solo_server.main import setup
from solo_server.commands import serve, status, stop, download_hf as download # models, remove,

app = typer.Typer()

# Register commands
app.command()(setup)
app.command()(serve.serve)
app.command()(status.status)
# app.command(models.models)
# app.command()(remove.remove)
app.command()(stop.stop)
app.command()(download.download)

if __name__ == "__main__":
    app()
