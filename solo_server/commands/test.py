import typer
import json
import os
import requests
import time
from enum import Enum
from typing import Optional
from solo_server.config import CONFIG_PATH
from solo_server.config.config_loader import get_server_config

class ServerType(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    LLAMACPP = "llama.cpp"

def test(
    timeout: Optional[int] = typer.Option(None, "--timeout", "-t", help="Request timeout in seconds. Default is 30s for vLLM/Llama.cpp and 120s for Ollama.")
):
    """
    Test if the Solo server is running correctly.
    Performs an inference test to verify server functionality.
    """
    typer.echo("Testing Solo server connection...")
    
    # Check if config file exists
    if not os.path.exists(CONFIG_PATH):
        typer.echo("❌ Configuration file not found. Please run 'solo setup' first.", err=True)
        return False
    
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Get active model information
    active_model = config.get('active_model', {})
    server_type = active_model.get('server')
    model_name = active_model.get('name')
    full_model_name = active_model.get('full_model_name')  # Get the full model name if available
    
    # If no active model is set, use the default server type
    if not server_type:
        server_type = config.get('server', {}).get('type', ServerType.OLLAMA.value)
        typer.echo(f"No active model found, using default server type: {server_type}")
    
    # Get server configurations
    vllm_config = get_server_config('vllm')
    ollama_config = get_server_config('ollama')
    llama_cpp_config = get_server_config('llama_cpp')
    
    # Get port for the given server type
    port = None
    if server_type == ServerType.VLLM.value:
        port = vllm_config.get('default_port', 5070)
    elif server_type == ServerType.OLLAMA.value:
        port = ollama_config.get('default_port', 5070)
    elif server_type == ServerType.LLAMACPP.value:
        port = llama_cpp_config.get('default_port', 5070)
    else:
        typer.echo(f"❌ Unknown server type: {server_type}", err=True)
        return False
    
    # Create base URL
    base_url = f"http://localhost:{port}"
    
    # Test connection with an actual inference request
    typer.echo(f"Checking server at {base_url}...")
    
    # Simple test prompt
    test_prompt = "What is machine learning? Keep it very brief."
    
    try:
        # Different API endpoints and payload formats for each server type
        if server_type == ServerType.VLLM.value or server_type == ServerType.LLAMACPP.value:
            # Use OpenAI-compatible chat completion API
            endpoint = f"{base_url}/v1/chat/completions"
            # For vLLM, use the full model name when available
            api_model_name = full_model_name if full_model_name and server_type == ServerType.VLLM.value else model_name
            payload = {
                "model": api_model_name if api_model_name else "default",
                "messages": [
                    {"role": "user", "content": test_prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.7
            }
            # Use default timeout for these servers
            request_timeout = 30
        elif server_type == ServerType.OLLAMA.value:
            # Use Ollama generate API
            endpoint = f"{base_url}/api/generate"
            payload = {
                "model": model_name if model_name else "default",
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 50
                }
            }
            # Increase timeout for Ollama server as it may take longer to respond
            request_timeout = 120
        
        # Use command line timeout if provided
        if timeout is not None:
            request_timeout = timeout
        
        # Indicate test is in progress
        with typer.progressbar(length=100, label="Testing inference") as progress:
            # Update progress to 30%
            for _ in range(30):
                progress.update(1)
                time.sleep(0.01)
            
            # Make the API request
            start_time = time.time()
            response = requests.post(endpoint, json=payload, timeout=request_timeout)
            inference_time = time.time() - start_time
            
            # Update progress to 100%
            for _ in range(70):
                progress.update(1)
                time.sleep(0.01)
        
        # Process response
        if response.status_code == 200:
            try:
                response_json = response.json()
                
                # Extract generated text based on server type
                generated_text = ""
                if server_type == ServerType.VLLM.value or server_type == ServerType.LLAMACPP.value:
                    if "choices" in response_json and len(response_json["choices"]) > 0:
                        if "message" in response_json["choices"][0]:
                            generated_text = response_json["choices"][0]["message"].get("content", "")
                elif server_type == ServerType.OLLAMA.value:
                    # Ollama can return different response formats
                    if "response" in response_json:
                        generated_text = response_json.get("response", "")
                    elif "message" in response_json:
                        # Some versions might use this format
                        generated_text = response_json.get("message", {}).get("content", "")
                    elif "content" in response_json:
                        # Fallback for other possible formats
                        generated_text = response_json.get("content", "")
                
                # Display results
                typer.secho("✅ Server is running and responded to inference request", fg=typer.colors.BRIGHT_GREEN, bold=True)
                
                # Print server details
                typer.secho(f"Server - {server_type.capitalize()}", fg=typer.colors.BRIGHT_BLUE)
                if model_name:
                    typer.secho(f"Model  - {model_name}", fg=typer.colors.BRIGHT_BLUE)
                typer.secho(f"URL    - {base_url}", fg=typer.colors.BRIGHT_CYAN)
                typer.secho(f"Inference time: {inference_time:.2f} seconds", fg=typer.colors.BRIGHT_CYAN)
                
                # Print generated text
                if generated_text:
                    typer.echo("\nTest prompt: " + test_prompt)
                    typer.echo("Response:")
                    typer.secho(generated_text.strip(), fg=typer.colors.WHITE)
                else:
                    typer.echo("\nServer responded but no generated text was found in the response.")
                
                return True
            except Exception as e:
                typer.secho(f"✅ Server is running but response parsing failed: {str(e)}", fg=typer.colors.BRIGHT_YELLOW, err=True)
                typer.echo(f"Raw response: {response.text[:200]}...")
                return True
        else:
            typer.secho(f"❌ Server returned status code {response.status_code}", fg=typer.colors.BRIGHT_RED, err=True)
            try:
                error_msg = response.json()
                typer.echo(f"Error: {json.dumps(error_msg, indent=2)}")
            except:
                typer.echo(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        typer.secho("❌ Failed to connect to server. Server is not running.", fg=typer.colors.BRIGHT_RED, err=True)
        typer.echo("Start the server using 'solo serve' command or wait for the server to start automatically.")
        return False
    except requests.exceptions.Timeout:
        typer.secho("❌ Inference request timed out. The server might be overloaded or the model is too large.", fg=typer.colors.BRIGHT_RED, err=True)
        typer.echo(f"Try running 'solo test --timeout 240' to increase the timeout or use a smaller model.")
        return False
    except Exception as e:
        typer.secho(f"❌ Error testing server: {str(e)}", fg=typer.colors.BRIGHT_RED, err=True)
        return False
