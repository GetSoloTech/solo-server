#!/usr/bin/env python3
import os
import sys
import platform
import psutil
import yaml
import shutil
import subprocess
import time
from tqdm import tqdm

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

# Import snapshot_download from huggingface_hub
from huggingface_hub import snapshot_download

console = Console()

GB = 1024 ** 3
LARGE_MEMORY_THRESHOLD = 16 * GB
MEDIUM_MEMORY_THRESHOLD = 8 * GB
SMALL_MEMORY_THRESHOLD = 4 * GB

AVAILABLE_ENGINES = ["ollama", "vllm", "sglang", "llamacpp"]
DEFAULT_ENGINE = "llamacpp"

# Ensure Python 3.8+ is installed
if sys.version_info < (3, 8):
    sys.exit("🚫 Python 3.8 or higher is required.")

# -------------------------------
# Domain-to-model mapping table
# -------------------------------
domain_model_mapping = {
    "Education": {
         "small": "HuggingFaceTB/SmolLM2-135M-Instruct",
         "medium": "HuggingFaceTB/llama-3.2-3B-Instruct",
         "large": "HuggingFaceTB/gemma-3"
    },
    "Agriculture": {
         "small": "HuggingFaceTB/AgriSmol-100M",
         "medium": "HuggingFaceTB/AgriLlama-3B",
         "large": "HuggingFaceTB/AgriGemma-3"
    },
    "Software Development": {
         "small": "HuggingFaceTB/CodeSmol-100M",
         "medium": "HuggingFaceTB/CodeLlama-3B",
         "large": "HuggingFaceTB/CodeGemma-3"
    },
    "Enterprise": {
         "small": "HuggingFaceTB/EnterpriseSmol-100M",
         "medium": "HuggingFaceTB/EnterpriseLlama-3B",
         "large": "HuggingFaceTB/EnterpriseGemma-3"
    },
    "Healthcare": {
         "small": "HuggingFaceTB/HealthSmol-100M",
         "medium": "HuggingFaceTB/HealthLlama-3B",
         "large": "HuggingFaceTB/HealthGemma-3"
    },
    "Governance": {
         "small": "HuggingFaceTB/GovSmol-100M",
         "medium": "HuggingFaceTB/GovLlama-3B",
         "large": "HuggingFaceTB/GovGemma-3"
    },
    "Robotics": {
         "small": "HuggingFaceTB/RobotSmol-100M",
         "medium": "HuggingFaceTB/RobotLlama-3B",
         "large": "HuggingFaceTB/RobotGemma-3"
    }
}

# -------------------------------
# Utility: Print All-Models Table
# -------------------------------
def print_models_table():
    from rich.table import Table
    table = Table(title="Domain Model Mapping", border_style="blue")
    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Small Model", style="magenta")
    table.add_column("Medium Model", style="green")
    table.add_column("Large Model", style="yellow")
    for domain, mapping in domain_model_mapping.items():
        table.add_row(domain, mapping["small"], mapping["medium"], mapping["large"])
    console.print(table)

# If the script is called with "all-models", show the table and exit.
if len(sys.argv) > 1 and sys.argv[1] == "all-models":
    print_models_table()
    sys.exit(0)

# -------------------------------
# Interactive prompts
# -------------------------------
def get_user_input_domain():
    """
    Prompt the user to select a domain or enter a custom one.
    """
    domains = list(domain_model_mapping.keys()) + ["Custom"]
    console.print(Panel("Select your domain from the following options:", border_style="blue"))
    for idx, d in enumerate(domains, start=1):
        console.print(f"[blue]{idx}.[/blue] {d}")
    
    choice = Prompt.ask("Enter the number corresponding to your domain", default=str(len(domains)))
    try:
        choice_num = int(choice)
        if 1 <= choice_num < len(domains):
            return domains[choice_num - 1]
        else:
            return Prompt.ask("Enter your custom domain")
    except ValueError:
        console.print("[red]Invalid input. Defaulting to 'Custom'.[/red]")
        return Prompt.ask("Enter your custom domain")

def get_user_input_role():
    """
    Prompt the user for their role.
    """
    return Prompt.ask("Enter your role (e.g., teacher, developer, data scientist)")

def get_inference_engine_preference():
    """
    Ask the user to choose their default inference engine.
    """
    console.print(Panel("Select your preferred default inference engine:", border_style="blue"))
    for idx, eng in enumerate(AVAILABLE_ENGINES, start=1):
        console.print(f"[blue]{idx}.[/blue] {eng}")
    choice = Prompt.ask("Enter the number corresponding to your preferred inference engine", default="1")
    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(AVAILABLE_ENGINES):
            return AVAILABLE_ENGINES[choice_num - 1]
        else:
            console.print("[red]Invalid choice. Defaulting to llamacpp.[/red]")
            return DEFAULT_ENGINE
    except ValueError:
        console.print("[red]Invalid input. Defaulting to llamacpp.[/red]")
        return DEFAULT_ENGINE

def get_file_type_preference():
    """
    Ask the user to choose their preferred file type.
    """
    FILE_TYPE_PREFERENCE = ["onnx", "gguf"]
    console.print(Panel("Select your preferred file type for model files:", border_style="blue"))
    for idx, ftype in enumerate(FILE_TYPE_PREFERENCE, start=1):
        console.print(f"[blue]{idx}.[/blue] {ftype}")
    choice = Prompt.ask("Enter the number corresponding to your file type preference", default="1")
    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(FILE_TYPE_PREFERENCE):
            return FILE_TYPE_PREFERENCE[choice_num - 1]
        else:
            console.print("[red]Invalid choice. Defaulting to onnx.[/red]")
            return "onnx"
    except ValueError:
        console.print("[red]Invalid input. Defaulting to onnx.[/red]")
        return "onnx"

# -------------------------------
# Hardware Detection Functions
# -------------------------------
def detect_gpu():
    """
    Return a dictionary describing GPU availability and names.
    Tries PyTorch first, then falls back to nvidia-smi.
    """
    gpu_info = {"available": False, "gpu_names": []}

    try:
        import torch
        if torch.cuda.is_available():
            gpu_info["available"] = True
            for i in range(torch.cuda.device_count()):
                gpu_info["gpu_names"].append(torch.cuda.get_device_name(i))
            return gpu_info
    except ImportError:
        pass

    if shutil.which("nvidia-smi"):
        try:
            output = (
                subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    stderr=subprocess.STDOUT,
                )
                .decode()
                .strip()
                .splitlines()
            )
            if output:
                gpu_info["available"] = True
                gpu_info["gpu_names"] = output
        except Exception:
            pass
    return gpu_info

def gather_hardware_info():
    """
    Gather OS, CPU, Memory, and GPU info into a dictionary.
    """
    hardware_info = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        },
        "cpu": {
            "processor": platform.processor(),
            "architecture": platform.machine(),
            "cores": psutil.cpu_count(logical=False),
            "logical_processors": psutil.cpu_count(logical=True)
        },
        "memory": {
            "total_bytes": psutil.virtual_memory().total,
            "available_bytes": psutil.virtual_memory().available,
        },
        "gpu": detect_gpu()
    }
    return hardware_info

def detect_computer_size():
    """
    Detect computer size based on available memory.
    - Large: 16GB or more
    - Medium: 8GB to 16GB
    - Small: less than 8GB
    """
    mem = psutil.virtual_memory().total
    if mem >= LARGE_MEMORY_THRESHOLD:
        return "large"
    elif mem >= MEDIUM_MEMORY_THRESHOLD:
        return "medium"
    else:
        return "small"

# -------------------------------
# Model Download Function
# -------------------------------
def download_model(model_id, local_dir):
    """
    Download a model using snapshot_download from huggingface_hub into the specified local directory.
    """
    os.makedirs(local_dir, exist_ok=True)
    with Status(f"[blue]Downloading model {model_id} to {local_dir}...", spinner="dots") as status:
        try:
            snapshot_download(repo_id=model_id, local_dir=local_dir)
        except Exception as e:
            console.print(f"[red]Error downloading model: {e}[/red]")
            sys.exit(1)
    console.print(f"[green]Model downloaded successfully to {local_dir}[/green]")

# -------------------------------
# Save Solo Card and Display
# -------------------------------
def save_to_solo_card(data):
    """
    Save the provided data into solo-card.yaml in the Hugging Face default cache directory.
    """
    default_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    os.makedirs(default_cache_dir, exist_ok=True)
    output_file = os.path.join(default_cache_dir, "solo-card.yaml")
    with open(output_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return output_file

# -------------------------------
# Main Onboarding Function
# -------------------------------
def main():
    console.print(Panel("Welcome to the Solo Model Onboarding!", border_style="blue", title="Solo Onboarding"))
    
    # Get domain and role from user
    domain = get_user_input_domain()
    role = get_user_input_role()
    
    # Get additional preferences
    inference_engine = get_inference_engine_preference()
    file_type = get_file_type_preference()
    
    # Gather hardware info with a spinner
    with Status("[blue]Detecting hardware...", spinner="dots") as status:
        hardware_info = gather_hardware_info()
        time.sleep(1)  # simulate delay

    # Determine computer size
    comp_size = detect_computer_size()
    console.print(f"[blue]Detected computer size:[/blue] {comp_size}")

    # Determine the model to download based on domain mapping;
    # if domain not in our mapping (i.e. "Custom"), use a default mapping.
    if domain in domain_model_mapping:
        model_id = domain_model_mapping[domain].get(comp_size, domain_model_mapping[domain]["small"])
    else:
        # Default mapping (same as for Education)
        default_models = {
            "small": "HuggingFaceTB/SmolLM2-135M-Instruct",
            "medium": "HuggingFaceTB/llama-3.2-3B-Instruct",
            "large": "HuggingFaceTB/gemma-3"
        }
        model_id = default_models.get(comp_size, default_models["small"])
    
    console.print(f"[blue]Selected model for {domain} on a {comp_size} computer:[/blue] {model_id}")

    # Download the model using snapshot_download into a local folder
    local_model_dir = os.path.join(os.getcwd(), "downloaded_model")
    download_model(model_id, local_model_dir)

    # Simulate a finishing progress using tqdm
    console.print("[blue]Finalizing setup...[/blue]")
    for _ in tqdm(range(50), desc="Finishing", ncols=80):
        time.sleep(0.03)

    # Prepare data for solo-card.yaml
    data = {
        "domain": domain,
        "role": role,
        "inference_engine": inference_engine,
        "file_type": file_type,
        "hardware": hardware_info,
        "model": {
            "id": model_id,
            "local_dir": local_model_dir
        },
        "seed_tags": [domain, role, inference_engine, file_type]
    }
    solo_card_path = save_to_solo_card(data)
    
    # Read the solo card YAML and display it in an awesome blue panel
    with open(solo_card_path, "r") as f:
        solo_card_content = f.read()
    console.print(Panel(solo_card_content, title="Your Solo Card", border_style="blue"))

    console.print(Panel("🎉 Onboarding complete! Your solo-card.yaml is ready.", border_style="blue", title="Success"))

if __name__ == "__main__":
    main()
