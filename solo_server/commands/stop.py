import typer
import subprocess
import socket
import psutil
from rich.console import Console
import time
import os
import signal

from solo_server.utils.llama_cpp_utils import find_process_by_port
from solo_server.config.config_loader import get_server_config

console = Console()

def stop(name: str = typer.Option("", help="Server type to stop (e.g., 'ollama', 'vllm', 'llama.cpp')")):
    """
    Stops Solo Server services. If a server type is specified (e.g., 'ollama', 'vllm', 'llama.cpp'),
    only that specific service will be stopped. Otherwise, all Solo services will be stopped.
    """
    typer.echo("\n🔍 Checking running Solo servers...")
    
    # Track what we found and stopped
    found_services = []
    stopped_services = []
    
    # Check for Docker-based services (ollama, vllm)
    try:
        # Check if docker is running
        docker_running = False
        try:
            subprocess.run(["docker", "info"], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            docker_running = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        if docker_running:
            # Check for running solo containers
            containers = []
            container_result = subprocess.run(
                ["docker", "ps", "-f", "name=solo*", "--format", "{{.Names}}"],
                check=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            if container_result:
                containers = container_result.split('\n')
                for container in containers:
                    if "vllm" in container:
                        found_services.append({"type": "vLLM", "id": container})
                    elif "ollama" in container:
                        found_services.append({"type": "Ollama", "id": container})
                    else:
                        found_services.append({"type": "Unknown Docker container", "id": container})
    except Exception as e:
        typer.echo(f"⚠️  Error checking Docker containers: {e}", err=True)
    
    # Check for llama.cpp process running on port 5070 (or other ports)
    default_ports = [5070]  # Add other ports if needed
    
    for port in default_ports:
        try:
            # Check if port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:  # Port is in use
                    process = find_process_by_port(port)
                    if process:
                        cmd_line = " ".join(process.cmdline()) if hasattr(process, 'cmdline') else ""
                        # Check if this is a llama.cpp server
                        if "llama_cpp.server" in cmd_line:
                            found_services.append({"type": "llama.cpp", "id": process.pid, "process": process})
        except Exception as e:
            pass
    
    # Display what was found
    if found_services:
        typer.echo(f"Found {len(found_services)} running Solo services:")
        for service in found_services:
            if service["type"] == "llama.cpp":
                typer.echo(f"  • {service['type']} (PID: {service['id']})")
            else:
                typer.echo(f"  • {service['type']} container: {service['id']}")
        
        typer.echo("\n🛑 Stopping Solo Server...")
        
        # Filter services based on name if provided
        services_to_stop = []
        if name:
            name = name.lower()
            for service in found_services:
                if (name == "llama.cpp" and service["type"] == "llama.cpp") or \
                   (name == "vllm" and service["type"] == "vLLM") or \
                   (name == "ollama" and service["type"] == "Ollama") or \
                   (name in service["id"].lower()):
                    services_to_stop.append(service)
            
            if not services_to_stop:
                typer.echo(f"❌ No running {name} services found.")
                return
        else:
            services_to_stop = found_services
        
        # Stop services
        for service in services_to_stop:
            try:
                if service["type"] == "llama.cpp":
                    # Stop the process
                    process = service["process"]
                    process.terminate()
                    # Wait briefly to see if it terminates gracefully
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        # Force kill if it didn't terminate gracefully
                        process.kill()
                    
                    typer.echo(f"✅ Stopped {service['type']} (PID: {service['id']})")
                    stopped_services.append(service)
                else:
                    # Docker container
                    subprocess.run(
                        ["docker", "stop", service["id"]],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    typer.echo(f"✅ Stopped {service['type']} container: {service['id']}")
                    stopped_services.append(service)
            except Exception as e:
                typer.echo(f"❌ Failed to stop {service['type']}: {e}", err=True)
        
        # Summarize what was stopped
        if stopped_services:
            total_stopped = len(stopped_services)
            typer.echo(f"✅ Successfully stopped {total_stopped} Solo service{'s' if total_stopped > 1 else ''}.")
        else:
            typer.echo("\n⚠️  No services were stopped due to errors.")
    else:
        typer.echo("✅ No running Solo Server found.")
