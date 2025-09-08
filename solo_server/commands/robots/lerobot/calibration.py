"""
Calibration utilities for LeRobot
"""

import typer
from rich.prompt import Prompt, Confirm
from typing import Dict
from lerobot.calibrate import calibrate, CalibrateConfig
from lerobot.teleoperators import make_teleoperator_from_config
from lerobot.robots import make_robot_from_config
from solo_server.commands.robots.lerobot.ports import detect_arm_port
from solo_server.commands.robots.lerobot.config import get_robot_config_classes, save_lerobot_config


def calibrate_arm(arm_type: str, port: str, robot_type: str = "so100") -> bool:
    """
    Calibrate a specific arm using the lerobot calibration system
    """
    typer.echo(f"\n🔧 Calibrating {arm_type} arm on port {port}...")
    
    try:
        # Determine the appropriate config class based on arm type and robot type
        leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
        
        if leader_config_class is None or follower_config_class is None:
            typer.echo(f"❌ Unsupported robot type for {arm_type}: {robot_type}")
            return False

        if arm_type == "leader":
            arm_config = leader_config_class(port=port, id=f"{robot_type}_{arm_type}")
            calibrate_config = CalibrateConfig(teleop=arm_config)
        else:
            arm_config = follower_config_class(port=port, id=f"{robot_type}_{arm_type}")
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


def setup_motors_for_arm(arm_type: str, port: str, robot_type: str = "so100") -> bool:
    """
    Setup motor IDs for a specific arm (leader or follower)
    Returns True if successful, False otherwise
    """

    try:
        # Determine the appropriate config class based on arm type and robot type
        leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
        
        if leader_config_class is None or follower_config_class is None:
            typer.echo(f"❌ Unsupported robot type for {arm_type}: {robot_type}")
            return False

        if arm_type == "leader":
            config_class = leader_config_class
            make_device = make_teleoperator_from_config
        else:
            config_class = follower_config_class
            make_device = make_robot_from_config
        
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


def calibration(main_config: dict = None, arm_type: str = None) -> Dict:
    """
    Setup process for arm calibration with selective arm support
    Returns configuration dictionary with arm setup details
    """
    config = {}
    
    # Gather any existing config and ask once to reuse
    lerobot_config = main_config.get('lerobot', {}) if main_config else {}
    existing_robot_type = lerobot_config.get('robot_type')
    existing_leader_port = lerobot_config.get('leader_port')
    existing_follower_port = lerobot_config.get('follower_port')
    
    reuse_all = False
    if existing_robot_type or existing_leader_port or existing_follower_port:
        typer.echo("\n📦 Found existing configuration:")
        if existing_robot_type:
            typer.echo(f"   • Robot type: {existing_robot_type}")
        if existing_leader_port:
            typer.echo(f"   • Leader port: {existing_leader_port}")
        if existing_follower_port:
            typer.echo(f"   • Follower port: {existing_follower_port}")
        reuse_all = Confirm.ask("Use these settings?", default=True)
    
    if reuse_all and existing_robot_type:
        robot_type = existing_robot_type
    else:
        # Ask for robot type
        typer.echo("\n🤖 Select your robot type:")
        typer.echo("1. SO100")
        typer.echo("2. SO101")
        robot_choice = int(Prompt.ask("Enter robot type", default="1"))
        robot_type = "so100" if robot_choice == 1 else "so101"
    
    config['robot_type'] = robot_type
    
    # Determine which arms to calibrate based on arm_type parameter
    if arm_type == "leader":
        setup_leader = True
        setup_follower = False
    elif arm_type == "follower":
        setup_leader = False
        setup_follower = True
    else:
        # arm_type is None or empty, setup both
        setup_leader = True
        setup_follower = True
    
    if setup_leader:
        # Use consolidated decision for leader port
        leader_port = existing_leader_port if reuse_all and existing_leader_port else None
        if not leader_port:
            leader_port = detect_arm_port("leader")
        
        if not leader_port:
            typer.echo("❌ Failed to detect leader arm. Skipping leader calibration.")
        else:
            config['leader_port'] = leader_port
            
            # Calibrate leader arm
            if calibrate_arm("leader", leader_port, robot_type):
                config['leader_calibrated'] = True
            else:
                typer.echo("❌ Leader arm calibration failed.")
                config['leader_calibrated'] = False
    
    if setup_follower:
        # Use consolidated decision for follower port
        follower_port = existing_follower_port if reuse_all and existing_follower_port else None
        if not follower_port:
            follower_port = detect_arm_port("follower")
        
        if not follower_port:
            typer.echo("❌ Failed to detect follower arm. Skipping follower calibration.")
        else:
            config['follower_port'] = follower_port
            
            # Calibrate follower arm
            if calibrate_arm("follower", follower_port, robot_type):
                config['follower_calibrated'] = True
            else:
                typer.echo("❌ Follower arm calibration failed.")
                config['follower_calibrated'] = False
    
    return config


def setup_motors_and_calibration(main_config: dict = None) -> Dict:
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


def display_calibration_error():
    """Display standard calibration error message."""
    typer.echo("❌ Arms are not properly calibrated.")
    typer.echo("Please run the following commands in order:")
    typer.echo("   • 'solo robo --type lerobot --motors' - Setup motor IDs for both arms")
    typer.echo("   • 'solo robo --type lerobot --motors leader' - Setup motor IDs for leader arm only")
    typer.echo("   • 'solo robo --type lerobot --motors follower' - Setup motor IDs for follower arm only")
    typer.echo("   • 'solo robo --type lerobot --calibrate' - Calibrate both arms")
    typer.echo("   • 'solo robo --type lerobot --calibrate leader' - Calibrate leader arm only")
    typer.echo("   • 'solo robo --type lerobot --calibrate follower' - Calibrate follower arm only")
    typer.echo("   • 'solo robo --type lerobot --teleop' - Start teleoperation")


def display_arms_status(robot_type: str, leader_port: str, follower_port: str):
    """Display current arms configuration status."""
    typer.echo("✅ Found calibrated arms:")
    typer.echo(f"   • Robot type: {robot_type.upper()}")
    if leader_port:
        typer.echo(f"   • Leader arm: {leader_port}")
    if follower_port:
        typer.echo(f"   • Follower arm: {follower_port}")


def check_calibration_success(arm_config: dict, setup_motors: bool = False) -> None:
    """Check and report calibration success status with appropriate messages."""
    leader_configured = arm_config.get('leader_port') and arm_config.get('leader_calibrated')
    follower_configured = arm_config.get('follower_port') and arm_config.get('follower_calibrated')
    
    if leader_configured and follower_configured:
        typer.echo("🎉 Arms calibrated successfully!")
        
        if setup_motors:
            leader_motors = arm_config.get('leader_motors_setup', False)
            follower_motors = arm_config.get('follower_motors_setup', False)
            if leader_motors and follower_motors:
                typer.echo("✅ Motor IDs have been set up for both arms.")
            else:
                typer.echo("⚠️  Some motor setups may have failed, but calibration completed.")
        
        typer.echo("🎮 You can now run 'solo robo --type lerobot --teleop' to start teleoperation.")
    else:
        typer.echo("⚠️  Calibration partially completed.")
        typer.echo("You can run 'solo robo --type lerobot --calibrate' again to retry.")
