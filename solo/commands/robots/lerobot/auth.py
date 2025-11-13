"""
Authentication utilities for LeRobot
"""

import re
import subprocess
import typer
import os
import json
from pathlib import Path
from rich.prompt import Confirm
from solo.config import CONFIG_PATH


def get_stored_credentials() -> tuple[str, str]:
    """
    Get stored HuggingFace credentials from config.json and .env file.
    Returns: (username, token)
    """
    username = ""
    token = ""
    
    # Try to get from .env file first
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('HUGGINGFACE_USERNAME='):
                        username = line.split('=', 1)[1].strip()
                    elif line.startswith('HUGGINGFACE_TOKEN='):
                        token = line.split('=', 1)[1].strip()
        except Exception:
            pass
    
    # If not found in .env, try config.json
    if not username or not token:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    hf_config = config.get('hugging_face', {})
                    username = hf_config.get('username', '')
                    token = hf_config.get('token', '')
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    return username, token


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
    Handle HuggingFace authentication flow using stored credentials.
    Returns: (success, username)
    """
    # Check if already logged in
    is_logged_in, username = check_huggingface_login()
    
    if is_logged_in:
        typer.echo(f"✅ Already logged in to HuggingFace as: {username}")
        return True, username
    
    # Try to use stored credentials
    stored_username, stored_token = get_stored_credentials()
    
    if stored_username and stored_token:
        typer.echo(f"🔐 Using stored HuggingFace credentials for: {stored_username}")
        
        # Set environment variable for HuggingFace token
        os.environ['HUGGINGFACE_TOKEN'] = stored_token
        
        # Try to login with stored credentials
        try:
            # Use huggingface-cli to login with token
            result = subprocess.run(
                ["hf", "auth", "login", "--token", stored_token], 
                check=False,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Verify login
                is_logged_in, username = check_huggingface_login()
                if is_logged_in:
                    typer.echo(f"✅ Successfully logged in using stored credentials: {username}")
                    return True, username
                else:
                    typer.echo("❌ Stored credentials appear to be invalid.")
            else:
                typer.echo("❌ Failed to login with stored credentials.")
        except Exception as e:
            typer.echo(f"❌ Error using stored credentials: {e}")
    
    # Fallback to interactive login if stored credentials don't work
    typer.echo("🔐 You need to log in to HuggingFace.")
    should_login = Confirm.ask("Would you like to log in now?", default=True)
    
    if not should_login:
        typer.echo("❌ HuggingFace login required.")
        return False, ""
    
    # Perform interactive login
    login_success, username = huggingface_login_flow()
    return login_success, username
