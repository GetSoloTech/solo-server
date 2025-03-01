import os
import json
import typer
import subprocess
import shutil

from enum import Enum
from solo_server.config import CONFIG_PATH
from solo_server.utils.docker_utils import start_docker_engine
from solo_server.utils.hardware import detect_hardware, display_hardware_info, recommended_server
from solo_server.utils.nvidia import check_nvidia_toolkit, install_nvidia_toolkit_linux, install_nvidia_toolkit_windows


class ServerType(str, Enum):
    OLLAMA = "Ollama"
    VLLM = "vLLM"
    LLAMACPP = "Llama.cpp"

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

    recmd_server = recommended_server(memory_gb, gpu_vendor, gpu_memory) 
    
    def server_type_prompt(value: str) -> ServerType:
        normalized_value = value.lower()
        for server in ServerType:
            if server.value.lower() == normalized_value:
                return server
        raise typer.BadParameter(f"Invalid server type: {value}")

    server_choice = typer.prompt(
        "\nChoose server",
        type=server_type_prompt,
        default=recmd_server,
    )
    
    # GPU Configuration
    use_gpu = False
    if gpu_vendor in ["NVIDIA", "AMD", "Intel", "Apple Silicon"]:
        use_gpu = True
        if use_gpu and gpu_vendor == "NVIDIA":
            if not check_nvidia_toolkit(os_name):
                if typer.confirm("NVIDIA GPU Detected, but GPU drivers not found. Install now?", default=True):
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
    
    # Save GPU configuration to config file
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    config['hardware'] = {'use_gpu': use_gpu}
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    
    # Docker Engine Check for Docker-based servers
    if server_choice in [ServerType.OLLAMA, ServerType.VLLM]:
        # Check Docker installation
        docker_path = shutil.which("docker")
        if not docker_path:
            typer.echo("❌ Docker is not installed or not in the system PATH. Please install Docker first.\n", err=True)
            typer.secho("Install Here: https://docs.docker.com/get-docker/", fg=typer.colors.GREEN)
            raise typer.Exit(code=1)

        
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=20)
        except subprocess.CalledProcessError:
            typer.echo("Docker daemon is not running. Attempting to start Docker...", err=True)
            if not start_docker_engine(os_name):
                raise typer.Exit(code=1)
            # Re-check if Docker is running
            try:
                subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=20)
            except subprocess.CalledProcessError:
                typer.echo("Try restarting the terminal with admin privileges and close any instances of podman.", err=True)
                raise typer.Exit(code=1)

            
    # Server setup
    try:
        if server_choice == ServerType.VLLM:
            # pull the appropriate vLLM image
            typer.echo("📥 Pulling vLLM image...")
            if gpu_vendor == "NVIDIA" and use_gpu:
                subprocess.run(["docker", "pull", "vllm/vllm-openai:latest"], check=True)
            elif gpu_vendor == "AMD" and use_gpu:
                subprocess.run(["docker", "pull", "rocm/vllm"], check=True)
            elif cpu_model and "Apple" in cpu_model:
                subprocess.run(["docker", "pull", "getsolo/vllm-arm"], check=True)
            elif cpu_model and any(vendor in cpu_model for vendor in ["Intel", "AMD"]):
                subprocess.run(["docker", "pull", "getsolo/vllm-cpu"], check=True)
            else:
                typer.echo("❌ vLLM currently does not support your machine", err=True)
                return False
                
            typer.secho(
                "✅ Solo server vLLM setup complete! Use 'solo serve -s vllm -m MODEL_NAME' to start the server.",
                fg=typer.colors.BRIGHT_GREEN
            )
            
        elif server_choice == ServerType.OLLAMA:
            # Just pull the Ollama image
            typer.echo("📥 Pulling Ollama image...")
            if gpu_vendor == "AMD" and use_gpu:
                subprocess.run(["docker", "pull", "ollama/ollama-rocm"], check=True)
            else:
                subprocess.run(["docker", "pull", "ollama/ollama"], check=True)
            
            typer.secho(
                "✅ Solo server ollama setup complete! \nUse 'solo serve -s ollama -m MODEL_NAME' to start the server.",
                fg=typer.colors.BRIGHT_GREEN
            )
            
        elif server_choice == ServerType.LLAMACPP:
            from solo_server.utils.server_utils import setup_llama_cpp_server
            setup_success = setup_llama_cpp_server(use_gpu, gpu_vendor, os_name, install_only=True)
            if setup_success:
                typer.secho(
                    "✅ Solo server llama.cpp setup complete! Use 'solo serve -s llama.cpp -m MODEL_PATH' to start the server.",
                    fg=typer.colors.BRIGHT_GREEN
                )
            else:
                typer.echo("❌ Failed to setup llama.cpp", err=True)
    
    except Exception as e:
        typer.echo(f"\n❌ Setup failed: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    typer.run(setup)