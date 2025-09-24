"""
Authentication utilities for LeRobot
"""

import re
import subprocess
import typer
from rich.prompt import Confirm


def check_huggingface_login() -> tuple[bool, str]:
    """
    Check if user is logged in to HuggingFace and return (is_logged_in, username)
    """
    try:
        # Check if user is logged in by running huggingface-cli whoami
        result = subprocess.run(
            ["hf", "auth", "whoami"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            username = ""

            for line in lines:
                match = re.search(r"user:\s*(\S+)", line, flags=re.IGNORECASE)
                if match:
                    username = match.group(1)
                    break

            if not username and lines:
                username = lines[0]

            username = username.strip()

            # Check if output contains an actual username (not error messages)
            if username and not any(phrase in username.lower() for phrase in ['not logged in', 'error', 'failed', 'invalid']):
                return True, username
            else:
                return False, ""
        else:
            return False, ""
            
    except FileNotFoundError:
        typer.echo("❌ huggingface-cli not found. Please install transformers with: pip install transformers[cli]")
        return False, ""
    except Exception as e:
        typer.echo(f"❌ Error checking HuggingFace login status: {e}")
        return False, ""


def huggingface_login_flow() -> tuple[bool, str]:
    """
    Handle HuggingFace login flow and return (success, username)
    """
    # Check if already logged in
    is_logged_in, username = check_huggingface_login()
    
    if is_logged_in:
        typer.echo(f"✅ Already logged in to HuggingFace as: {username}")
        return True, username

    try:
        # Run huggingface-cli login
        typer.echo("Please enter your HuggingFace token when prompted.")
        
        result = subprocess.run(["hf", "auth", "login"], check=False)
        
        if result.returncode == 0:
            # Check login status again
            is_logged_in, username = check_huggingface_login()
            if is_logged_in:
                typer.echo(f"✅ Successfully logged in as: {username}")
                return True, username
            else:
                typer.echo("❌ Login appeared successful but unable to verify username.")
                return False, ""
        else:
            typer.echo("❌ Login failed.")
            return False, ""
            
    except Exception as e:
        typer.echo(f"❌ Error during login: {e}")
        return False, ""


def authenticate_huggingface() -> tuple[bool, str]:
    """
    Handle HuggingFace authentication flow with user interaction.
    Returns: (success, username)
    """
    # Check if already logged in
    is_logged_in, username = check_huggingface_login()
    
    if is_logged_in:
        typer.echo(f"✅ Already logged in to HuggingFace as: {username}")
        return True, username
    
    # Not logged in, prompt for login
    typer.echo("🔐 You need to log in to HuggingFace.")
    should_login = Confirm.ask("Would you like to log in now?", default=True)
    
    if not should_login:
        typer.echo("❌ HuggingFace login required.")
        return False, ""
    
    # Perform login
    login_success, username = huggingface_login_flow()
    return login_success, username
