import os 
import json
import typer
import click
import sys
import time
import shutil
import subprocess
from solo_server.config import CONFIG_PATH
from solo_server.utils.hf_utils import select_best_model_file
from solo_server.config.config_loader import load_config, get_server_config, get_timeout_config
from solo_server.utils.llama_cpp_utils import (is_port_in_use, 
                                              find_process_by_port,
                                              preprocess_model_path, 
                                              is_llama_cpp_installed)

def start_vllm_server(gpu_enabled: bool, cpu: str = None, gpu_vendor: str = None, 
                      os_name:str = None, port: int = None, model: str = None):
    """Setup vLLM server with Docker"""
    # Load vLLM configuration from YAML
    vllm_config = get_server_config('vllm')
    timeout_config = get_timeout_config()
    
    # Use default values from config if not provided
    port = port or vllm_config.get('default_port', 8000)
    model = model or vllm_config.get('default_model', "meta-llama/Llama-3.2-1B-Instruct")
    container_name = vllm_config.get('container_name', 'solo-vllm')
    
    # Initialize container_exists flag
    container_exists = False
    try:
        # Check if container exists (running or stopped)
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={container_name}"], 
            capture_output=True, 
            text=True
        ).stdout.strip()

        if container_exists:
            # Check if container is running
            check_cmd = ["docker", "ps", "-q", "-f", f"name={container_name}"]
            is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
            if is_running:
                subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)
                subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
                container_exists = False
            else:
                subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
                container_exists = False
                   
        if not container_exists:
            # Check if port is available
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # Try to bind to the port to check if it's available
                sock.bind(('127.0.0.1', port))
                sock.close()
            except socket.error:
                typer.echo(f"❌ Port {port} is already in use, please try a different port", err=True)
                typer.echo(f"Run 'solo stop' to stop all running servers.")
                return False
            
            docker_run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{port}:8000",
                "--ipc=host"
            ]

            # If model is provided, use it directly
            if model:
                # Determine if it's a local path or HuggingFace model
                if os.path.exists(os.path.expanduser(model)):
                    model_source = "local"
                    model_name = os.path.abspath(os.path.expanduser(model))
                    
                    # Add volume mount for local model
                    local_model_dir = os.path.dirname(model_name)
                    local_model_dir = local_model_dir.replace('\\', '/')
                    container_model_dir = "/models"
                    model_path = os.path.join(container_model_dir, os.path.basename(model_name)).replace('\\', '/')
                    docker_run_cmd += [
                        "-v", f"{local_model_dir}:{container_model_dir}"
                    ]
                else:
                    model_source = "huggingface"
                    model_name = model
    
                    # Get HuggingFace token from config file 
                    hf_token = os.getenv('HUGGING_FACE_TOKEN', '')
                    if not hf_token:  # If not in env, try config file
                        if os.path.exists(CONFIG_PATH):
                            with open(CONFIG_PATH, 'r') as f:
                                config = json.load(f)
                                hf_token = config.get('hugging_face', {}).get('token', '')

                    # Add volume mount for HuggingFace cache
                    docker_run_cmd += [ 
                        "--env", f"HUGGING_FACE_HUB_TOKEN={hf_token}",
                        "-v", f"{os.path.expanduser('~')}/.cache/huggingface:/root/.cache/huggingface"
                    ]
            
            # Get appropriate docker image from config
            if gpu_vendor == "NVIDIA" and gpu_enabled:
                image = vllm_config.get('images', {}).get('nvidia', "vllm/vllm-openai:latest")
                docker_run_cmd += ["--gpus", "all"]
            elif gpu_vendor == "AMD" and gpu_enabled:
                image = vllm_config.get('images', {}).get('amd', "rocm/vllm")
                docker_run_cmd += [
                    "--network=host",
                    "--group-add=video", 
                    "--cap-add=SYS_PTRACE",
                    "--security-opt", "seccomp=unconfined",
                    "--device", "/dev/kfd",
                    "--device", "/dev/dri"
                ]
            elif cpu == "Apple":
                image = vllm_config.get('images', {}).get('apple', "getsolo/vllm-arm")
            elif cpu in ["Intel", "AMD"]:
                image = vllm_config.get('images', {}).get('cpu', "getsolo/vllm-cpu")
            else:
                typer.echo("❌ Solo server vLLM currently do not support your machine", err=True)
                return False

            # Check if image exists
            image_exists = subprocess.run(
                ["docker", "images", "-q", image],
                capture_output=True,
                text=True
            ).stdout.strip()

            if not image_exists:
                typer.echo(f"❌ Solo server is not setup. Please run 'solo setup' first.", err=True)
                return False

            docker_run_cmd.append(image)

            if gpu_vendor == "NVIDIA" and gpu_enabled:
                # Check GPU compute capability
                gpu_info = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv"],
                    capture_output=True,
                    text=True
                ).stdout.strip().split('\n')[-1]
                compute_cap = float(gpu_info.split(',')[-1].strip())

            # Add vLLM arguments after the image name
            if model_source == "huggingface":
                docker_run_cmd += ["--model", model_name]
            else:
                docker_run_cmd += [
                    "--model", model_path,
                ]

            # Get max_model_len from config
            max_model_len = vllm_config.get('max_model_len', 4096)
            docker_run_cmd += ["--max_model_len", str(max_model_len)]

            if gpu_vendor == "NVIDIA":
                # Get GPU memory utilization from config
                gpu_memory_utilization = vllm_config.get('gpu_memory_utilization', 0.85)
                docker_run_cmd += [
                    "--gpu_memory_utilization", str(gpu_memory_utilization)
                ]
                if 5 < compute_cap < 8:
                    docker_run_cmd += ["--dtype", "half"]

            subprocess.run(docker_run_cmd, check=True, capture_output=True)
            
            # Check docker logs for any errors
            try:
                logs = subprocess.run(
                    ["docker", "logs", container_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if logs.stderr:
                    typer.echo(f"⚠️ Server logs show errors:\n{logs.stderr}", err=True)
                if logs.stdout:
                    typer.echo(f"Server logs:\n{logs.stdout}")
            except subprocess.CalledProcessError as e:
                typer.echo(f"❌ Failed to fetch docker logs: {e}", err=True)

        # Wait for container to be ready with timeout
        server_timeout = timeout_config.get('server_start', 30)
        start_time = time.time()
        while time.time() - start_time < server_timeout:
            try:
                subprocess.run(
                    ["docker", "exec", container_name, "ps", "aux"],
                    check=True,
                    capture_output=True,
                )
                return True
            except subprocess.CalledProcessError:
                time.sleep(1)
        
        typer.echo("❌ vLLM server failed to start within timeout", err=True)
        return False

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Docker command failed: {e}", err=True)
        # Cleanup on failure
        if container_exists:
            subprocess.run(["docker", "stop", container_name], check=False)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        return False

def start_ollama_server(gpu_enabled: bool = False, gpu_vendor: str = None, port: int = None):
    """Setup solo-server Ollama environment."""
    # Load Ollama configuration from YAML
    ollama_config = get_server_config('ollama')
    timeout_config = get_timeout_config()
    
    # Use default values from config if not provided
    port = port or ollama_config.get('default_port', 11434)
    container_name = ollama_config.get('container_name', 'solo-ollama')
    
    # Initialize container_exists flag
    container_exists = False

    try:
        # Check if container exists (running or stopped)
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={container_name}"], 
            capture_output=True, 
            text=True
        ).stdout.strip()

        if container_exists:
            # Check if container is running
            check_cmd = ["docker", "ps", "-q", "-f", f"name={container_name}"]
            is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
            if not is_running:
                subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
                container_exists = False
            else:
                subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)
                subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
                container_exists = False

        if not container_exists:
            # port availability check
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # Try to bind to the port to check if it's available
                sock.bind(('127.0.0.1', port))
                sock.close()
            except socket.error:
                typer.echo(f"❌ Port {port} is already in use, please try a different port", err=True)
                typer.echo(f"Run 'solo stop' to stop all running servers.")
                return False
                
            # Get appropriate docker image from config
            if gpu_vendor == "AMD" and gpu_enabled:
                image = ollama_config.get('images', {}).get('amd', "ollama/ollama:rocm")
            else:
                image = ollama_config.get('images', {}).get('default', "ollama/ollama")

            # Check if Ollama image exists
            try:
                subprocess.run(["docker", "image", "inspect", image], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                typer.echo("❌ Solo server is not setup. Please run 'solo setup' first", err=True)
                return False

            # Start Ollama container
            docker_run_cmd = ["docker", "run", "-d", "--name", container_name, "-p", f"{port}:11434"]
            
            # Check if local ollama directory exists
            home_dir = os.path.expanduser("~")
            local_ollama_dir = os.path.join(home_dir, ".ollama")
            
            if os.path.exists(local_ollama_dir) and os.path.isdir(local_ollama_dir):
                typer.echo(f"Found existing Ollama directory at {local_ollama_dir}")
                # Use local directory instead of volume
                docker_run_cmd.extend(["-v", f"{local_ollama_dir}:/root/.ollama"])
            else:
                typer.echo("No existing Ollama directory found. Creating a new Docker volume.")
                # Use Docker volume for storage
                docker_run_cmd.extend(["-v", "ollama:/root/.ollama"])
            
            if gpu_vendor == "NVIDIA" and gpu_enabled:
                docker_run_cmd += ["--gpus", "all"]
            elif gpu_vendor == "AMD" and gpu_enabled:
                docker_run_cmd += ["--device", "/dev/kfd", "--device", "/dev/dri"]
            
            docker_run_cmd.append(image)
            subprocess.run(docker_run_cmd, check=True, capture_output=True)

        # Wait for container to be ready with timeout
        server_timeout = timeout_config.get('server_start', 30)
        start_time = time.time()
        while time.time() - start_time < server_timeout:
            try:
                subprocess.run(
                    ["docker", "exec", container_name, "ollama", "list"],
                    check=True,
                    capture_output=True,
                )
                return True
            except subprocess.CalledProcessError:
                time.sleep(1)
        
        typer.echo("❌ Solo server failed to start within timeout", err=True)
        return False

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Docker command failed: {e}", err=True)
        # Cleanup on failure
        if container_exists:
            subprocess.run(["docker", "stop", container_name], check=False)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        return False
    

def start_llama_cpp_server(os_name: str = None, model_path: str = None, port: int = None):
    """
    Start the llama.cpp server.
    
    Parameters:
    os_name (str, optional): The name of the operating system.
    model_path (str, optional): Path to the model file or HuggingFace repo ID.
    port (int, optional): Port to run the server on.
    """
    # Check if llama_cpp is installed
    if not is_llama_cpp_installed():
        typer.echo("❌ Server not found. Please run 'solo setup' first.", err=True)
        return False
        
    # Load llama.cpp configuration from YAML
    llama_cpp_config = get_server_config('llama_cpp')
    
    # Use default values from config if not provided
    port = port or llama_cpp_config.get('default_port', 8080)
    model_path = model_path or llama_cpp_config.get('default_model')
    
    try:
        # Check if port is already in use
        if is_port_in_use(port):
            typer.echo(f"❌ Port {port} is already in use, please try a different port", err=True)
            typer.echo(f"Run 'solo stop' to stop all running servers.")
            return False
        
        # If no model path is provided, prompt the user
        if not model_path:
            typer.echo("Please provide the path to your GGUF model file or a HuggingFace repo ID.")
            model_path = typer.prompt("Enter the model path or repo ID")
            
        # Get HuggingFace token if needed
        hf_token = os.getenv('HUGGING_FACE_TOKEN', '')
        if not hf_token and not os.path.exists(model_path):  # Only check for token if not a local file
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    hf_token = config.get('hugging_face', {}).get('token', '')
        
        # Determine if this is a repo ID or direct path
        hf_repo_id, model_pattern = preprocess_model_path(model_path, hf_token)

        # Build server command
        server_cmd = [
            sys.executable, "-m", "llama_cpp.server",
            "--host", "0.0.0.0",
            "--port", str(port)
        ]
        
        if hf_repo_id and not os.path.exists(model_path):
            # This is a HuggingFace repo ID
            typer.echo(f"Using HuggingFace repo: {hf_repo_id}")
            server_cmd.extend(["--hf_model_repo_id", hf_repo_id])
            server_cmd.extend(["--model", model_pattern])
        else:
            # Direct model path
            model_path = os.path.abspath(os.path.expanduser(model_path))
            if not os.path.exists(model_path):
                typer.echo(f"❌ Model file not found: {model_path}", err=True)
                return False
            server_cmd.extend(["--model", model_path])
        
        if os_name == "Windows":
            # Create a log file for capturing output
            log_dir = os.path.join(os.path.expanduser("~"), ".solo", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "llama_cpp_server.log")
            
            # Start the server in a new console window and keep it open with a pause command
            cmd_str = " ".join(server_cmd) + " & pause"
            process = subprocess.Popen(
                f'start cmd /k "{cmd_str}"',
                shell=True
            )
            typer.echo(f"Solo Server is running in a new terminal window. Use ctrl + c to stop.")
        else:
            # For Unix-like systems, use terminal-specific commands
            if os_name == "Darwin":  # macOS
                # For macOS, use AppleScript to keep the Terminal window open
                script = f'tell app "Terminal" to do script "{" ".join(server_cmd)} ; echo \'\\nServer is running. Press Ctrl+C to stop.\'; bash"'
                terminal_cmd = ["osascript", "-e", script]
                subprocess.Popen(terminal_cmd)
                typer.echo("Server is running in a new Terminal window")
            else:  # Linux and other Unix-like systems
                # Try to detect the terminal and keep it open
                if shutil.which("gnome-terminal"):
                    terminal_cmd = ["gnome-terminal", "--", "bash", "-c", f"{' '.join(server_cmd)}; echo '\\nServer is running. Press Ctrl+C to stop.'; exec bash"]
                    subprocess.Popen(terminal_cmd)
                elif shutil.which("xterm"):
                    terminal_cmd = ["xterm", "-e", f"{' '.join(server_cmd)}; echo '\\nServer is running. Press Ctrl+C to stop.'; exec bash"]
                    subprocess.Popen(terminal_cmd)
                elif shutil.which("konsole"):
                    terminal_cmd = ["konsole", "-e", f"bash -c '{' '.join(server_cmd)}; echo \"\\nServer is running. Press Ctrl+C to stop.\"; exec bash'"]
                    subprocess.Popen(terminal_cmd)
                else:
                    # Fallback to background process if no terminal is found
                    process = subprocess.Popen(
                        server_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True
                    )
                    typer.echo(f"Server is running in the background. Process ID: {process.pid}")
                    return True
                
                typer.echo("Server is running in a new terminal window")
        
        # Wait for the server to start
        time.sleep(2)
        return True
        
    except Exception as e:
        typer.echo(f"❌ Failed to start Solo server: {e}", err=True)
        return False

def is_huggingface_repo(model: str) -> bool:
    """Check if the model string is a HuggingFace repository ID."""
    return model.startswith("hf://") or model.startswith("hf.co/") or "/" in model and not model.startswith("ollama/")

def pull_model_from_huggingface(container_name: str, model: str) -> str:
    """
    Pull a model from HuggingFace to Ollama.
    Returns the Ollama model name after pulling.
    """
    from solo_server.utils.hf_utils import get_available_models
    
    # Format the model string for Ollama's pull command
    if model.startswith("hf://"):
        model = model.replace("hf://", "")
    elif model.startswith("hf.co/"):
        model = model.replace("hf.co/", "")
    
    # Get HuggingFace token from environment variable or config file
    hf_token = os.getenv('HUGGING_FACE_TOKEN', '')
    if not hf_token:  # If not in env, try config file
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                hf_token = config.get('hugging_face', {}).get('token', '')
    
    # Check if a specific model file is specified or just the repo
    if model.count('/') >= 2:  
        # Specific model file is provided (username/repo/filename.gguf)
        parts = model.split('/')
        repo_id = '/'.join(parts[:-1])  # username/repo
        model_file = parts[-1]  # filename.gguf
        
        # Extract quantization format from filename (e.g., Q4_K_M)
        quant_format = None
        if ".gguf" in model_file.lower():
            # Try to extract quantization format like Q4_K_M
            parts = model_file.lower().split('.')
            if len(parts) > 1:
                # Look for Q4_K_M or similar pattern in the filename
                for part in parts:
                    if part.startswith('q') and '_' in part:
                        quant_format = part.upper()
                        break
        
        # Format for Ollama: hf.co/username/repo:QUANT
        if quant_format:
            hf_model = f"hf.co/{repo_id}:{quant_format}"
        else:
            # If no quantization format found, use the repo ID only
            hf_model = f"hf.co/{repo_id}"
        
        # Use repo name as model name
        model_name = repo_id.split('/')[-1]

    else:  # Format: username/repo
        # Only repo is provided, need to select best model file
        repo_id = model
        
        # Get available GGUF models from the repo
        model_files = get_available_models(repo_id, suffix=".gguf")

        if not model_files:
            typer.echo(f"❌ No GGUF models found in repository {repo_id}", err=True)
            raise typer.Exit(code=1)
        
        # Select the best model based on quantization
        best_model = select_best_model_file(model_files)
        typer.echo(f"Selected model: {best_model}")
        
        # Extract quantization format from filename (e.g., Q4_K_M)
        quant_format = None
        if ".gguf" in best_model.lower():
            # Try to extract quantization format like Q4_K_M
            parts = best_model.lower().split('.')
            if len(parts) > 1:
                # Look for Q4_K_M or similar pattern in the filename
                for part in parts:
                    if part.startswith('q') and '_' in part:
                        quant_format = part.upper()
                        break
        
        # Format for Ollama: hf.co/username/repo:QUANT
        if quant_format:
            hf_model = f"hf.co/{repo_id}:{quant_format}"
        else:
            # If no quantization format found, use the repo ID only
            hf_model = f"hf.co/{repo_id}"
        
        # Use repo name as model name
        model_name = repo_id.split('/')[-1]
    
    typer.echo(f"📥 Pulling model {hf_model} from HuggingFace...")
    
    try:
        subprocess.run(
            ["docker", "exec", container_name, "ollama", "pull", hf_model],
            check=True
        )
        typer.echo(f"✅ Successfully pulled model from HuggingFace")
        return model_name
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to pull model from HuggingFace: {e}", err=True)
        raise e
