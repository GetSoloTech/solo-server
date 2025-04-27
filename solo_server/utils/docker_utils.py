import subprocess
import time
import typer

def start_docker_engine(os_name):
    """
    Attempts to start the Docker engine based on the OS.
    """
    typer.echo("Starting the Docker engine...")
    try:
        if os_name == "Windows":
            try:
                subprocess.run(["sc", "start", "docker"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                typer.echo("Docker service is not registered. Trying to start Docker Desktop...", err=True)

                # Run PowerShell command to get Docker path
                result = subprocess.run(
                    ["powershell", "-Command", "(Get-Command docker | Select-Object -ExpandProperty Source)"],
                    capture_output=True,
                    text=True
                )

                docker_path = result.stdout.strip()
                if "Docker" in docker_path:
                    # Find the second occurrence of 'Docker'
                    parts = docker_path.split("\\")
                    docker_index = [i for i, part in enumerate(parts) if part.lower() == "docker"]

                    if len(docker_index) >= 2:
                        docker_desktop_path = "\\".join(parts[:docker_index[1] + 1]) + "\\Docker Desktop.exe"

                        typer.echo(f"Starting Docker Desktop from: {docker_desktop_path}")
                        subprocess.run(["powershell", "-Command", f"Start-Process '{docker_desktop_path}' -Verb RunAs"], check=True)
                    else:
                        typer.echo("❌ Could not determine Docker Desktop path.", err=True)
                else:
                    typer.echo("❌ Docker is not installed or incorrectly configured.", err=True)

        elif os_name == "Linux":
            try:
                # First try systemctl for system Docker service
                subprocess.run(["sudo", "systemctl", "start", "docker"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                try:
                    # If systemctl fails, try starting Docker Desktop
                    subprocess.run(["systemctl", "--user", "start", "docker-desktop"], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    typer.echo("❌ Failed to start Docker. Please start manually", err=True)

        elif os_name == "Darwin":  # macOS
            subprocess.run(["open", "/Applications/Docker.app"], check=True, capture_output=True)

        # Wait for Docker to start
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                subprocess.run(["docker", "info"], check=True, capture_output=True)
                typer.echo("✅ Docker is running")
                return True
            except subprocess.CalledProcessError:
                time.sleep(5)

        typer.echo("❌ Docker did not start within the timeout period.", err=True)
        return False

    except subprocess.CalledProcessError:
        typer.echo("❌ Failed to start Docker. Please start Docker with admin privileges manually.", err=True)
        return False