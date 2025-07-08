"""
LeRobot utilities for Solo Server
Handles port detection, calibration, and teleoperation setup for robotic arms
"""

import time
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
import typer

console = Console()

# Import lerobot modules with error handling
try:
    from lerobot.calibrate import calibrate, CalibrateConfig
    from lerobot.teleoperate import teleoperate, TeleoperateConfig
    from lerobot.common.teleoperators.so100_leader import SO100LeaderConfig
    from lerobot.common.teleoperators.so101_leader import SO101LeaderConfig
    from lerobot.common.robots.so100_follower import SO100FollowerConfig
    from lerobot.common.robots.so101_follower import SO101FollowerConfig
    from lerobot.common.teleoperators import make_teleoperator_from_config
    from lerobot.common.robots import make_robot_from_config
    LEROBOT_AVAILABLE = True
except ImportError:
    # Set to None if lerobot is not available
    calibrate = None
    CalibrateConfig = None
    teleoperate = None
    TeleoperateConfig = None
    SO100LeaderConfig = None
    SO101LeaderConfig = None
    SO100FollowerConfig = None
    SO101FollowerConfig = None
    make_teleoperator_from_config = None
    make_robot_from_config = None
    LEROBOT_AVAILABLE = False

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

def calibrate_arm(arm_type: str, port: str, robot_type: str = "so100") -> bool:
    """
    Calibrate a specific arm using the lerobot calibration system
    """
    typer.echo(f"\n🔧 Calibrating {arm_type} arm on port {port}...")
    
    if not LEROBOT_AVAILABLE:
        typer.echo("❌ LeRobot modules are not available.")
        typer.echo("Please ensure lerobot is properly installed.")
        return False
    
    try:
        # Determine the appropriate config class based on arm type and robot type
        if arm_type == "leader":
            if robot_type == "so100":
                config_class = SO100LeaderConfig
            elif robot_type == "so101":
                config_class = SO101LeaderConfig
            else:
                typer.echo(f"❌ Unsupported robot type for leader: {robot_type}")
                return False
        elif arm_type == "follower":
            if robot_type == "so100":
                config_class = SO100FollowerConfig
            elif robot_type == "so101":
                config_class = SO101FollowerConfig
            else:
                typer.echo(f"❌ Unsupported robot type for follower: {robot_type}")
                return False
        else:
            typer.echo(f"❌ Unknown arm type: {arm_type}")
            return False
        
        # Create config instance
        if arm_type == "leader":
            arm_config = config_class(port=port, id=f"{robot_type}_{arm_type}")
            calibrate_config = CalibrateConfig(teleop=arm_config)
        else:
            arm_config = config_class(port=port, id=f"{robot_type}_{arm_type}")
            calibrate_config = CalibrateConfig(robot=arm_config)
        
        # Run calibration
        typer.echo(f"🔧 Starting calibration for {arm_type} arm...")
        typer.echo("⚠️  Please follow the calibration instructions that will appear.")
        
        calibrate(calibrate_config)
        typer.echo(f"✅ {arm_type.title()} arm calibrated successfully!")
        return True
        
    except Exception as e:
        typer.echo(f"❌ Calibration failed for {arm_type} arm: {e}")
        return False

def start_teleoperation(leader_port: str, follower_port: str, robot_type: str = "so100") -> bool:
    """
    Start teleoperation between leader and follower arms
    """
    typer.echo(f"\n🎮 Starting teleoperation...")
    typer.echo(f"Leader arm port: {leader_port}")
    typer.echo(f"Follower arm port: {follower_port}")
    
    if not LEROBOT_AVAILABLE:
        typer.echo("❌ LeRobot modules are not available.")
        typer.echo("Please ensure lerobot is properly installed.")
        return False
    
    try:
        # Determine config classes based on robot type
        if robot_type == "so100":
            leader_config_class = SO100LeaderConfig
            follower_config_class = SO100FollowerConfig
        elif robot_type == "so101":
            leader_config_class = SO101LeaderConfig
            follower_config_class = SO101FollowerConfig
        else:
            typer.echo(f"❌ Unsupported robot type: {robot_type}")
            return False
        
        # Create configurations
        leader_config = leader_config_class(port=leader_port, id=f"{robot_type}_leader")
        follower_config = follower_config_class(port=follower_port, id=f"{robot_type}_follower")
        
        # Create teleoperation config
        teleop_config = TeleoperateConfig(
            teleop=leader_config,
            robot=follower_config,
            fps=60,
            display_data=True
        )
        
        typer.echo("🎮 Starting teleoperation... Press Ctrl+C to stop.")
        typer.echo("📋 Move the leader arm to control the follower arm.")
        
        # Start teleoperation
        teleoperate(teleop_config)
        
        return True
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Teleoperation stopped by user.")
        return True
    except Exception as e:
        typer.echo(f"❌ Teleoperation failed: {e}")
        return False

def setup_motors_for_arm(arm_type: str, port: str, robot_type: str = "so100") -> bool:
    """
    Setup motor IDs for a specific arm (leader or follower)
    Returns True if successful, False otherwise
    """
    typer.echo(f"\n🔧 Setting up motor IDs for {arm_type} arm on port {port}...")
    
    if not LEROBOT_AVAILABLE:
        typer.echo("❌ LeRobot modules are not available.")
        typer.echo("Please ensure lerobot is properly installed.")
        return False
    
    try:
        # Determine the appropriate config class based on arm type and robot type
        if arm_type == "leader":
            if robot_type == "so100":
                config_class = SO100LeaderConfig
                make_device = make_teleoperator_from_config
            elif robot_type == "so101":
                config_class = SO101LeaderConfig
                make_device = make_teleoperator_from_config
            else:
                typer.echo(f"❌ Unsupported robot type for leader: {robot_type}")
                return False
        elif arm_type == "follower":
            if robot_type == "so100":
                config_class = SO100FollowerConfig
                make_device = make_robot_from_config
            elif robot_type == "so101":
                config_class = SO101FollowerConfig
                make_device = make_robot_from_config
            else:
                typer.echo(f"❌ Unsupported robot type for follower: {robot_type}")
                return False
        else:
            typer.echo(f"❌ Unknown arm type: {arm_type}")
            return False
        
        # Create device config and instance
        device_config = config_class(port=port, id=f"{robot_type}_{arm_type}")
        device = make_device(device_config)
        
        # Run motor setup
        typer.echo(f"🔧 Starting motor setup for {arm_type} arm...")
        typer.echo("⚠️  You will be asked to connect each motor individually.")
        typer.echo("Make sure your arm is powered on and ready.")
        
        device.setup_motors()
        typer.echo(f"✅ Motor setup completed for {arm_type} arm!")
        return True
        
    except Exception as e:
        typer.echo(f"❌ Motor setup failed for {arm_type} arm: {e}")
        return False

def setup_calibration() -> Dict:
    """
    Setup process for arm calibration 
    Returns configuration dictionary with arm setup details
    """
    config = {}
    
    # Ask for robot type
    typer.echo("\n🤖 Select your robot type:")
    typer.echo("1. SO100")
    typer.echo("2. SO101")
    
    robot_choice = int(Prompt.ask("Enter robot type", default="1"))
    robot_type = "so100" if robot_choice == 1 else "so101"
    config['robot_type'] = robot_type
    
    # Detect and calibrate leader arm
    typer.echo("\n👑 Setting up Leader Arm")
    leader_port = detect_arm_port("leader")
    
    if not leader_port:
        typer.echo("❌ Failed to detect leader arm. Skipping setup.")
        return config
    
    config['leader_port'] = leader_port
    
    # Calibrate leader arm
    if calibrate_arm("leader", leader_port, robot_type):
        config['leader_calibrated'] = True
    else:
        typer.echo("❌ Leader arm calibration failed. Continuing with follower setup.")
        config['leader_calibrated'] = False
    
    # Detect and calibrate follower arm
    typer.echo("\n🤖 Setting up Follower Arm")
    follower_port = detect_arm_port("follower")
    
    if not follower_port:
        typer.echo("❌ Failed to detect follower arm. Skipping setup.")
        return config
    
    config['follower_port'] = follower_port
    
    # Calibrate follower arm
    if calibrate_arm("follower", follower_port, robot_type):
        config['follower_calibrated'] = True
    else:
        typer.echo("❌ Follower arm calibration failed.")
        config['follower_calibrated'] = False
    
    return config

def setup_motors_and_calibration() -> Dict:
    """
    Complete setup process for motor IDs and arm calibration
    Returns configuration dictionary with setup details
    """
    config = {}
    
    # Ask for robot type
    typer.echo("\n🤖 Select your robot type:")
    typer.echo("1. SO100")
    typer.echo("2. SO101")
    
    robot_choice = int(Prompt.ask("Enter robot type", default="1"))
    robot_type = "so100" if robot_choice == 1 else "so101"
    config['robot_type'] = robot_type
    
    # Setup leader arm
    typer.echo("\n👑 Setting up Leader Arm")
    leader_port = detect_arm_port("leader")
    
    if not leader_port:
        typer.echo("❌ Failed to detect leader arm. Skipping setup.")
        return config
    
    config['leader_port'] = leader_port
    
    # Setup motor IDs for leader arm
    typer.echo(f"\n🔧 Setting up motor IDs for leader arm...")
    leader_motors_setup = setup_motors_for_arm("leader", leader_port, robot_type)
    config['leader_motors_setup'] = leader_motors_setup
    
    if not leader_motors_setup:
        typer.echo("⚠️  Leader arm motor setup failed. Continuing with calibration anyway.")
    
    # Calibrate leader arm
    if calibrate_arm("leader", leader_port, robot_type):
        config['leader_calibrated'] = True
    else:
        typer.echo("❌ Leader arm calibration failed. Continuing with follower setup.")
        config['leader_calibrated'] = False
    
    # Setup follower arm
    typer.echo("\n🤖 Setting up Follower Arm")
    follower_port = detect_arm_port("follower")
    
    if not follower_port:
        typer.echo("❌ Failed to detect follower arm. Skipping setup.")
        return config
    
    config['follower_port'] = follower_port
    
    # Setup motor IDs for follower arm
    typer.echo(f"\n🔧 Setting up motor IDs for follower arm...")
    follower_motors_setup = setup_motors_for_arm("follower", follower_port, robot_type)
    config['follower_motors_setup'] = follower_motors_setup
    
    if not follower_motors_setup:
        typer.echo("⚠️  Follower arm motor setup failed. Continuing with calibration anyway.")
    
    # Calibrate follower arm
    if calibrate_arm("follower", follower_port, robot_type):
        config['follower_calibrated'] = True
    else:
        typer.echo("❌ Follower arm calibration failed.")
        config['follower_calibrated'] = False
    
    return config 