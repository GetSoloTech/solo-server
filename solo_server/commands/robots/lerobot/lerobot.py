"""
LeRobot framework handler for Solo Server
Handles LeRobot motor setup, calibration, teleoperation, data recording, and training
"""

import typer
from rich.console import Console
from rich.prompt import Confirm
from solo_server.commands.robots.lerobot.calibration import calibration
from solo_server.commands.robots.lerobot.teleoperation import teleoperation
from solo_server.commands.robots.lerobot.config import save_lerobot_config
from solo_server.commands.robots.lerobot.calibration import check_calibration_success
from solo_server.commands.robots.lerobot.recording import recording_mode, training_mode, inference_mode


console = Console()

def handle_lerobot(config: dict, calibrate: str, motors: str, teleop: bool, record: bool, train: bool, inference: bool = False):
    """Handle LeRobot framework operations"""
    # LeRobot is now installed by default with solo-server
    import lerobot
    
    if train:
        # Training mode - train a policy on recorded data
        training_mode(config)
    elif record:
        # Recording mode - check for existing calibration and setup recording
        recording_mode(config)
    elif inference:
        # Inference mode - run pretrained policy on robot
        inference_mode(config)
    elif teleop:
        # Teleoperation mode - check for existing calibration
        teleop_mode(config)
    elif motors is not None:
        # Motor setup mode - setup motor IDs only
        motor_setup_mode(config, motors)
    elif calibrate is not None:
        # Calibration mode - calibrate only 
        calibration_mode(config, calibrate)

def teleop_mode(config: dict):
    """Handle LeRobot teleoperation mode"""
    from solo_server.commands.robots.lerobot.config import validate_lerobot_config
    from solo_server.commands.robots.lerobot.calibration import display_calibration_error, display_arms_status

    typer.echo("🎮 Starting LeRobot teleoperation mode...")
    
    # Validate configuration using utility function
    leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type = validate_lerobot_config(config)
    
    if leader_port and follower_port and leader_calibrated and follower_calibrated:
        # Always ask for camera setup during teleoperation
        camera_config = None  # Force camera setup prompt
        
        # Start teleoperation
        success = teleoperation(leader_port, follower_port, robot_type, camera_config, config)
        if success:
            typer.echo("✅ Teleoperation completed.")
        else:
            typer.echo("❌ Teleoperation failed.")
    else:
        display_calibration_error()

def calibration_mode(config: dict, arm_type: str = None):
    """Handle LeRobot calibration mode"""
    typer.echo("🔧 Starting LeRobot calibration mode...")
    
    arm_config = calibration(config, arm_type)
    save_lerobot_config(config, arm_config)
    
    # Check calibration success using utility function
    check_calibration_success(arm_config, False)  # Motors already set up

def motor_setup_mode(config: dict, arm_type: str = None):
    """Handle LeRobot motor setup mode"""
    typer.echo("🔧 Starting LeRobot motor setup mode...")
    
    from solo_server.commands.robots.lerobot.calibration import setup_motors_for_arm
    from solo_server.commands.robots.lerobot.ports import detect_arm_port
    from solo_server.commands.robots.lerobot.config import save_lerobot_config
    from rich.prompt import Prompt, Confirm
    
    # Gather any existing config and ask once to reuse
    lerobot_config = config.get('lerobot', {})
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
    
    motor_config = {'robot_type': robot_type}
    
    # Determine which arms to setup based on arm_type parameter
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
            typer.echo("❌ Failed to detect leader arm. Skipping leader setup.")
        else:
            motor_config['leader_port'] = leader_port
            # Save port to config immediately
            save_lerobot_config(config, {'leader_port': leader_port})
            
            # Setup motor IDs for leader arm
            leader_motors_setup = setup_motors_for_arm("leader", leader_port, robot_type)
            motor_config['leader_motors_setup'] = leader_motors_setup
            
            if leader_motors_setup:
                typer.echo("✅ Leader arm motor setup completed!")
            else:
                typer.echo("❌ Leader arm motor setup failed.")
    
    if setup_follower:
        # Use consolidated decision for follower port
        follower_port = existing_follower_port if reuse_all and existing_follower_port else None
        if not follower_port:
            follower_port = detect_arm_port("follower")
        
        if not follower_port:
            typer.echo("❌ Failed to detect follower arm. Skipping follower setup.")
        else:
            motor_config['follower_port'] = follower_port
            # Save port to config immediately
            save_lerobot_config(config, {'follower_port': follower_port})
            
            # Setup motor IDs for follower arm
            follower_motors_setup = setup_motors_for_arm("follower", follower_port, robot_type)
            motor_config['follower_motors_setup'] = follower_motors_setup
            
            if follower_motors_setup:
                typer.echo("✅ Follower arm motor setup completed!")
            else:
                typer.echo("❌ Follower arm motor setup failed.")
    
    # Save final motor configuration
    save_lerobot_config(config, motor_config)
    
    # Report final status
    leader_setup = motor_config.get('leader_motors_setup', False)
    follower_setup = motor_config.get('follower_motors_setup', False)
    
    if (setup_leader and leader_setup) or (setup_follower and follower_setup):
        typer.echo("\n🎉 Motor setup completed!")
        if leader_setup and follower_setup:
            typer.echo("✅ Motor IDs have been set up for both arms.")
        elif leader_setup:
            typer.echo("✅ Motor IDs have been set up for the leader arm.")
        elif follower_setup:
            typer.echo("✅ Motor IDs have been set up for the follower arm.")
        
        typer.echo("🔧 You can now run 'solo robo --type lerobot --calibrate' to calibrate the arms.")
    else:
        typer.echo("\n⚠️  Motor setup failed or was skipped.")
        typer.echo("You can run 'solo robo --type lerobot --motors' again to retry.")