"""
Port detection utilities for LeRobot
"""

import platform
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import typer
from rich.prompt import Prompt


def find_available_ports() -> List[str]:
    """Find all available serial ports on the system"""
    try:
        from serial.tools import list_ports  # Part of pyserial library
        
        if platform.system() == "Windows":
            # List COM ports using pyserial
            ports = [port.device for port in list_ports.comports()]
        else:  # Linux/macOS
            # List /dev/tty* ports for Unix-based systems
            ports = [str(path) for path in Path("/dev").glob("tty*")]
        return ports
    except ImportError:
        typer.echo("❌ pyserial is required for port detection. Installing...")
        try:
            subprocess.run(["pip", "install", "pyserial"], check=True)
            # Retry import after installation
            from serial.tools import list_ports
            if platform.system() == "Windows":
                ports = [port.device for port in list_ports.comports()]
            else:
                ports = [str(path) for path in Path("/dev").glob("tty*")]
            return ports
        except Exception as e:
            typer.echo(f"❌ Failed to install pyserial: {e}")
            return []


def detect_arm_port(arm_type: str) -> Optional[str]:
    """
    Detect the port for a specific arm (leader or follower)
    Returns the detected port or None if detection failed
    """
    typer.echo(f"\n🔍 Detecting port for {arm_type} arm...")
    
    # Get initial ports
    ports_before = find_available_ports()
    typer.echo(f"Available ports: {ports_before}")
    
    # Ask user to plug in the arm
    typer.echo(f"\n📱 Please plug in your {arm_type} arm and press Enter when connected.")
    input()
    
    time.sleep(1.0)  # Allow time for port to be detected
    
    # Get ports after connection
    ports_after = find_available_ports()
    new_ports = list(set(ports_after) - set(ports_before))
    
    if len(new_ports) == 1:
        port = new_ports[0]
        typer.echo(f"✅ Detected {arm_type} arm on port: {port}")
        return port
    elif len(new_ports) == 0:
        # If no new ports detected but there are existing ports,
        # the arm might already be connected. Try unplug/replug method.
        if len(ports_before) > 0:
            typer.echo(f"⚠️  No new port detected. The {arm_type} arm might already be connected.")
            typer.echo(f"Let's identify the correct port by unplugging and replugging.")
            
            # Ask user to unplug the arm
            typer.echo(f"\n📱 Please UNPLUG your {arm_type} arm and press Enter when disconnected.")
            input()
            
            time.sleep(1.0)  # Allow time for port to be released
            
            # Get ports after disconnection
            ports_unplugged = find_available_ports()
            missing_ports = list(set(ports_before) - set(ports_unplugged))
            
            if len(missing_ports) == 1:
                # Found the port that disappeared
                port = missing_ports[0]
                typer.echo(f"✅ Identified {arm_type} arm port: {port}")
                typer.echo(f"📱 Please plug your {arm_type} arm back in and press Enter.")
                input()
                time.sleep(1.0)  # Allow time for reconnection
                return port
            elif len(missing_ports) == 0:
                typer.echo(f"❌ No port disappeared when unplugging {arm_type} arm. Please check connection.")
                return None
            else:
                typer.echo(f"⚠️  Multiple ports disappeared: {missing_ports}")
                typer.echo("Please select which port corresponds to your arm:")
                for i, port in enumerate(missing_ports, 1):
                    typer.echo(f"  {i}. {port}")
                
                choice = int(Prompt.ask("Enter port number", default="1"))
                if 1 <= choice <= len(missing_ports):
                    port = missing_ports[choice - 1]
                    typer.echo(f"📱 Please plug your {arm_type} arm back in and press Enter.")
                    input()
                    time.sleep(1.0)
                    return port
                else:
                    port = missing_ports[0]
                    typer.echo(f"📱 Please plug your {arm_type} arm back in and press Enter.")
                    input()
                    time.sleep(1.0)
                    return port
        else:
            typer.echo(f"❌ No ports available and no new port detected for {arm_type} arm. Please check connection.")
            return None
    else:
        typer.echo(f"⚠️  Multiple new ports detected: {new_ports}")
        typer.echo("Please select the correct port:")
        for i, port in enumerate(new_ports, 1):
            typer.echo(f"  {i}. {port}")
        
        choice = int(Prompt.ask("Enter port number", default="1"))
        if 1 <= choice <= len(new_ports):
            return new_ports[choice - 1]
        else:
            return new_ports[0]


def detect_and_retry_ports(leader_port: str, follower_port: str, config: dict = None) -> tuple[str, str]:
    """
    Detect new ports if connection fails and update config
    Returns (new_leader_port, new_follower_port)
    """
    typer.echo("🔍 Ports may have changed. Detecting new ports...")
    
    # Detect new ports
    new_leader_port = detect_arm_port("leader")
    new_follower_port = detect_arm_port("follower")
    
    if new_leader_port and new_follower_port:
        typer.echo(f"✅ Found new ports:")
        typer.echo(f"   • Leader: {leader_port} → {new_leader_port}")
        typer.echo(f"   • Follower: {follower_port} → {new_follower_port}")
        
        # Update config with new ports if provided
        if config:
            from solo_server.commands.robots.lerobot.config import save_lerobot_config
            save_lerobot_config(config, {
                'leader_port': new_leader_port,
                'follower_port': new_follower_port
            })
        
        return new_leader_port, new_follower_port
    else:
        typer.echo("❌ Could not detect new ports automatically.")
        typer.echo("Please check your robot connections and try again.")
        return leader_port, follower_port