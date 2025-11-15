"""
LeRobot framework handler for Solo CLI
Handles LeRobot motor setup, calibration, teleoperation, data recording, and training
"""

import typer
from rich.console import Console


console = Console()

def handle_lerobot(config: dict, calibrate: str, motors: str, teleop: bool, record: bool, train: bool, inference: bool = False):
    """Handle LeRobot framework operations"""
    # Check LeRobot installation
    import lerobot
    
    if train:
        # Training mode - train a policy on recorded data
        from solo.commands.robots.lerobot.recording import training_mode
        training_mode(config)
    elif record:
        # Recording mode - check for existing calibration and setup recording
        from solo.commands.robots.lerobot.recording import recording_mode
        recording_mode(config)
    elif inference:
        # Inference mode - run pretrained policy on robot
        from solo.commands.robots.lerobot.recording import inference_mode
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
    # Lazy import - only load when teleop is actually used
    from solo.commands.robots.lerobot.teleoperation import teleoperation

    typer.echo("🎮 Starting LeRobot teleoperation mode...")
        
    # Start teleoperation
    success = teleoperation(config)
    if success:
        typer.echo("✅ Teleoperation completed.")
    else:
        typer.echo("❌ Teleoperation failed.")

def calibration_mode(config: dict, arm_type: str = None):
    """Handle LeRobot calibration mode"""
    # Lazy import - only load when calibration is actually used
    from solo.commands.robots.lerobot.calibration import calibration, check_calibration_success
    from solo.commands.robots.lerobot.config import save_lerobot_config
    
    typer.echo("🔧 Starting LeRobot calibration mode...")
    
    arm_config = calibration(config, arm_type)
    save_lerobot_config(config, arm_config)
    
    # Check calibration success using utility function
    check_calibration_success(arm_config, False)  # Motors already set up

def motor_setup_mode(config: dict, arm_type: str = None):
    """Handle LeRobot motor setup mode"""
    from solo.commands.robots.lerobot.calibration import setup_motors_for_arm
    from solo.commands.robots.lerobot.ports import detect_arm_port
    from solo.commands.robots.lerobot.config import save_lerobot_config
    from rich.prompt import Prompt, Confirm
    
    typer.echo("🔧 Starting LeRobot motor setup mode...")

    if arm_type is not None and arm_type not in ["leader", "follower", "all"]:
        raise ValueError(f"Invalid arm type: {arm_type}, please use 'leader', 'follower', or 'all'")
    
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
        # Only show relevant port(s) based on arm_type
        if arm_type == "leader" and existing_leader_port:
            typer.echo(f"   • Leader port: {existing_leader_port}")
        elif arm_type == "follower" and existing_follower_port:
            typer.echo(f"   • Follower port: {existing_follower_port}")
        elif arm_type not in ["leader", "follower"]:
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
        # arm_type is "all", setup both arms
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
        
        typer.echo("🔧 You can now run 'solo robo --calibrate all' to calibrate the arms.")
    else:
        typer.echo("\n⚠️  Motor setup failed or was skipped.")
        typer.echo("You can run 'solo robo --motors all' again to retry.")