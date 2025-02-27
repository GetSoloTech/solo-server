import typer
from solo_server.commands import status, serve, stop, download_hf as download
from solo_server.commands import finetune
from solo_server.main import setup

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

if __name__ == "__main__":
    app()
