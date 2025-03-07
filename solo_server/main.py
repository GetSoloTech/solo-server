import time
import subprocess
import typer
import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich import box

app = typer.Typer(help="Solo Server Setup CLI\nA polished CLI for hardware detection, model initialization, and advanced module loading.")

# Define a Google-inspired theme (blue, red, yellow, green)
google_theme = Theme({
    "header": "bold #4285F4",      # Google Blue
    "info": "bold #4285F4",        # Google Blue
    "warning": "bold #DB4437",     # Google Red
    "success": "bold #0F9D58",     # Google Green
    "prompt": "bold #F4B400",      # Google Yellow
    "panel.border": "bright_blue",
    "panel.title": "bold white"
})
console = Console(theme=google_theme)

# Model options mapping (based on your table)
# Here we assume the "smallest fastest" option for each family:
MODEL_OPTIONS = {
    "llama3": "meta-llama/Llama-3.1-1B-Instruct",    # Smallest variant from Llama 3 family
    "code_llama": "meta-llama/Code-Llama-7B",          # Smallest variant for Code Llama
    "codegemma": "google/CodeGemma-7B",                # Only one variant for CodeGemma
    "gemma2": "google/Gemma2-2B",                      # Smallest variant for Gemma 2
    "phi4": "microsoft/phi-4",                         # Only one option for Phi 4 (14B)
    "qwen2.5": "qwen2.5/0.5B",                         # Smallest variant for Qwen2.5
    "qwen2.5_coder": "qwen2.5-coder/0.5B",             # Smallest variant for Qwen2.5 Coder
    "r1_distill_llama": "deepseek-ai/R1-Distill-Llama-8B"  # Smallest variant for R1 Distill Llama
}

def print_banner():
    """Display a header banner for the Solo Server CLI."""
    banner_text = """

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

def auto_select_model(hardware_category: str) -> str:
    """
    Auto-select a default model based on hardware category.
    For each situation, we recommend the smallest and fastest model available.
    """
    mapping = {
        "Fresh Adopter": MODEL_OPTIONS["llama3"],
        "Mid Range": MODEL_OPTIONS["code_llama"],
        "High Performance": MODEL_OPTIONS["phi4"],
        "Maestro": MODEL_OPTIONS["r1_distill_llama"]
    }
    return mapping.get(hardware_category, MODEL_OPTIONS["llama3"])

def simulate_model_download(selected_model: str, sleep_time: int = 3):
    """
    Simulate model download with a delay.
    """
    with console.status(f"[info]Downloading model {selected_model}...[/info]", spinner="dots"):
        time.sleep(sleep_time)  # Simulate download delay
    return f"[success]Model {selected_model} download complete.[/success]"

def prompt_core_initialization(confirm_fn=typer.confirm) -> bool:
    """
    Ask user to confirm core initialization.
    """
    init_prompt = (
        "Continue to solo core initialization?\n"
        "Yes: Proceed with full initialization and model setup\n"
        "No:  Exit setup"
    )
    console.print(
        Panel(init_prompt, title="Core Initialization", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
    )
    return confirm_fn("", default=True)

def prompt_advanced_modules(confirm_fn=typer.confirm, prompt_fn=typer.prompt) -> (bool, str):
    """
    Ask user if they want to load advanced modules and select module pack if yes.
    Returns a tuple (advanced_modules, module_pack)
    """
    adv_prompt = (
        "Load advanced modules?\n"
        "Yes: Load additional functionalities and module packs\n"
        "No:  Skip advanced modules"
    )
    console.print(
        Panel(adv_prompt, title="Advanced Modules", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
    )
    advanced_modules = confirm_fn("", default=True)
    module_pack = None
    if advanced_modules:
        module_pack_info = (
            "Choose module pack:\n"
            "pro             - Pro Pack: RAG, LangChain, Transformers\n"
            "industrial      - Industrial Pack: PyTorch, Tensorflow, vLLM\n"
            "robotics        - Robotics Pack: ROS, LeRobot, OpenEMMA\n"
            "custom ensemble - Custom Ensemble: Additional containers\n"
            "Enter your choice:"
        )
        console.print(
            Panel(module_pack_info, title="Module Pack Options", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
        )
        module_pack = prompt_fn("", type=click.Choice(["pro", "industrial", "robotics", "custom ensemble"], case_sensitive=False), default="pro")
    return advanced_modules, module_pack

def build_docker_ensemble(module_pack: str, run_subprocess_fn=subprocess.run):
    """
    Build an ensemble of Docker images for the selected module pack.
    """
    docker_modules = {
        "pro": [
            "rag",
            "langchain",
            "Transformers"
        ],
        "industrial": [
            "PyTorch",
            "Tensorflow",
            "vLLM"
        ],
        "robotics": [
            "ROS",
            "LeRobot",
            "OpenEMMA"
        ],
        "custom ensemble": [
            "Browser Use",
            "Computer Use",
            "Cosmos",
            "homeassistant-core",
            "JAX",
            "LITA",
            "llama-index"
        ]
    }
    modules = docker_modules.get(module_pack.lower(), [])
    if not modules:
        console.print(f"[warning]No modules found for the '{module_pack}' pack. Adjust your dictionary as needed.[/warning]")
        return

    for module in modules:
        console.print(f"[info]Building Docker image for module:[/info] {module}")
        image_tag = module.lower().replace(' ', '-')
        build_path = f"./containers/{module}"
        try:
            run_subprocess_fn(
                [
                    "docker", 
                    "build", 
                    "-t", f"ensemble/{image_tag}", 
                    build_path
                ],
                check=True,
                capture_output=True
            )
            console.print(f"[success]Successfully built image for:[/success] {module}")
        except subprocess.CalledProcessError as e:
            console.print(f"[warning]Docker build failed for module {module}: {e}[/warning]")

def save_setup_info(setup_info: dict, filename: str = "ensemble.yaml"):
    """
    Save setup information to a YAML file.
    """
    with open(filename, "w") as f:
        yaml.dump(setup_info, f)
    return f"[success]Setup information saved to {filename}.[/success]"

def serve_model(model: str, port: int = 5070, run_subprocess_fn=subprocess.run) -> str:
    """
    Serve the model using the LitGPT CLI syntax.
    Example: litgpt serve meta-llama/Llama-3.1-1B-Instruct --port 5070
    """
    try:
        cmd = ["litgpt", "serve", model, "--port", str(port)]
        run_subprocess_fn(cmd, check=True)
        return f"[success]Server started on port {port} with model: {model}[/success]"
    except subprocess.CalledProcessError as e:
        return f"[warning]Failed to start server: {e}[/warning]"

def get_hardware_info():
    """
    Get hardware information and categorization.
    """
    cpu_model, cpu_cores, memory_gb, gpu_memory = detect_hardware()
    hardware_category = get_hardware_category(memory_gb)
    hardware_info = {
        "cpu_model": cpu_model,
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "gpu_memory": gpu_memory,
        "category": hardware_category
    }
    return hardware_info

@app.command()
def setup(
    model_choice: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Optional model choice. Options: " + ", ".join(MODEL_OPTIONS.keys())
    )
):
    """Run the full solo server setup."""
    console.print("\n")
    print_banner()
    console.print("\n")

    # Step 1: Hardware Detection & Categorization
    typer.echo("[info]Detecting hardware...[/info]")
    hardware_info = get_hardware_info()
    hardware_info_str = (
        f"CPU: {hardware_info['cpu_model']} ({hardware_info['cpu_cores']} cores)\n"
        f"Memory: {hardware_info['memory_gb']} GB\n"
        f"GPU Memory: {hardware_info['gpu_memory']} GB\n"
        f"Category: {hardware_info['category']}"
    )
    console.print(
        Panel(hardware_info_str, title="Hardware Info", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
    )
    
    # Step 2: Core Initialization Prompt
    if not prompt_core_initialization():
        typer.echo("[warning]Exiting setup.[/warning]")
        raise typer.Exit()
    
    console.print("\n")
    
    # Step 3: Model Selection & Download Simulation
    if model_choice:
        # Use user provided model option if valid
        selected_model = MODEL_OPTIONS.get(model_choice.lower())
        if not selected_model:
            typer.echo(f"[warning]Invalid model choice: {model_choice}. Falling back to auto-selection.[/warning]")
            selected_model = auto_select_model(hardware_info['category'])
    else:
        selected_model = auto_select_model(hardware_info['category'])
    
    download_message = simulate_model_download(selected_model)
    typer.echo(download_message)
    
    console.print("\n")
    
    # Step 4: Advanced Modules Prompt
    advanced_modules, module_pack = prompt_advanced_modules()
    if advanced_modules:
        typer.echo(f"[info]Module pack selected: {module_pack}[/info]")
    else:
        typer.echo("[info]Skipping advanced modules.[/info]")
    
    console.print("\n")
    
    # Step 5: Save Setup Information to ensemble.yaml
    setup_info = {
        "hardware": hardware_info,
        "selected_model": selected_model,
        "advanced_modules": advanced_modules,
        "module_pack": module_pack,
        "model_choice": model_choice
    }
    save_message = save_setup_info(setup_info)
    typer.echo(save_message)
    
    # Step 6: Docker Ensemble Build for Advanced Modules
    if advanced_modules and module_pack:
        console.print(
            Panel("Starting Docker builds for advanced modules...", title="Docker Ensemble", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
        )
        build_docker_ensemble(module_pack)
    
    console.print("\n")
    console.print(
        Panel("Solo core initialization complete!", title="Setup Complete", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
    )
    console.print("\n")
    
    # Step 7: Serve the Model using LitGPT CLI syntax
    console.print(
        Panel(f"Starting server on port 5070 with model: {selected_model}", title="Server", border_style="panel.border", box=box.ROUNDED, padding=(1, 2))
    )
    server_message = serve_model(selected_model, port=5070)
    typer.echo(server_message)

if __name__ == "__main__":
    app()
