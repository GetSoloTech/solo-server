import time
import subprocess
import socket
import typer
import click
import yaml
from pathlib import Path
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich import box

app = typer.Typer(help="Solo Server Setup CLI\nA polished CLI for hardware detection, model initialization, and advanced module loading.")

# Google-inspired theme
google_theme = Theme({
    "header": "bold #4285F4",
    "info": "bold #4285F4",
    "warning": "bold #DB4437",
    "success": "bold #0F9D58",
    "panel.border": "bright_blue",
    "panel.title": "bold white"
})
console = Console(theme=google_theme)

# Hard-coded model and starting port
MODEL = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
START_PORT = 5070

def print_banner():
    """Display a header banner for the Solo Server CLI."""
    banner_text = """
    ___  _             __      __  _ 
   / _ \(_)___  ___   / /___  / /_(_)
  / , _/ / _ \/ -_) / / __/ / __/ / 
 /_/|_/_/ .__/\__/ /_/\__/  \__/_/  
       /_/                         
    """
    console.print(Panel(banner_text, style="header", border_style="panel.border", title="SOLO SERVER INIT", box=box.DOUBLE))

def detect_hardware():
    """
    Dummy hardware detection function.
    Replace with your actual hardware detection logic.
    """
    cpu_model = "Intel i7"
    cpu_cores = 8
    memory_gb = 16  # Example value
    gpu_memory = 4  # Example value (in GB)
    return cpu_model, cpu_cores, memory_gb, gpu_memory

def get_hardware_category(memory_gb: float) -> str:
    if memory_gb < 8:
        return "Fresh Adopter"
    elif memory_gb < 16:
        return "Mid Range"
    elif memory_gb < 32:
        return "High Performance"
    else:
        return "Maestro"

def simulate_model_download(model: str, sleep_time: int = 3) -> str:
    """
    Simulate model download with a progress bar.
    (sleep_time is in seconds; e.g., 3 sec ~ 0.05 mins)
    """
    for _ in tqdm(range(sleep_time), desc="Downloading model (est. {:.2f} mins)".format(sleep_time/60), unit="sec", total=sleep_time):
        time.sleep(1)
    return f"[success]Model {model} download complete.[/success]"

def prompt_core_initialization(confirm_fn=typer.confirm) -> bool:
    """
    Ask user to confirm core initialization.
    """
    init_prompt = (
        "Continue to solo core initialization?\n"
        "Yes: Proceed with full initialization and model setup\n"
        "No:  Exit setup"
    )
    console.print(Panel(init_prompt, title="Core Initialization", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    return confirm_fn("", default=True)

def test_downloaded_model(model: str, run_subprocess_fn=subprocess.run) -> str:
    """
    Prompt the user for a test prompt (defaulting to 'solo @@ test') and use the LitGPT CLI
    to generate sample output from the downloaded model.
    A progress bar shows the testing duration.
    """
    test_prompt = typer.prompt("Enter test prompt", default="solo @@ test")
    console.print(f"[info]Testing model {model} with prompt: '{test_prompt}'[/info]")
    for _ in tqdm(range(5), desc="Testing model (est. 0.08 mins)", unit="sec", total=5):
        time.sleep(1)
    try:
        # Assuming the LitGPT CLI provides a generate command.
        cmd = ["litgpt", "generate", model, "--prompt", test_prompt]
        result = run_subprocess_fn(cmd, check=True, capture_output=True, text=True)
        output = result.stdout.strip()
        console.print(f"[success]Test generation output:[/success]\n{output}")
        return output
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() if e.stderr else str(e)
        console.print(f"[warning]Test generation failed: {error_output}[/warning]")
        return ""

def prompt_advanced_modules(confirm_fn=typer.confirm, prompt_fn=typer.prompt) -> (bool, str):
    """
    Ask user if they want to load advanced modules and select a vertical.
    New verticals include: secure enterprise, healthcare, robotics, and lean ensemble.
    Returns a tuple (advanced_modules, module_pack)
    """
    adv_prompt = (
        "Load advanced modules?\n"
        "Yes: Load additional functionalities for a vertical\n"
        "No:  Skip advanced modules"
    )
    console.print(Panel(adv_prompt, title="Advanced Modules", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    advanced_modules = confirm_fn("", default=True)
    module_pack = None
    if advanced_modules:
        module_pack_info = (
            "Choose advanced vertical:\n"
            "secure enterprise - Modules for security and compliance\n"
            "healthcare        - Modules for healthcare applications\n"
            "robotics          - Modules for robotics integration\n"
            "lean ensemble     - A lean set of general modules\n"
            "Enter your choice:"
        )
        console.print(Panel(module_pack_info, title="Vertical Options", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
        module_pack = prompt_fn("", type=click.Choice(["secure enterprise", "healthcare", "robotics", "lean ensemble"], case_sensitive=False), default="lean ensemble")
    return advanced_modules, module_pack

def build_docker_ensemble(module_pack: str, run_subprocess_fn=subprocess.run):
    """
    Build an ensemble of Docker images for the selected vertical.
    Uses the path: commands/containers/<module> (relative to main.py).
    A tqdm progress bar shows the estimated duration.
    """
    # New advanced module packs for different verticals
    advanced_module_packs = {
        "secure enterprise": ["auth", "data-encryption", "audit-log"],
        "healthcare": ["hl7", "fhir-connector", "secure-patient"],
        "robotics": ["ros", "le-robot", "robotics-core"],
        "lean ensemble": ["microservice", "edge-ai", "light-transformers"]
    }
    modules = advanced_module_packs.get(module_pack.lower(), [])
    if not modules:
        console.print(f"[warning]No modules found for vertical '{module_pack}'.[/warning]")
        return

    for module in tqdm(modules, desc="Building Docker images (est. 2 mins/module)", unit="module", total=len(modules)):
        build_path = Path("commands") / "containers" / module
        if not build_path.exists():
            console.print(f"[warning]Path {build_path} does not exist. Skipping module {module}.[/warning]")
            continue
        console.print(f"[info]Building Docker image for module:[/info] {module}")
        image_tag = module.lower().replace(' ', '-')
        try:
            run_subprocess_fn(
                ["docker", "build", "-t", f"ensemble/{image_tag}", str(build_path)],
                check=True,
                capture_output=True
            )
            console.print(f"[success]Successfully built image for:[/success] {module}")
        except subprocess.CalledProcessError as e:
            console.print(f"[warning]Docker build failed for module {module}: {e}[/warning]")

def save_setup_info(setup_info: dict, filename: str = "ensemble.yaml") -> str:
    """
    Save setup information to a YAML file.
    """
    with open(filename, "w") as f:
        yaml.dump(setup_info, f)
    return f"[success]Setup information saved to {filename}.[/success]"

def get_available_port(start_port: int) -> int:
    """
    Return the first available port starting from start_port.
    """
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                port += 1

def serve_model(model: str, port: int, run_subprocess_fn=subprocess.run) -> (str, int):
    """
    Serve the model using the LitGPT CLI syntax.
    If the given port is in use, automatically increment to the next available port.
    Returns a tuple of the success message and the port used.
    """
    available_port = get_available_port(port)
    try:
        cmd = ["litgpt", "serve", model, "--port", str(available_port)]
        run_subprocess_fn(cmd, check=True, capture_output=True, text=True)
        success_msg = f"[success]Server started on port {available_port} with model: {model}[/success]"
        test_curl = f"curl http://localhost:{available_port}/"
        console.print(f"[info]You can test the server with: {test_curl}[/info]")
        return success_msg, available_port
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() if e.stderr else str(e)
        console.print(f"ERROR:    {error_output}")
        return f"[warning]Failed to start server: {e}[/warning]", available_port

def get_hardware_info() -> dict:
    """
    Get hardware information and categorization.
    """
    cpu_model, cpu_cores, memory_gb, gpu_memory = detect_hardware()
    hardware_category = get_hardware_category(memory_gb)
    return {
        "cpu_model": cpu_model,
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "gpu_memory": gpu_memory,
        "category": hardware_category
    }

@app.command()
def setup(
    model_choice: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Optional model choice (ignored in this setup; always uses HuggingFaceTB/SmolLM2-1.7B-Instruct)"
    )
):
    """Run the full solo server setup."""
    console.print("\n")
    print_banner()
    console.print("\n")

    # Step 1: Hardware Detection & Categorization
    console.print("[info]Detecting hardware...[/info]")
    hardware_info = get_hardware_info()
    hardware_info_str = (
        f"CPU: {hardware_info['cpu_model']} ({hardware_info['cpu_cores']} cores)\n"
        f"Memory: {hardware_info['memory_gb']} GB\n"
        f"GPU Memory: {hardware_info['gpu_memory']} GB\n"
        f"Category: {hardware_info['category']}"
    )
    console.print(Panel(hardware_info_str, title="Hardware Info", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    
    # Step 2: Core Initialization Prompt
    if not prompt_core_initialization():
        console.print("[warning]Exiting setup.[/warning]")
        raise typer.Exit()
    
    console.print("\n")
    
    # Step 3: Model Download Simulation (always uses the specified model)
    download_message = simulate_model_download(MODEL)
    console.print(download_message)
    
    console.print("\n")
    
    # NEW STEP: Test the downloaded model using the solo @@ structure
    console.print(Panel("Testing downloaded model...", title="Test Model", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    test_output = test_downloaded_model(MODEL)
    
    console.print("\n")
    
    # Step 4: Advanced Modules Prompt (optional)
    advanced_modules, module_pack = prompt_advanced_modules()
    if advanced_modules:
        console.print(f"[info]Vertical selected: {module_pack}[/info]")
    else:
        console.print("[info]Skipping advanced modules.[/info]")
    
    console.print("\n")
    
    # Step 5: Save Setup Information to YAML and print config details
    setup_info = {
        "checkpoint_dir": str(Path("checkpoints") / MODEL),
        "devices": 1,
        "max_new_tokens": 50,
        "port": START_PORT,  # initial port, actual port may change
        "precision": None,
        "quantize": None,
        "stream": False,
        "temperature": 0.8,
        "top_k": 50,
        "top_p": 1.0,
        "selected_model": MODEL,
        "hardware": hardware_info,
        "advanced_modules": advanced_modules,
        "module_pack": module_pack,
        "model_choice": model_choice
    }
    save_message = save_setup_info(setup_info)
    console.print(save_message)
    console.print(setup_info)
    
    # Step 6: Docker Ensemble Build for Advanced Modules (if enabled)
    if advanced_modules and module_pack:
        console.print(Panel("Starting Docker builds for advanced modules...", title="Docker Ensemble", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
        build_docker_ensemble(module_pack)
    
    console.print("\n")
    console.print(Panel("Solo core initialization complete!", title="Setup Complete", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    console.print("\n")
    
    # Step 7: Serve the Model using LitGPT CLI syntax and capture errors gracefully
    console.print(Panel(f"Starting server with model: {MODEL}", title="Server", border_style="panel.border", box=box.ROUNDED, padding=(1, 2)))
    server_message, used_port = serve_model(MODEL, port=START_PORT)
    console.print(server_message)

if __name__ == "__main__":
    app()
