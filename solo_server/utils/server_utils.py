import os 
import json
import typer
import sys
import time
import subprocess

from solo_server.config import CONFIG_PATH
from solo_server.utils.nvidia import is_cuda_toolkit_installed
from solo_server.utils.llama_cpp_utils import is_uv_available, start_llama_cpp_server

def setup_vllm_server(gpu_enabled: bool, cpu: str = None, gpu_vendor: str = None, os_name:str = None, port: int = 8000):
    """Setup vLLM server with Docker"""
    # Initialize container_exists flag
    container_exists = False
    try:
        # Check if container exists (running or stopped)
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", "name=solo-vllm"], 
            capture_output=True, 
            text=True
        ).stdout.strip()

        if container_exists:
            # Check if container is running
            check_cmd = ["docker", "ps", "-q", "-f", "name=solo-vllm"]
            is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
            if is_running:
                typer.echo("✅ vLLM server is already setup!")
                return True
            else:
                remove_container = typer.confirm("vLLM server already exists. Do you want to run with a new model?", default=False)
                if remove_container:
                    subprocess.run(["docker", "rm", "solo-vllm"], check=True, capture_output=True)
                else:
                    subprocess.run(["docker", "start", "solo-vllm"], check=True, capture_output=True)
                    return True
                
        if not container_exists or remove_container:
            # Pull vLLM image
            typer.echo("📥 Pulling vLLM image...")
            cpu = cpu.split()[0] if cpu else ""
            if gpu_vendor == "NVIDIA" and gpu_enabled:
                subprocess.run(["docker", "pull", "vllm/vllm-openai:latest"], check=True)
            elif gpu_vendor == "AMD" and gpu_enabled:
                subprocess.run(["docker", "pull", "rocm/vllm"], check=True)
            elif cpu == "Apple":
                subprocess.run(["docker", "pull", "getsolo/vllm-arm"], check=True)
            elif cpu in ["Intel", "AMD"]:
                subprocess.run(["docker", "pull", "getsolo/vllm-cpu"], check=True)
            else:
                typer.echo("❌ vLLM currently do not support your machine", err=True)
                return False
            
            # Check if port is available
            try:
                subprocess.run(
                    ["docker", "run", "--rm", "-p", f"{port}:8000", "alpine", "true"], 
                    check=True, 
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                typer.echo(f"❌ Port {port} is already in use", err=True)
                return False

            # Get HuggingFace token from environment variable or config file
            typer.echo("\nChecking for HuggingFace token...")
            hf_token = os.getenv('HUGGING_FACE_TOKEN', '')

            if not hf_token:  # If not in env, try config file
                if os.path.exists(CONFIG_PATH):
                    with open(CONFIG_PATH, 'r') as f:
                        config = json.load(f)
                        hf_token = config.get('hugging_face', {}).get('token', '')

            if not hf_token:
                if os_name in ["Linux", "Windows"]:
                    typer.echo("Use Ctrl + Shift + V to paste your token.")
                hf_token = typer.prompt("Please add your HuggingFace token (Recommended)")
                
            # Save token if provided 
            if hf_token:
                if os.path.exists(CONFIG_PATH):
                    with open(CONFIG_PATH, 'r') as f:
                        config = json.load(f)
                else:
                    config = {}
                config['hugging_face'] = {'token': hf_token}
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=4)

            docker_run_cmd = [
                "docker", "run", "-d",
                "--name", "solo-vllm",
                "-v", f"{os.path.expanduser('~')}/.cache/huggingface:/root/.cache/huggingface",
                "--env", f"HUGGING_FACE_HUB_TOKEN={hf_token}",
                "-p", f"{port}:8000",
                "--ipc=host"
            ]

            # Modify command based on GPU vendor
            if gpu_vendor == "NVIDIA" and gpu_enabled:
                docker_run_cmd += ["--gpus", "all"]
                docker_run_cmd.append("vllm/vllm-openai:latest")

                # Check GPU compute capability
                gpu_info = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv"],
                    capture_output=True,
                    text=True
                ).stdout.strip().split('\n')[-1]
                compute_cap = float(gpu_info.split(',')[-1].strip())

            elif gpu_vendor == "AMD" and gpu_enabled:
                docker_run_cmd += [
                    "--network=host",
                    "--group-add=video",
                    "--cap-add=SYS_PTRACE",
                    "--security-opt", "seccomp=unconfined",
                    "--device", "/dev/kfd",
                    "--device", "/dev/dri"
                ]
                docker_run_cmd.append("rocm/vllm")

            elif cpu == "Apple":
                docker_run_cmd.append("getsolo/vllm-arm")

            elif cpu in ["Intel", "AMD"]:
                docker_run_cmd.append("getsolo/vllm-cpu")
            else:
                typer.echo("❌ Solo server vLLM currently do not support your machine", err=True)
                return False
            
            # Ask user for model name
            default_model = "meta-llama/Llama-3.2-1B-Instruct"
            model_name = typer.prompt(f"Enter the model name", default=default_model)
            # Add the model argument and additional parameters
            docker_run_cmd.append("--model")
            docker_run_cmd.append(model_name)
            docker_run_cmd.append("--max_model_len=4096")

            if gpu_vendor == "NVIDIA":
                docker_run_cmd.append("--gpu_memory_utilization=0.95")
                if 5 < compute_cap < 8:
                    docker_run_cmd.append("--dtype=half")
        
            typer.echo("🚀 Starting vLLM server...")
            subprocess.run(docker_run_cmd, check=True, capture_output=True)
            # Check docker logs for any errors
            try:
                logs = subprocess.run(
                    ["docker", "logs", "solo-vllm"],
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
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                subprocess.run(
                    ["docker", "exec", "solo-vllm", "ps", "aux"],
                    check=True,
                    capture_output=True,
                )
                typer.secho(
                    "✅ vLLM server is ready!\n",
                    fg=typer.colors.BRIGHT_CYAN,
                    bold=True
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
            subprocess.run(["docker", "stop", "solo-vllm"], check=False)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        return False

def setup_ollama_server(gpu_enabled: bool = False, gpu_vendor: str = None, port: int = 8000):
    """Setup solo-server Ollama environment."""
    # Initialize container_exists flag
    container_exists = False

    try:
        # Check if container exists (running or stopped)
        container_exists = subprocess.run(
            ["docker", "ps", "-aq", "-f", "name=solo-ollama"], 
            capture_output=True, 
            text=True
        ).stdout.strip()

        if container_exists:
            # Check if container is running
            check_cmd = ["docker", "ps", "-q", "-f", "name=solo-ollama"]
            is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
            if is_running:
                typer.echo("✅ Ollama server is already setup!")
                return True
            else:    
                subprocess.run(["docker", "start", "solo-ollama"], check=True, capture_output=True)
        else:
            # Pull Ollama image
            typer.echo("📥 Pulling Ollama Registry...")
            subprocess.run(["docker", "pull", "ollama/ollama"], check=True)

            # Check if port is available
            try:
                subprocess.run(
                    ["docker", "run", "--rm", "-p", "11434:11434", "alpine", "true"], 
                    check=True, 
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                typer.echo("❌ Port 11434 is already in use", err=True)
                return

            # Start Ollama container
            docker_run_cmd = ["docker", "run", "-d", "--name", "solo-ollama", "-v", "ollama:/root/.ollama", "-p", "11434:11434"]
            if gpu_vendor == "NVIDIA" and gpu_enabled:
                docker_run_cmd += ["--gpus", "all"]
                docker_run_cmd.append("ollama/ollama")
            elif gpu_vendor == "AMD" and gpu_enabled:
                docker_run_cmd += ["--device", "/dev/kfd", "--device", "/dev/dri"]
                docker_run_cmd.append("ollama/ollama:rocm")
            else:
                docker_run_cmd.append("ollama/ollama")

            typer.echo("\n🚀 Starting Ollama Server...")
            subprocess.run(docker_run_cmd, check=True, capture_output=True)

        # Wait for container to be ready with timeout
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                subprocess.run(
                    ["docker", "exec", "solo-ollama", "ollama", "list"],
                    check=True,
                    capture_output=True,
                )
                typer.secho(
                "✅ Ollama server is ready!\n",
                fg=typer.colors.BRIGHT_CYAN,
                bold=True
                )

                return True
            except subprocess.CalledProcessError:
                time.sleep(1)
        
        typer.echo("❌ Solo server failed to start within timeout", err=True)

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Docker command failed: {e}", err=True)
        # Cleanup on failure
        if container_exists:
            subprocess.run(["docker", "stop", "solo-ollama"], check=False)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        return False

def setup_llama_cpp_server(gpu_enabled: bool, gpu_vendor: str = None, os_name: str = None):
    """
    Setup llama_cpp_python server using system config.

    Parameters:
    gpu_enabled (bool): Whether GPU is enabled.
    gpu_vendor (str, optional): The GPU vendor (e.g., NVIDIA, AMD, Apple Silicon).
    os_name (str, optional): The name of the operating system.
    """
     # Check if llama-cpp-python is already installed
    try:
        import llama_cpp
        typer.echo("✅ llama.cpp server is already installed")
        return start_llama_cpp_server(os_name)
    except ImportError:
        typer.echo("Installing llama.cpp server...")

    # Set CMAKE_ARGS based on hardware and OS
    cmake_args = []
    if gpu_enabled:
        if gpu_vendor == "NVIDIA":
            if not is_cuda_toolkit_installed():
                typer.echo("❌ NVIDIA CUDA Toolkit is not installed. Please install it to proceed with GPU acceleration.", err=True)
                typer.secho("Install Here: https://developer.nvidia.com/cuda-downloads", fg=typer.colors.GREEN)
                return False
            cmake_args.append("-DGGML_CUDA=on")
        elif gpu_vendor == "AMD":
            cmake_args.append("-DGGML_HIPBLAS=on")
        elif gpu_vendor == "Apple Silicon":
            cmake_args.append("-DGGML_METAL=on")
  
    cmake_args_str = " ".join(cmake_args)

    try:
        env = os.environ.copy()
        env["CMAKE_ARGS"] = cmake_args_str
        # Install llama-cpp-python using the Python interpreter
        if is_uv_available():
            use_uv = typer.confirm("uv is available. Are you using (uv's) virtual env for installation?", default=True)
            if use_uv:
                installer_cmd = ["uv", "pip", "install", "--no-cache-dir", "llama-cpp-python[server]"]
            else:
                installer_cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "llama-cpp-python[server]"]
        else:
            installer_cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "llama-cpp-python[server]"]

        subprocess.check_call(installer_cmd, env=env)
        try:
            if start_llama_cpp_server(os_name):
                typer.echo("\n ✅ llama.cpp server is ready!")
                return True
        except Exception as e:
            typer.echo(f"❌ Failed to start llama.cpp server: {e}", err=True)
            return False

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to setup llama.cpp server: {e}", err=True)
        return False
