import re
import typer
from huggingface_hub import list_repo_files

def get_available_models(repo_id: str, suffix: list[str] | str = ".gguf") -> list:
    """
    Fetch the list of available models from a Hugging Face repository.

    :param repo_id: The repository ID on Hugging Face (e.g., "TheBloke/Llama-2-7B-GGUF")
    :param suffix: String or list of strings of file extensions to filter (e.g., [".gguf", ".bin"])
    :return: List of model files in the repository
    """
    try:
        files = list_repo_files(repo_id)
        # Convert single suffix to list for uniform handling
        suffixes = [suffix] if isinstance(suffix, str) else suffix
        # Filter for files with specified suffixes
        model_files = [f for f in files if any(f.endswith(s) for s in suffixes)]
        return model_files
     
    except Exception as e:
        typer.echo(f"Error fetching models from {repo_id}: {e}")
        return []
    

def select_best_model_file(model_files):
    """
    Select the most appropriate model file based on quantization level.
    
    Prioritizes:
    1. q4_k_M if available
    2. Any q4 model
    3. q5_k_M if available
    4. Any q5 model
    5. q8_k_M if available
    6. Any q8 model
    7. First available model
    
    Parameters:
    model_files (list): List of available model files
    
    Returns:
    str: The selected model file name
    """
    if not model_files:
        return None
    
    if len(model_files) == 1:
        return model_files[0]
    
    # Define regex patterns for different quantization levels
    q4_km_pattern = re.compile(r'q4_k_m', re.IGNORECASE)
    q4_pattern = re.compile(r'q4', re.IGNORECASE)
    q5_km_pattern = re.compile(r'q5_k_m', re.IGNORECASE)
    q5_pattern = re.compile(r'q5', re.IGNORECASE)
    q8_km_pattern = re.compile(r'q8_k_m', re.IGNORECASE)
    q8_pattern = re.compile(r'q8', re.IGNORECASE)
    
    # Check for q4_k_M models
    q4_km_models = [f for f in model_files if q4_km_pattern.search(f)]
    if q4_km_models:
        return q4_km_models[0]
    
    # Check for any q4 models
    q4_models = [f for f in model_files if q4_pattern.search(f)]
    if q4_models:
        return q4_models[0]
    
    # Check for q5_k_M models
    q5_km_models = [f for f in model_files if q5_km_pattern.search(f)]
    if q5_km_models:
        return q5_km_models[0]
    
    # Check for any q5 models
    q5_models = [f for f in model_files if q5_pattern.search(f)]
    if q5_models:
        return q5_models[0]
    
    # Check for q8_k_M models
    q8_km_models = [f for f in model_files if q8_km_pattern.search(f)]
    if q8_km_models:
        return q8_km_models[0]
    
    # Check for any q8 models
    q8_models = [f for f in model_files if q8_pattern.search(f)]
    if q8_models:
        return q8_models[0]
    
    # If no specific quantization found, return the first model
    return model_files[0]