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
