import typer
import subprocess
import shutil
import socket
import time
from enum import Enum
from pathlib import Path
from solo_server.utils.docker_utils import start_docker_engine
from solo_server.utils.hardware import detect_hardware, display_hardware_info
from solo_server.utils.nvidia import check_nvidia_toolkit, install_nvidia_toolkit_linux, install_nvidia_toolkit_windows
from solo_server.utils.server_utils import setup_vllm_server, setup_ollama_server, setup_llama_cpp_server

class ServerType(str, Enum):
    OLLAMA = "Ollama"
    VLLM = "vLLM"
    LLAMACPP = "Llama.cpp"
    CUSTOM = "Custom API"

def setup():
    """Interactive setup for Solo Server environment"""
    # Display hardware info
    display_hardware_info(typer)
    cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name = detect_hardware()
    
    typer.echo("\n🔧 Starting Solo Server Setup...\n")
    
    # Server Selection
    typer.echo("📊 Available Server Options:")
    for server in ServerType:
        typer.echo(f"  • {server.value}")
    
    def server_type_prompt(value: str) -> ServerType:
        normalized_value = value.lower()
        for server in ServerType:
            if server.value.lower() == normalized_value:
                return server
        raise typer.BadParameter(f"Invalid server type: {value}")

    server_choice = typer.prompt(
        "\nChoose server",
        type=server_type_prompt,
        default="ollama",
    )

    # GPU Configuration
    use_gpu = False
    if gpu_vendor in ["NVIDIA", "AMD", "Intel",  "Apple Silicon"]:
        use_gpu = typer.confirm(
                f"\n🎮 {gpu_vendor} GPU detected ({gpu_model}). Use GPU acceleration?",
                default=True
            )
        if use_gpu and gpu_vendor == "NVIDIA":
            if not check_nvidia_toolkit(os_name):
                if typer.confirm("NVIDIA toolkit not found. Install now?", default=True):
                    if os_name == "Linux":
                        try:
                            install_nvidia_toolkit_linux()
                        except subprocess.CalledProcessError as e:
                            typer.echo(f"Failed to install NVIDIA toolkit: {e}", err=True)
                            use_gpu = False
                    elif os_name == "Windows":
                        try:
                            install_nvidia_toolkit_windows()
                        except subprocess.CalledProcessError as e:
                            typer.echo(f"Failed to install NVIDIA toolkit: {e}", err=True)
                            use_gpu = False
                else:
                    typer.echo("Falling back to CPU inference.")
                    use_gpu = False
    
    # Docker Engine Check
    if server_choice in [ServerType.OLLAMA, ServerType.VLLM]:
        # Check Docker installation
        docker_path = shutil.which("docker")
        if not docker_path:
            typer.echo("❌ Docker is not installed or not in the system PATH. Please install Docker first.\n", err=True)
            typer.secho("Install Here: https://docs.docker.com/get-docker/", fg=typer.colors.GREEN)
            raise typer.Exit(code=1)
        else:
            try:
                subprocess.run([docker_path, "info"], check=True, capture_output=True, timeout=30)
            except subprocess.CalledProcessError:
                typer.echo("Docker daemon is not running. Attempting to start Docker...", err=True)
                if not start_docker_engine(os_name):
                    raise typer.Exit(code=1)
                # Re-check if Docker is running
                try:
                    subprocess.run([docker_path, "info"], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    typer.echo("Try running the terminal with admin privileges.", err=True)
                    raise typer.Exit(code=1)
            
    # Server setup
    try:
        if server_choice == ServerType.VLLM:
            setup_success = setup_vllm_server(use_gpu, cpu_model, gpu_vendor)
            if setup_success:
                def is_port_in_use(port: int) -> bool:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        return s.connect_ex(('localhost', port)) == 0

                # Wait for the port to be in use
                port = 8000
                timeout = 60  # seconds
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if is_port_in_use(port):
                        typer.secho(
                            f"Access the API at: http://localhost:{port}",
                            fg=typer.colors.BLUE
                        )
                        typer.secho(
                            "If you experience issues, check docker logs with 'docker logs solo-vllm'\n",
                            fg=typer.colors.YELLOW
                        )
                        break
                    time.sleep(1)
                else:
                    typer.secho(
                        f"Port {port} is not listening after {timeout} seconds. Please check docker logs for for more information.\n",
                        fg=typer.colors.RED
                    )
            
        elif server_choice == ServerType.OLLAMA:
            setup_success = setup_ollama_server(use_gpu, gpu_vendor)
            if setup_success:
                typer.secho(
                    "Access the API at: http://localhost:11434\n",
                    fg=typer.colors.BLUE
                )
            
        elif server_choice == ServerType.LLAMACPP:
            setup_success = setup_llama_cpp_server(use_gpu, gpu_vendor, os_name)
            if setup_success:
                typer.secho(
                    "Access the API at: http://localhost:8000.",
                    fg=typer.colors.BLUE
                )
                typer.secho(
                    "kill the terminal to stop the server.\n",
                    fg=typer.colors.BLUE
                )

        elif server_choice == ServerType.CUSTOM:
            api_url = typer.prompt("Enter your custom API endpoint")
            api_key = typer.prompt("Enter your API key (optional)", default="")
            
            # Save custom configuration
            config_dir = Path.home() / ".solo"
            config_dir.mkdir(exist_ok=True)
            
            with open(config_dir / "config.ini", "w") as f:
                f.write(f"[custom]\napi_url={api_url}\napi_key={api_key}\n")
            
            typer.secho("\n✅ Custom API configuration saved!", fg=typer.colors.BRIGHT_GREEN)
    
    except Exception as e:
        typer.echo(f"\n❌ Unexpected error: {e}", err=True)
        typer.echo("Please check docker logs for more information.", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    typer.run(setup)