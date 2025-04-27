import os
import sys
import json
import time
import typer
import shutil
import subprocess
import socket
import psutil

from solo_server.config import CONFIG_PATH
from solo_server.utils.nvidia import is_cuda_toolkit_installed
from solo_server.config.config_loader import get_server_config
from solo_server.utils.hf_utils import get_available_models, select_best_model_file

def is_uv_available():
    return shutil.which("uv") is not None

def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_process_by_port(port: int):
    """Find a process using the specified port."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None
# No process to stop, so consider it a success

def preprocess_model_path(model_path: str, hf_token: str = None) -> tuple[str, str]:
    """
    Preprocess the model path to determine if it's a repo ID or direct GGUF path.
    Returns tuple of (hf_repo_id, model_pattern).
    """
    if model_path.endswith('.gguf'):
        # Direct GGUF file path
        parts = model_path.split('/')
        repo_id = '/'.join(parts[:-1]) if '/' in model_path else None
        return repo_id, parts[-1] if parts else model_path
    else:
        os.environ['HUGGING_FACE_TOKEN'] = hf_token
        model_files = get_available_models(model_path, suffix=".gguf")
        if model_files:
                # Auto-select best model if there are multiple
                best_model = select_best_model_file(model_files)
        # Repo ID format - auto-append quantization pattern
        return model_path, best_model

def is_llama_cpp_installed():
    """Check if llama_cpp is installed."""
    try:
        import importlib.util
        return importlib.util.find_spec("llama_cpp") is not None
    except ImportError:
        return False

def setup_llama_cpp_server(gpu_enabled: bool, gpu_vendor: str = None, os_name: str = None, use_uv: bool = False):
    """
    Setup llama_cpp_python server using system config.

    Parameters:
    gpu_enabled (bool): Whether GPU is enabled.
    gpu_vendor (str, optional): The GPU vendor (e.g., NVIDIA, AMD, Apple Silicon).
    os_name (str, optional): The name of the operating system.
    install_only (bool, optional): If True, only install the library without starting the server.
    using_uv (bool, optional): If provided, skips the uv confirmation prompt and uses this value.
    """
    # Load llama.cpp configuration from YAML
    llama_cpp_config = get_server_config('llama_cpp')
    # Set CMAKE_ARGS based on hardware and OS
    cmake_args = []
    use_gpu_build = False
    
    if gpu_enabled:
        if gpu_vendor == "NVIDIA":
            if is_cuda_toolkit_installed():
                use_gpu_build = True
                cmake_args.append(llama_cpp_config.get('cmake_args', {}).get('nvidia', "-DGGML_CUDA=on"))
            else:
                typer.echo("⚠️ NVIDIA CUDA Toolkit not properly configured. Will try CPU-only build instead.", err=True)
        elif gpu_vendor == "AMD":
            use_gpu_build = True
            cmake_args.append(llama_cpp_config.get('cmake_args', {}).get('amd', "-DGGML_HIPBLAS=on"))
        elif gpu_vendor == "Apple Silicon":
            use_gpu_build = True
            cmake_args.append(llama_cpp_config.get('cmake_args', {}).get('apple_silicon', "-DGGML_METAL=on"))
  
    cmake_args_str = " ".join(cmake_args)

    try:
        env = os.environ.copy()
        if use_gpu_build:
            env["CMAKE_ARGS"] = cmake_args_str
            typer.echo(f"Attempting GPU-accelerated build with: {cmake_args_str}")
        else:
            typer.echo("Installing CPU-only version of llama-cpp-python")
        
        typer.echo(f"Using {'uv' if use_uv else 'pip'} as package manager")
        # Install llama-cpp-python using the Python interpreter
        if use_uv:
            installer_cmd = ["uv", "pip", "install", "--no-cache-dir", "llama-cpp-python[server]"]
        else:
            installer_cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "llama-cpp-python[server]"]

        try:
            subprocess.check_call(installer_cmd, env=env)
        except subprocess.CalledProcessError as e:
            if use_gpu_build:
                typer.echo("❌ GPU-accelerated build failed. Falling back to CPU-only build...", err=True)
                # Clear CMAKE_ARGS for CPU-only build
                env.pop("CMAKE_ARGS", None)
                subprocess.check_call(installer_cmd, env=env)
            else:
                raise e
    except Exception as e:
        typer.echo(f"❌ Failed to install package: {e}", err=True)
        return False
    return True
            