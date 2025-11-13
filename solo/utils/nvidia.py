import subprocess
import typer

def is_cuda_toolkit_installed():
    """Check if CUDA Toolkit is installed by running nvcc command."""
    try:
        result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            return False
    except FileNotFoundError:
        return False
                
def check_nvidia_toolkit(os_name) -> bool:
    """
    Checks if NVIDIA toolkit is properly installed based on the operating system.
    """
    if os_name == "Linux":
        try:
            result = subprocess.run("docker info | grep -i nvidia", 
                                 shell=True, 
                                 check=True, 
                                 capture_output=True, 
                                 text=True)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False
    elif os_name == "Windows":
        try:
            subprocess.run("nvidia-smi", 
                         check=True, 
                         capture_output=True, 
                         text=True)
            return True
        except subprocess.CalledProcessError:
            return False
    return False
    

def install_nvidia_toolkit_linux():
    """
    Installs the NVIDIA Container Toolkit on Linux (Debian & Ubuntu).
    """
    typer.echo("Configuring the repository")
    try:
        subprocess.run("curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg", shell=True, check=True)
        subprocess.run("curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list", shell=True, check=True)
        subprocess.run("sudo apt-get update", shell=True, check=True)

        typer.echo("Installing Nvidia Container Toolkit")
        subprocess.run("sudo apt-get install -y nvidia-container-toolkit", shell=True, check=True)
        subprocess.run("sudo nvidia-ctk runtime configure --runtime=docker", shell=True, check=True)
        subprocess.run("sudo systemctl restart docker", shell=True, check=True)

        typer.echo("NVIDIA Container Toolkit installed successfully on Linux.")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Failed to install NVIDIA Container Toolkit on Linux. Error: {e}", err=True)


def install_nvidia_toolkit_windows():
    """
    Provide a structured step-by-step guide for Windows users to configure
    their system for NVIDIA GPU support, including driver & CUDA installation.
    """
    # Step-by-step instructions
    typer.secho("\n========================================", fg=typer.colors.CYAN)
    typer.secho(" Windows NVIDIA GPU Setup ", fg=typer.colors.CYAN, bold=True)
    typer.secho("========================================\n", fg=typer.colors.CYAN)

    typer.echo("Follow these steps to enable NVIDIA GPU support on Windows:\n")

    steps = [
        ("Step 1: Install or Update NVIDIA Drivers", "https://www.nvidia.com/Download/index.aspx"),
        ("Step 2: Install the NVIDIA CUDA Toolkit", "https://developer.nvidia.com/cuda-downloads")
    ]
    for step_num, (step_title, link) in enumerate(steps, start=1):
        typer.secho(f"{step_title}", fg=typer.colors.BRIGHT_GREEN)
        typer.echo(f"   Link: {link}\n")

    typer.echo("Once you've completed the above steps:")
    typer.echo(" - Ensure Docker Desktop is installed and running.")
    typer.echo(" - Enable 'Use the WSL 2 based engine' in Docker Desktop settings.\n")
    
    typer.secho("⚠️  Please restart Solo Server after installing the required tools.", fg=typer.colors.YELLOW)
    raise typer.Exit(1)
