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
from solo_server.utils.hardware import is_ollama_natively_installed, check_ollama_service_status

def start_ui(server_type: str, container_name: str = None) -> bool:
    """
    Start the UI Docker container and connect it to the model server.
    
    Args:
        server_type (str): The server type (ollama, vllm, llama.cpp)
        container_name (str, optional): The name of the server container
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Define the UI container name
        ui_container_name = "solo-ui"
        ui_port = 9000
        
        # Check if the UI container already exists
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={ui_container_name}"], 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        # Stop and remove existing container if it's running
        if container_exists:
            subprocess.run(["docker", "stop", ui_container_name], check=False, capture_output=True)
            subprocess.run(["docker", "rm", ui_container_name], check=False, capture_output=True)
        
        # Check if port is available
        if is_port_in_use(ui_port):
            typer.echo(f"⚠️ Port {ui_port} is already in use.", err=True)
            return False

        # Get server port from config for connecting to the server
        server_port = None
        if server_type == 'ollama':
            server_config = get_server_config('ollama')
            # Check if using native Ollama
            use_native = False
            try:
                if os.path.exists(CONFIG_PATH):
                    with open(CONFIG_PATH, 'r') as f:
                        config_data = json.load(f)
                        use_native = config_data.get('environment', {}).get('ollama_native', False)
            except:
                pass
            
            # Check if native Ollama is available and running
            if (use_native or is_ollama_natively_installed()) and check_ollama_service_status():
                server_port = server_config.get('native_port', 11434)  # Use native Ollama port
            else:
                server_port = server_config.get('default_port', 11434)  # Use Docker port
        elif server_type == 'vllm':
            server_config = get_server_config('vllm')
            server_port = server_config.get('default_port', 8000)
        elif server_type == 'llama.cpp':
            server_config = get_server_config('llama_cpp')
            server_port = server_config.get('default_port', 8080)

        # Read config.json to get active model information
        config_path = os.path.expanduser("~/.solo_server/config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            active_model = config.get('active_model', {})
            # Use the port specified in active_model if available
            if active_model and 'port' in active_model:
                server_port = active_model.get('port')
                
        typer.echo(f"Using server port: {server_port}")

        # Check if solo-network exists, create if not
        network_exists = subprocess.run(
            ["docker", "network", "inspect", "solo-network"],
            capture_output=True,
            text=True
        ).returncode == 0
        
        if not network_exists:
            subprocess.run(["docker", "network", "create", "solo-network"], check=True, capture_output=True)
            typer.echo("Created docker network: solo-network")
        
        # Connect the server container to the solo-network if it exists and container name is provided
        if container_name and server_type != 'llama.cpp':
            try:
                # Check if container is connected to network
                network_connected = subprocess.run(
                    ["docker", "network", "inspect", "solo-network", "-f", f"{{{{.Containers}}}}"],
                    capture_output=True, 
                    text=True
                ).stdout
                
                # If not connected, connect it
                if container_name not in network_connected:
                    subprocess.run(
                        ["docker", "network", "connect", "solo-network", container_name], 
                        capture_output=True,
                        text=True
                    )
                    typer.echo(f"Connected Solo server to Solo UI")
            except Exception as e:
                # If connecting fails, we can still try to run the UI
                typer.echo(f"Note: Could not connect server to network: {e}")
        
        # Check if aiaio image exists locally
        image_exists = subprocess.run(
            ["docker", "images", "-q", "getsolo/aiaio"], 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        # If image doesn't exist locally, pull it
        if not image_exists:
            typer.echo("Setting up...")
            try:
                # Try to pull the image from Docker Hub
                subprocess.run(
                    ["docker", "pull", "getsolo/aiaio:latest"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                typer.echo("Failed to pull from Docker Hub, checking if image exists locally")
                image_exists = subprocess.run(
                    ["docker", "images", "-q", "getsolo/aiaio:latest"], 
                    capture_output=True, 
                    text=True
                ).stdout.strip()
                
                if not image_exists:
                    typer.echo(f"❌ Failed to find UI image", err=True)
                    return False
        
        # Start the AIAIO UI container
        run_cmd = [
            "docker", "run", "-d",
            "--name", ui_container_name,
            "-p", f"{ui_port}:9000",  # Map external port to container's internal port
            "--network", "solo-network",
            "-v", f"{os.path.expanduser('~')}/.solo_server:/root/.solo_server"
        ]
        
        # For llama.cpp which runs on the host, we need to add extra_hosts setting
        # to allow the container to access the host's IP
        if server_type == 'llama.cpp':
            run_cmd.extend(["--add-host", "host.docker.internal:host-gateway"])
        
        # Add environment variables for server configuration
        run_cmd.extend([
            "-e", f"SOLO_SERVER_TYPE={server_type}",
            "-e", f"SOLO_SERVER_PORT={server_port}"
        ])
        
        # Add the image name (try both aiaio:latest and aiaio/latest)
        if image_exists:
            run_cmd.append("getsolo/aiaio:latest") 
        else:
            run_cmd.append("getsolo/aiaio:latest")
        
        result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            typer.echo(f"❌ Failed to start UI: {result.stderr}", err=True)
            return False
        
        # Wait briefly to ensure container is running
        time.sleep(2)
        
        # Check if container is running
        is_running = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={ui_container_name}"],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if not is_running:
            typer.echo("❌ UI container failed to start", err=True)
            return False
            
        return True
    
    except Exception as e:
        typer.echo(f"❌ Error starting UI: {e}", err=True)
        return False

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
    
    # Check if native Ollama is installed and configured
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                use_native = config.get('environment', {}).get('ollama_native', False)
        else:
            use_native = False
    except:
        use_native = False
    
    # If native Ollama is configured, use it
    if use_native and is_ollama_natively_installed() and check_ollama_service_status():
        return True  # Native Ollama is already running
    
    # Fall back to Docker approach
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
            log_dir = os.path.join(os.path.expanduser("~"), ".solo_server", "logs")
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
                escaped_cmd = " ".join(server_cmd).replace('"', '\\"')
                script = f'tell app "Terminal" to do script "{escaped_cmd} ; echo \\\"\\\\nServer is running. Press Ctrl+C to stop.\\\"; bash"'
                typer.echo(f"Debug: Executing AppleScript with command: {escaped_cmd}")
                terminal_cmd = ["osascript", "-e", script]
                try:
                    result = subprocess.Popen(terminal_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = result.communicate(timeout=5)
                    if stderr:
                        typer.echo(f"Debug: AppleScript stderr: {stderr.decode('utf-8')}")
                    typer.echo("Server is running in a new Terminal window")
                except Exception as e:
                    typer.echo(f"Warning: Issue launching Terminal: {e}")
                    # Fallback to background process
                    typer.echo("Falling back to background process...")
                    process = subprocess.Popen(
                        server_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True
                    )
                    typer.echo(f"Server is running in the background. Process ID: {process.pid}")
                    return True
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

def check_ollama_model_exists(container_name: str, model: str) -> tuple[bool, str]:
    """
    Check if a model exists in Ollama.
    
    Args:
        container_name (str): The name of the Ollama container
        model (str): The model name to check
        
    Returns:
        tuple[bool, str]: A tuple containing (exists, model_name)
            - exists (bool): True if the model exists, False otherwise
            - model_name (str): The full model name with tag if it exists, otherwise the original model name
    """
    try:
        # Get the list of models from Ollama
        model_exists = subprocess.run(
            ["docker", "exec", container_name, "ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        
        # Check if the model has a tag
        has_tag = ':' in model
        if has_tag:
            # If the model has a tag, check for exact match
            if model in model_exists:
                return True, model
        else:
            # If the model doesn't have a tag, check for the model with :latest tag
            model_with_latest = f"{model}:latest"
            if model_with_latest in model_exists:
                return True, model_with_latest
                    
        # Model not found
        return False, model
    except subprocess.CalledProcessError:
        # Error running the command
        return False, model

def pull_ollama_model(container_name: str, model: str) -> str:
    """
    Pull a model from Ollama.
    
    Args:
        container_name (str): The name of the Ollama container
        model (str): The model name to pull
        
    Returns:
        str: The model name after pulling (may include tag)
        
    Raises:
        typer.Exit: If the model could not be pulled
    """
    # First check if the model exists with a different tag
    model_exists, existing_model = check_ollama_model_exists(container_name, model)
    if model_exists:
        typer.echo(f"✅ Model {existing_model} already exists")
        return existing_model
    
    # Check if model already has a tag
    has_tag = ':' in model
    if has_tag:
        # If the model has a tag, try to pull that exact model
        typer.echo(f"📥 Pulling model {model}...")
        try:
            # Run the pull command 
            process = subprocess.Popen(
                ["docker", "exec", container_name, "ollama", "pull", model],
                stdout=None,  # Use None to show output in real-time
                stderr=None,  # Use None to show errors in real-time
                text=True
            )
            # Wait for the process to complete
            process.wait()
            
            if process.returncode != 0:
                typer.echo(f"❌ Failed to pull model {model}", err=True)
                raise typer.Exit(code=1)
                
            typer.echo(f"✅ Model {model} pulled successfully")
            # Return the model name with tag
            return model
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model {model}: {e}", err=True)
            raise typer.Exit(code=1)
    else:
        # If the model doesn't have a tag, try to pull with :latest tag first
        model_with_tag = f"{model}:latest"
        typer.echo(f"📥 Pulling model {model_with_tag}...")
        try:
            # Run the pull command 
            process = subprocess.Popen(
                ["docker", "exec", container_name, "ollama", "pull", model_with_tag],
                stdout=None,  # Use None to show output in real-time
                stderr=None,  # Use None to show errors in real-time
                text=True
            )
            # Wait for the process to complete
            process.wait()
            
            if process.returncode != 0:
                typer.echo(f"❌ Failed to pull model {model_with_tag}", err=True)
                # Try without the tag as a fallback
                typer.echo(f"Trying to pull model {model} without tag...")
                process = subprocess.Popen(
                    ["docker", "exec", container_name, "ollama", "pull", model],
                    stdout=None,  # Use None to show output in real-time
                    stderr=None,  # Use None to show errors in real-time
                    text=True
                )
                # Wait for the process to complete
                process.wait()
                
                if process.returncode != 0:
                    typer.echo(f"❌ Failed to pull model {model}", err=True)
                    raise typer.Exit(code=1)
                    
                typer.echo(f"✅ Model {model} pulled successfully")
                return model
            else:
                typer.echo(f"✅ Model {model_with_tag} pulled successfully")
                # Return the model name with tag
                return model_with_tag
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model {model_with_tag}: {e}", err=True)
            raise typer.Exit(code=1)

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

def start_native_ollama_server(port: int = None) -> bool:
    """
    Start native Ollama server if not already running.
    
    Args:
        port (int, optional): Port to run the server on
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Load Ollama configuration from YAML
    ollama_config = get_server_config('ollama')
    timeout_config = get_timeout_config()
    
    # Use native port from config if not provided
    port = port or ollama_config.get('native_port', 11434)
    
    try:
        # Check if Ollama is natively installed
        if not is_ollama_natively_installed():
            typer.echo("❌ Native Ollama is not installed.", err=True)
            return False
        
        # Check if Ollama service is already running
        if check_ollama_service_status():
            typer.echo("✅ Ollama service is already running.")
            return True
        
        # Check if port is available
        if is_port_in_use(port):
            typer.echo(f"❌ Port {port} is already in use, please try a different port", err=True)
            typer.echo(f"Run 'solo stop' to stop all running servers.")
            return False
        
        # Start Ollama service
        typer.echo("🚀 Starting native Ollama service...")
        
        # Start Ollama in background
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        # Wait for service to be ready with timeout
        server_timeout = timeout_config.get('server_start', 30)
        start_time = time.time()
        while time.time() - start_time < server_timeout:
            if check_ollama_service_status():
                typer.echo("✅ Native Ollama service started successfully.")
                return True
            time.sleep(1)
        
        typer.echo("❌ Native Ollama service failed to start within timeout", err=True)
        return False
        
    except Exception as e:
        typer.echo(f"❌ Failed to start native Ollama service: {e}", err=True)
        return False

def check_native_ollama_model_exists(model: str) -> tuple[bool, str]:
    """
    Check if a model exists in native Ollama.
    
    Args:
        model (str): The model name to check
        
    Returns:
        tuple[bool, str]: A tuple containing (exists, model_name)
            - exists (bool): True if the model exists, False otherwise
            - model_name (str): The full model name with tag if it exists, otherwise the original model name
    """
    try:
        # Get the list of models from Ollama
        model_exists = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        
        # Check if the model has a tag
        has_tag = ':' in model
        if has_tag:
            # If the model has a tag, check for exact match
            if model in model_exists:
                return True, model
        else:
            # If the model doesn't have a tag, check for the model with :latest tag
            model_with_latest = f"{model}:latest"
            if model_with_latest in model_exists:
                return True, model_with_latest
                    
        # Model not found
        return False, model
    except subprocess.CalledProcessError:
        # Error running the command
        return False, model

def pull_native_ollama_model(model: str) -> str:
    """
    Pull a model using native Ollama.
    
    Args:
        model (str): The model name to pull
        
    Returns:
        str: The model name after pulling (may include tag)
        
    Raises:
        typer.Exit: If the model could not be pulled
    """
    # First check if the model exists with a different tag
    model_exists, existing_model = check_native_ollama_model_exists(model)
    if model_exists:
        typer.echo(f"✅ Model {existing_model} already exists")
        return existing_model
    
    # Check if model already has a tag
    has_tag = ':' in model
    if has_tag:
        # If the model has a tag, try to pull that exact model
        typer.echo(f"📥 Pulling model {model}...")
        try:
            # Run the pull command 
            process = subprocess.Popen(
                ["ollama", "pull", model],
                stdout=None,  # Use None to show output in real-time
                stderr=None,  # Use None to show errors in real-time
                text=True
            )
            # Wait for the process to complete
            process.wait()
            
            if process.returncode != 0:
                typer.echo(f"❌ Failed to pull model {model}", err=True)
                raise typer.Exit(code=1)
                
            typer.echo(f"✅ Model {model} pulled successfully")
            # Return the model name with tag
            return model
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model {model}: {e}", err=True)
            raise typer.Exit(code=1)
    else:
        # If the model doesn't have a tag, try to pull with :latest tag first
        model_with_tag = f"{model}:latest"
        typer.echo(f"📥 Pulling model {model_with_tag}...")
        try:
            # Run the pull command 
            process = subprocess.Popen(
                ["ollama", "pull", model_with_tag],
                stdout=None,  # Use None to show output in real-time
                stderr=None,  # Use None to show errors in real-time
                text=True
            )
            # Wait for the process to complete
            process.wait()
            
            if process.returncode != 0:
                typer.echo(f"❌ Failed to pull model {model_with_tag}", err=True)
                # Try without the tag as a fallback
                typer.echo(f"Trying to pull model {model} without tag...")
                process = subprocess.Popen(
                    ["ollama", "pull", model],
                    stdout=None,  # Use None to show output in real-time
                    stderr=None,  # Use None to show errors in real-time
                    text=True
                )
                # Wait for the process to complete
                process.wait()
                
                if process.returncode != 0:
                    typer.echo(f"❌ Failed to pull model {model}", err=True)
                    raise typer.Exit(code=1)
                    
                typer.echo(f"✅ Model {model} pulled successfully")
                return model
            else:
                typer.echo(f"✅ Model {model_with_tag} pulled successfully")
                # Return the model name with tag
                return model_with_tag
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model {model_with_tag}: {e}", err=True)
            raise typer.Exit(code=1)

def pull_native_model_from_huggingface(model: str) -> str:
    """
    Pull a model from HuggingFace using native Ollama.
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
            ["ollama", "pull", hf_model],
            check=True
        )
        typer.echo(f"✅ Successfully pulled model from HuggingFace")
        return model_name
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to pull model from HuggingFace: {e}", err=True)
        raise e
