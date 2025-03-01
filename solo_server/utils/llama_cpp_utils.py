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

def stop_server_on_port(port: int) -> bool:
    """Stop any server running on the specified port."""
    process = find_process_by_port(port)
    if process:
        try:
            typer.echo(f"Found existing server on port {port} (PID: {process.pid}). Stopping it...")
            process.terminate()
            process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
            if process.is_running():
                process.kill()  # Force kill if still running
            typer.echo(f"Successfully stopped existing server on port {port}")
            time.sleep(1)  # Give the OS time to free up the port
            return True
        except Exception as e:
            typer.echo(f"Error stopping server: {e}", err=True)
            return False
    return True  # No process to stop, so consider it a success

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
            typer.echo(f"Port {port} is already in use.")
            if not stop_server_on_port(port):
                typer.echo(f"❌ Failed to stop existing server on port {port}. Please stop it manually.", err=True)
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
        
        # Start the server as a background process
        typer.echo(f"Using model: {hf_repo_id + '/' + model_pattern if hf_repo_id and not os.path.exists(model_path) else model_path}")
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
            typer.echo(f"Server is running in a new terminal window. The window will stay open.")
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
        typer.echo(f"❌ Failed to start llama.cpp server: {e}", err=True)
        return False