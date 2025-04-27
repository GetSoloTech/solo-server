import typer
import os
import json
import subprocess
from datetime import datetime

from enum import Enum
from typing import Optional
from solo_server.config import CONFIG_PATH
from solo_server.config.config_loader import get_server_config
from solo_server.utils.hardware import detect_hardware
from solo_server.utils.server_utils import (start_vllm_server, 
                                            start_ollama_server, 
                                            start_llama_cpp_server, 
                                            is_huggingface_repo, 
                                            pull_model_from_huggingface)
from solo_server.utils.docker_utils import start_docker_engine

class ServerType(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    LLAMACPP = "llama.cpp"

def serve(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="""Model name or path. Can be:
    - HuggingFace repo ID (e.g., 'meta-llama/Llama-3.2-1B-Instruct')
    - Ollama model Registry (e.g., 'llama3.2')
    - Local path to a model file (e.g., '/path/to/model.gguf')
    If not specified, the default model from configuration will be used."""),
    server: Optional[str] = typer.Option(None, "--server", "-s", help="Server type (ollama, vllm, llama.cpp)"), 
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port to run the server on")
):
    """Start a model server with the specified model.
    
    If no server is specified, uses the server type from configuration.
    To set up your configuration, run 'solo setup' first.
    """
    
    # Check if config file exists
    if not os.path.exists(CONFIG_PATH):
        typer.echo("❌ Configuration file not found. Please run 'solo setup' first.", err=True)
        typer.echo("Run 'solo setup' to complete the Solo Server setup and then try again.")
        raise typer.Exit(code=1)
    
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Extract hardware info from config
    hardware_config = config.get('hardware', {})
    use_gpu = hardware_config.get('use_gpu', False)
    cpu_model = hardware_config.get('cpu_model')
    gpu_vendor = hardware_config.get('gpu_vendor')
    os_name = hardware_config.get('os')
    
    # If hardware info isn't in config, detect it
    if not cpu_model or not gpu_vendor or not os_name:
        cpu_model, _, _, gpu_vendor, _, _, _, os_name = detect_hardware()
    
    # Only enable GPU if configured and supported
    gpu_enabled = use_gpu and gpu_vendor in ["NVIDIA", "AMD", "Apple Silicon"]
    
    # Use server from config if not specified
    if not server:
        server = config.get('server', {}).get('type', ServerType.OLLAMA.value)
    else:
        # Normalize server name
        server = server.lower()
    
    # Validate server type
    if server not in [s.value for s in ServerType]:
        typer.echo(f"❌ Invalid server type: {server}. Choose from: {', '.join([s.value for s in ServerType])}", err=True)
        raise typer.Exit(code=1)
    
    # Get server configurations from YAML
    vllm_config = get_server_config('vllm')
    ollama_config = get_server_config('ollama')
    llama_cpp_config = get_server_config('llama_cpp')
    
    # Set default models based on server type
    if not model:
        if server == ServerType.VLLM.value:
            model = vllm_config.get('default_model', "meta-llama/Llama-3.2-1B-Instruct")
        elif server == ServerType.OLLAMA.value:
            model = ollama_config.get('default_model', "llama3.2")
        elif server == ServerType.LLAMACPP.value:
            model = llama_cpp_config.get('default_model', "bartowski/Llama-3.2-1B-Instruct-GGUF/llama-3.2-1B-Instruct-Q4_K_M.gguf")
    
    if not port:
        if server == ServerType.VLLM.value:
            port = vllm_config.get('default_port', 5070)
        elif server == ServerType.OLLAMA.value:
            port = ollama_config.get('default_port', 5070)
        elif server == ServerType.LLAMACPP.value:
            port = llama_cpp_config.get('default_port', 5070)
    
    # Check Docker is installed and running for Docker-based servers
    if server in [ServerType.VLLM.value, ServerType.OLLAMA.value]:
        # Check if Docker is installed
        docker_installed = True
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except FileNotFoundError:
            docker_installed = False
            typer.echo("❌ Docker is not installed on your system.", err=True)
            typer.echo("Please install Docker Desktop from https://www.docker.com/products/docker-desktop/")
            typer.echo("After installation, run 'solo setup'.")
            raise typer.Exit(code=1)
        
        # Check if Docker is running
        docker_running = False
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True)
            docker_running = True
        except subprocess.CalledProcessError:
            docker_running = False
            typer.echo("⚠️  Docker is installed but not running. Trying to start Docker...")
            docker_running = start_docker_engine(os_name)
            
            if not docker_running:
                typer.echo("❌ Could not start Docker automatically.", err=True)
                typer.echo("Please start Docker manually and run 'solo serve' again.")
                raise typer.Exit(code=1)
    
    # Start the appropriate server
    typer.echo(f"\nStarting Solo server...")
    success = False
    original_model_name = model
    server_pretty_name = server.capitalize()
    
    if server == ServerType.VLLM.value:
        try:
            success = start_vllm_server(gpu_enabled, cpu_model, gpu_vendor, os_name, port, model)
            # Display container logs command
            if success:
                typer.echo(f"Use 'docker logs -f {vllm_config.get('container_name', 'solo-vllm')}' to view the logs.")
        except Exception as e:
            typer.echo(f"❌ Failed to start Solo Server: {e}", err=True)
            raise typer.Exit(code=1)
        
    elif server == ServerType.OLLAMA.value:
        # Start Ollama server
        if not start_ollama_server(gpu_enabled, gpu_vendor, port):
            typer.echo("❌ Failed to start Solo Server!", err=True)
            raise typer.Exit(code=1)
        
        # Pull the model if not already available
        try:
            # Check if model exists
            container_name = ollama_config.get('container_name', 'solo-ollama')
            model_exists = subprocess.run(
                ["docker", "exec", container_name, "ollama", "list"],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            
            # Check if this is a HuggingFace model
            if is_huggingface_repo(model):
                # Pull from HuggingFace
                model = pull_model_from_huggingface(container_name, model)
            elif model not in model_exists:
                typer.echo(f"📥 Pulling model {model}...")
                subprocess.run(
                    ["docker", "exec", container_name, "ollama", "pull", model],
                    check=True
                )
            success = True
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model: {e}", err=True)
            raise typer.Exit(code=1)
            
    elif server == ServerType.LLAMACPP.value:
        # Start llama.cpp server with the specified model
        success = start_llama_cpp_server(os_name, model_path=model, port=port)
        if not success:
            typer.echo("❌ Failed to start Solo server", err=True)
            raise typer.Exit(code=1)
    
    # Display server information in the requested format
    if success:
        # Get formatted model name for display
        display_model = original_model_name
        if is_huggingface_repo(original_model_name):
            # For HF models, get the repository name for display
            display_model = original_model_name.split('/')[-1] if '/' in original_model_name else original_model_name
        
        # Save model information to config file
        # Update config with active model information
        config['active_model'] = {
            'server': server,
            'name': display_model,
            'full_model_name': original_model_name,  # Save the complete model name
            'last_used': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save updated config
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Print server information
        typer.secho("✅ Solo Server is running", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.secho(f"Model  - {display_model}", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho(f"URL    - http://localhost:{port}", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho(f"Use 'solo test' to test the server.", fg=typer.colors.BRIGHT_MAGENTA)
