import typer
import requests
import json
from solo_server.main import setup
from solo_server.commands import serve, status, stop, test, download_hf as download, models_list as models

app = typer.Typer()

# Register commands
app.command()(setup)
app.command()(serve.serve)
app.command()(status.status)
app.command()(models.list)
app.command()(test.test)
app.command()(stop.stop)
app.command()(download.download)

if __name__ == "__main__":
    app()
