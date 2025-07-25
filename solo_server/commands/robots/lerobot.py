"""
LeRobot framework handler for Solo Server
Handles LeRobot motor setup, calibration, teleoperation, data recording, and training
"""

import typer
from rich.console import Console
from rich.prompt import Confirm
from solo_server.utils.lerobot_utils import calibration, teleoperation, setup_motors_and_calibration, recording_mode, training_mode, inference_mode


console = Console()

def handle_lerobot(config: dict, calibrate: bool, teleop: bool, record: bool, train: bool, inference: bool = False):
    """Handle LeRobot framework operations"""
    # Check if lerobot is installed
    try:
        import lerobot
    except ImportError:
        typer.echo("❌ LeRobot package not found.")
        typer.echo("Please run 'solo setup' and select LeRobot as your server type first.")
        return
    
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
    elif calibrate:
        # Calibration mode - setup motors (optional) + calibrate
        calibration_mode(config)
    else:
        # Full mode - setup motors + calibrate + teleoperate
        setup_mode(config)

def teleop_mode(config: dict):
    """Handle LeRobot teleoperation mode"""
    from solo_server.utils.lerobot_utils import validate_lerobot_config, display_calibration_error, display_arms_status, teleoperation

    typer.echo("🎮 Starting LeRobot teleoperation mode...")
    
    # Validate configuration using utility function
    leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type = validate_lerobot_config(config)
    
    if leader_port and follower_port and leader_calibrated and follower_calibrated:
        display_arms_status(robot_type, leader_port, follower_port)

        # Always ask for camera setup during teleoperation
        camera_config = None  # Force camera setup prompt
        
        # Start teleoperation
        success = teleoperation(leader_port, follower_port, robot_type, camera_config)
        if success:
            typer.echo("✅ Teleoperation completed.")
        else:
            typer.echo("❌ Teleoperation failed.")
    else:
        display_calibration_error()

def calibration_mode(config: dict):
    """Handle LeRobot calibration mode"""
    typer.echo("🔧 Starting LeRobot calibration mode...")
    
    # Ask if user wants to setup motor IDs first
    setup_motors = Confirm.ask("Would you like to setup motor IDs first?", default=True)
    
    if setup_motors:
        # Use the complete motor setup and calibration function
        arm_config = setup_motors_and_calibration()
    else:
        # Run calibration only
        typer.echo("\n🔧 Starting arm calibration...")
        arm_config = calibration()
    
    # Save configuration using utility function
    from solo_server.utils.lerobot_utils import save_lerobot_config
    save_lerobot_config(config, arm_config)
    
    # Check calibration success using utility function
    from solo_server.utils.lerobot_utils import check_calibration_success
    check_calibration_success(arm_config, setup_motors)

def setup_mode(config: dict):
    """Handle LeRobot full setup mode"""
    typer.echo("🤖 Starting full LeRobot setup...")
    typer.echo("This will run: motor setup → calibration → teleoperation\n")
    
    # Step 1 & 2: Setup motors and calibration
    typer.echo("Step 1/3: Setting up motor IDs and calibration...")
    arm_config = setup_motors_and_calibration()
    
    # Save configuration using utility function  
    save_lerobot_config(config, arm_config)
    
    # Step 3: Teleoperation (if calibration successful)
    leader_configured = arm_config.get('leader_port') and arm_config.get('leader_calibrated')
    follower_configured = arm_config.get('follower_port') and arm_config.get('follower_calibrated')
    
    if leader_configured and follower_configured:
        # Report motor setup status
        leader_motors = arm_config.get('leader_motors_setup', False)
        follower_motors = arm_config.get('follower_motors_setup', False)
        if leader_motors and follower_motors:
            typer.echo("✅ Motor IDs set up successfully for both arms.")
        else:
            typer.echo("⚠️  Some motor setups may have failed, but calibration completed.")
        
        typer.echo("\nStep 3/3: Starting teleoperation...")
        robot_type = arm_config.get('robot_type', 'so100')
        leader_port = arm_config.get('leader_port')
        follower_port = arm_config.get('follower_port')
        
        # Get camera config from arm_config
        camera_config = arm_config.get('cameras', {'enabled': False, 'cameras': []})
        
        success = teleoperation(leader_port, follower_port, robot_type, camera_config)
        if success:
            typer.echo("🎉 Full LeRobot setup completed successfully!")
        else:
            typer.echo("⚠️  Setup completed but teleoperation failed.")
    else:
        typer.echo("\n⚠️  Calibration failed. Skipping teleoperation.")
        typer.echo("You can run 'solo robo --type lerobot --calibrate' to retry calibration.")  