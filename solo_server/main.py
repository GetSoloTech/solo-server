import time
import typer
import click
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich import box
from litgpt import LLM  # Requires: pip install 'litgpt[all]'

app = typer.Typer()

# Define a custom neon blue theme
solo_theme = Theme({
    "info": "bold bright_blue",
    "warning": "bold magenta",
    "success": "bold bright_blue",
    "panel.border": "bright_blue",
    "panel.title": "bright_cyan"
})
console = Console(theme=solo_theme)

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

@app.command()
def setup():
    console.print("\n")
    
    # Step 1: Hardware Detection & Categorization
    typer.echo("Detecting hardware...")
    cpu_model, cpu_cores, memory_gb, gpu_memory = detect_hardware()
    hardware_category = get_hardware_category(memory_gb)
    hardware_info = (
        f"CPU: {cpu_model} ({cpu_cores} cores)\n"
        f"Memory: {memory_gb} GB\n"
        f"GPU Memory: {gpu_memory} GB\n"
        f"Category: {hardware_category}"
    )
    console.print(
        Panel(hardware_info, title="Hardware Info", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    
    # Step 2: Core Initialization Prompt
    init_prompt = (
        "Continue to solo core initialization?\n"
        "Yes: Proceed with full initialization and model setup\n"
        "No:  Exit setup"
    )
    console.print(
        Panel(init_prompt, title="Core Initialization", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    if not typer.confirm("", default=True):
        typer.echo("Exiting setup.")
        raise typer.Exit()
    
    console.print("\n")
    
    # Step 3: Model Selection & Download Simulation
    model_map = {
        "Fresh Adopter": "SmolLM2-135M",
        "Mid Range": "Qwen2.5-0.5B",
        "High Performance": "microsoft/phi-2",
        "Maestro": "Deepseek-r1"
    }
    selected_model = model_map.get(hardware_category, "SmolLM2-135M")
    with console.status(f"Downloading model {selected_model}...", spinner="dots", spinner_style="bold bright_blue"):
        time.sleep(3)  # Simulate download delay
    typer.echo(f"Model {selected_model} download complete.")
    
    console.print("\n")
    
    # Step 4: Advanced Modules Prompt
    adv_prompt = (
        "Load advanced modules?\n"
        "Yes: Load additional functionalities and module packs\n"
        "No:  Skip advanced modules"
    )
    console.print(
        Panel(adv_prompt, title="Advanced Modules", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    if typer.confirm("", default=True):
        module_pack_info = (
            "Choose module pack:\n"
            "pro             - Pro Pack: RAG, OCR, and Voice Models\n"
            "industrial      - Industrial Pack: CV, Search, and Video Models\n"
            "robotics        - Robotics Pack: ROS, OpenEMMA, and Advanced Models\n"
            "custom ensemble - Custom Ensemble: Paid option for tailored modules\n"
            "Enter your choice:"
        )
        console.print(
            Panel(module_pack_info, title="Module Pack Options", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
        )
        module_pack = typer.prompt("", type=click.Choice(["pro", "industrial", "robotics", "custom ensemble"], case_sensitive=False), default="pro")
        typer.echo(f"Module pack selected: {module_pack}")
    else:
        typer.echo("Skipping advanced modules.")
    
    console.print("\n")
    console.print(
        Panel("Solo core initialization complete!", title="Setup Complete", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    console.print("\n")
    
    # Step 5: Load the LLM using litgpt
    console.print(
        Panel(f"Loading LLM model: {selected_model}", title="LLM Load", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    try:
        llm = LLM.load(selected_model)
        typer.echo("LLM loaded successfully.")
    except Exception as e:
        typer.echo(f"Failed to load LLM: {e}")
        raise typer.Exit()
    
    # Step 6: Start the server on port 5070
    console.print(
        Panel(f"Starting server on port 5070 with model: {selected_model}", title="Server", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
    )
    try:
        llm.serve(port=5070)
    except Exception as e:
        typer.echo(f"Failed to start server: {e}")
    
    # Step 7: Optionally Generate Text
    prompt_text = typer.prompt(
        "Enter a prompt to generate text (default: 'Fix the spelling: Every fall, the familly goes to the mountains.')",
        default="Fix the spelling: Every fall, the familly goes to the mountains."
    )
    typer.echo("Generating text...")
    try:
        generated_text = llm.generate(prompt_text)
        typer.echo("\nGenerated text:")
        typer.echo(generated_text)
    except Exception as e:
        typer.echo(f"Failed to generate text: {e}")

if __name__ == "__main__":
    app()
