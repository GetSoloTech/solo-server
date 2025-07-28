"""
LeRobot utilities for Solo Server
Handles port detection, calibration, teleoperation setup, and data recording
"""

import json
import os
import time
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
import typer
from solo_server.config import CONFIG_PATH

console = Console()

# Import lerobot modules with error handling
try:
    from lerobot.calibrate import calibrate, CalibrateConfig
    from lerobot.teleoperate import teleoperate, TeleoperateConfig
    from lerobot.teleoperators.so100_leader import SO100LeaderConfig
    from lerobot.teleoperators.so101_leader import SO101LeaderConfig
    from lerobot.robots.so100_follower import SO100FollowerConfig
    from lerobot.robots.so101_follower import SO101FollowerConfig
    from lerobot.teleoperators import make_teleoperator_from_config
    from lerobot.robots import make_robot_from_config
    from lerobot.cameras.opencv.camera_opencv import OpenCVCamera
    from lerobot.cameras.realsense.camera_realsense import RealSenseCamera
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
    LEROBOT_AVAILABLE = True
    CAMERAS_AVAILABLE = True
except ImportError:
    # Set to None if lerobot is not available
    (calibrate, CalibrateConfig, teleoperate, TeleoperateConfig, SO100LeaderConfig, SO101LeaderConfig,
     SO100FollowerConfig, SO101FollowerConfig, make_teleoperator_from_config, make_robot_from_config,
     OpenCVCamera, RealSenseCamera, OpenCVCameraConfig, RealSenseCameraConfig) = [None] * 14
    LEROBOT_AVAILABLE = False
    CAMERAS_AVAILABLE = False


def validate_lerobot_config(config: dict) -> tuple[Optional[str], Optional[str], bool, bool, str]:
    """
    Extract and validate lerobot configuration from main config.
    Returns: (leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type)
    """
    lerobot_config = config.get('lerobot', {})
    leader_port = lerobot_config.get('leader_port')
    follower_port = lerobot_config.get('follower_port')
    leader_calibrated = lerobot_config.get('leader_calibrated', False)
    follower_calibrated = lerobot_config.get('follower_calibrated', False)
    robot_type = lerobot_config.get('robot_type', 'so100')
    
    return leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type

def display_calibration_error():
    """Display standard calibration error message."""
    typer.echo("❌ Arms are not properly calibrated.")
    typer.echo("Please run one of the following first:")
    typer.echo("   • 'solo robo --type lerobot --calibrate' - Configure arms only")
    typer.echo("   • 'solo robo --type lerobot' - Full setup (motors + calibration + teleoperation)")

def display_arms_status(robot_type: str, leader_port: Optional[str], follower_port: Optional[str]):
    """Display current arms configuration status."""
    typer.echo("✅ Found calibrated arms:")
    typer.echo(f"   • Robot type: {robot_type.upper()}")
    if leader_port:
        typer.echo(f"   • Leader arm: {leader_port}")
    if follower_port:
        typer.echo(f"   • Follower arm: {follower_port}")

def save_lerobot_config(config: dict, arm_config: dict) -> None:
    """Save lerobot configuration to config file."""
    if 'lerobot' not in config:
        config['lerobot'] = {}
    config['lerobot'].update(arm_config)
    
    # Update server type
    if 'server' not in config:
        config['server'] = {}
    config['server']['type'] = 'lerobot'
    
    # Save to file
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    
    typer.echo(f"\n✅ Configuration saved to {CONFIG_PATH}")

def create_robot_configs(robot_type: str, leader_port: str, follower_port: str, 
                        camera_config: Dict) -> tuple[Optional[object], Optional[object]]:
    """
    Create leader and follower configurations for given robot type.
    Returns: (leader_config, follower_config)
    """
    leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
    
    if leader_config_class is None or follower_config_class is None:
        typer.echo(f"❌ Unsupported robot type: {robot_type}")
        return None, None
    
    leader_config = leader_config_class(port=leader_port, id=f"{robot_type}_leader")
    follower_config = create_follower_config(follower_config_class, follower_port, robot_type, camera_config)
    
    return leader_config, follower_config

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

def get_robot_config_classes(robot_type: str) -> Tuple[Optional[type], Optional[type]]:
    """
    Get the appropriate config classes for leader and follower based on robot type
    Returns (leader_config_class, follower_config_class)
    """
    if robot_type == "so100":
        return SO100LeaderConfig, SO100FollowerConfig
    elif robot_type == "so101":
        return SO101LeaderConfig, SO101FollowerConfig
    else:
        return None, None

def build_camera_configuration(camera_config: Dict) -> Dict:
    """
    Build camera configuration dictionary from camera_config
    Returns cameras_dict for robot configuration
    """
    if not camera_config.get('enabled', False):
        return {}
    
    # Import camera configuration classes
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
    
    cameras_dict = {}
    for cam in camera_config.get('cameras', []):
        camera_name = cam['angle']  # Use angle as camera name
        cam_info = cam['camera_info']
        
        # Create camera config based on type
        if cam['camera_type'] == 'OpenCV':
            stream_profile = cam_info.get('default_stream_profile') or {}
            cameras_dict[camera_name] = OpenCVCameraConfig(
                index_or_path=cam_info.get('id', 0),
                width=stream_profile.get('width', 640),
                height=stream_profile.get('height', 480),
                fps=stream_profile.get('fps', 30)
            )
        elif cam['camera_type'] == 'RealSense':
            stream_profile = cam_info.get('default_stream_profile') or {}
            cameras_dict[camera_name] = RealSenseCameraConfig(
                serial_number_or_name=str(cam_info.get('id', '')),
                width=stream_profile.get('width', 640),
                height=stream_profile.get('height', 480),
                fps=stream_profile.get('fps', 30)
            )
    
    return cameras_dict

def create_follower_config(follower_config_class, follower_port: str, robot_type: str, camera_config: Dict):
    """
    Create follower configuration with optional camera support
    """
    cameras_dict = build_camera_configuration(camera_config)
    
    if cameras_dict:
        return follower_config_class(
            port=follower_port, 
            id=f"{robot_type}_follower",
            cameras=cameras_dict
        )
    else:
        return follower_config_class(port=follower_port, id=f"{robot_type}_follower")

def check_dataset_exists(repo_id: str, root: Optional[str] = None) -> bool:
    """
    Check if a dataset already exists by looking for the dataset directory
    """
    try:
        if root is not None:
            dataset_path = Path(root)
        else:
            # Import
            from lerobot.constants import HF_LEROBOT_HOME
            dataset_path = HF_LEROBOT_HOME / repo_id
        
        return dataset_path.exists() and dataset_path.is_dir()
    except ImportError:
        # If we can't import lerobot constants, fall back to checking standard cache location
        from pathlib import Path
        import os
        
        cache_home = Path(os.getenv("HF_HOME", "~/.cache/huggingface")).expanduser()
        dataset_path = cache_home / "lerobot" / repo_id
        return dataset_path.exists() and dataset_path.is_dir()

def handle_existing_dataset(repo_id: str, root: Optional[str] = None) -> Tuple[str, bool]:
    """
    Handle the case when a dataset already exists
    Returns (final_repo_id, should_resume)
    """
    while True:
        if not check_dataset_exists(repo_id, root):
            # Dataset doesn't exist, we can proceed with creation
            return repo_id, False
        
        # Dataset exists, ask user what to do
        typer.echo(f"\n⚠️  Dataset already exists: {repo_id}")
        
        choice = Confirm.ask("Resume recording?", default=True)
        
        if choice:
            # User wants to resume
            return repo_id, True
        else:
            # User wants a different name
            typer.echo(f"\nCurrent repository: {repo_id}")
            repo_id = Prompt.ask("Enter a new repository ID", default=repo_id)

def check_huggingface_login() -> tuple[bool, str]:
    """
    Check if user is logged in to HuggingFace and return (is_logged_in, username)
    """
    try:
        # Check if user is logged in by running huggingface-cli whoami
        result = subprocess.run(
            ["huggingface-cli", "whoami"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip().split('\n')[0]
            # Check if output contains an actual username (not error messages)
            if output and not any(phrase in output.lower() for phrase in ['not logged in', 'error', 'failed', 'invalid']):
                return True, output
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
        
        result = subprocess.run(["huggingface-cli", "login"], check=False)
        
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

# ========== UNIFIED RECORD CONFIGURATION ==========

def unified_record_config(
    robot_type: str, 
    leader_port: str, 
    follower_port: str, 
    camera_config: Dict,
    mode: str = "inference",  # "inference" or "recording"
    **mode_specific_kwargs
) -> 'RecordConfig':
    """
    Create a unified record configuration for both inference and recording modes.
    Uses the same underlying lerobot record infrastructure.
    """
    # Import lerobot components
    from lerobot.record import RecordConfig, DatasetRecordConfig
    from lerobot.configs.policies import PreTrainedConfig
    
    # Create robot configurations
    leader_config, follower_config = create_robot_configs(robot_type, leader_port, follower_port, camera_config)
    
    if follower_config is None:
        raise ValueError(f"Failed to create robot configuration for {robot_type}")
    
    # Configure based on mode
    if mode == "recording":
        # Recording mode - create full dataset configuration
        dataset_config = DatasetRecordConfig(
            repo_id=mode_specific_kwargs.get('dataset_repo_id', 'default/dataset'),
            single_task=mode_specific_kwargs.get('task_description', ''),
            episode_time_s=mode_specific_kwargs.get('episode_time', 60),
            num_episodes=mode_specific_kwargs.get('num_episodes', 50),
            push_to_hub=mode_specific_kwargs.get('push_to_hub', True),
            fps=mode_specific_kwargs.get('fps', 30),
            video=True,
        )
        
        record_config = RecordConfig(
            robot=follower_config,
            teleop=leader_config,
            dataset=dataset_config,
            display_data=True,
            play_sounds=True,
            resume=mode_specific_kwargs.get('should_resume', False),
        )
    
    elif mode == "inference":
        # Inference mode - create minimal configuration with policy
        policy_path = mode_specific_kwargs.get('policy_path')
        if not policy_path:
            raise ValueError("Policy path is required for inference mode")
        
        # Load policy configuration
        policy_config = PreTrainedConfig.from_pretrained(
            policy_path,
            cache_dir=mode_specific_kwargs.get('cache_dir'),
            local_files_only=False,
            force_download=False
        )
        policy_config.pretrained_path = policy_path
        
        # Create minimal dataset config for inference (not for recording)
        dataset_config = DatasetRecordConfig(
            repo_id="inference/session",  # Dummy repo_id 
            single_task=mode_specific_kwargs.get('task_description', ''),
            episode_time_s=mode_specific_kwargs.get('inference_time', 60),
            num_episodes=1,  # Single inference session
            push_to_hub=False,  # Never push inference sessions
            fps=mode_specific_kwargs.get('fps', 30),
            video=False,  # No video for inference
        )
        
        record_config = RecordConfig(
            robot=follower_config,
            teleop=leader_config if mode_specific_kwargs.get('use_teleoperation', False) else None,
            dataset=None,  # No dataset for pure inference
            policy=policy_config,
            display_data=True,
            play_sounds=False,  # Quieter for inference
            resume=False,
        )
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Must be 'inference' or 'recording'")
    
    return record_config

def recording_mode(config: dict):
    """Handle LeRobot recording mode"""
    typer.echo("🎬 Starting LeRobot recording mode...")
    
    # Validate configuration using utility function
    leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type = validate_lerobot_config(config)
    
    if not (leader_port and follower_port and leader_calibrated and follower_calibrated):
        display_calibration_error()
        return
    
    display_arms_status(robot_type, leader_port, follower_port)
    
    # Step 1: HuggingFace authentication
    typer.echo("\n📋 Step 1: HuggingFace Authentication")
    login_success, hf_username = authenticate_huggingface()
    
    if not login_success:
        typer.echo("❌ Cannot proceed with recording without HuggingFace authentication.")
        return
    
    # Step 2: Ask about pushing to hub
    typer.echo(f"\n📤 Step 2: Dataset Upload Configuration")
    typer.echo(f"HuggingFace username: {hf_username}")
    push_to_hub = Confirm.ask("Would you like to push the recorded data to HuggingFace Hub?", default=True)
    
    # Step 3: Get recording parameters
    typer.echo("\n⚙️  Step 3: Recording Configuration")
    
    # Get dataset name and handle existing datasets
    dataset_name = Prompt.ask("Enter dataset repository name", default="lerobot-dataset")
    initial_repo_id = f"{hf_username}/{dataset_name}"
    
    # Check if dataset exists and handle appropriately
    dataset_repo_id, should_resume = handle_existing_dataset(initial_repo_id)
    
    # Get task description
    task_description = Prompt.ask("Enter task description (e.g., 'Pick up the red cube and place it in the box')")
    
    # Get episode time
    episode_time = float(Prompt.ask("Duration of each recording episode in seconds", default="60"))
    
    # Get number of episodes
    num_episodes = int(Prompt.ask("Total number of episodes to record", default="50"))
    
    # Step 4: Start recording
    typer.echo("\n🎬 Step 4: Starting Data Recording")
    typer.echo("Configuration:")
    typer.echo(f"   • Dataset: {dataset_repo_id}")
    typer.echo(f"   • Task: {task_description}")
    typer.echo(f"   • Episode duration: {episode_time}s")
    typer.echo(f"   • Number of episodes: {num_episodes}")
    typer.echo(f"   • Push to hub: {push_to_hub}")
    typer.echo(f"   • Robot type: {robot_type.upper()}")
    
    # Import lerobot recording components
    try:
        from lerobot.record import record
    except ImportError as e:
        typer.echo(f"❌ Error importing lerobot recording components: {e}")
        return
    
    try:
        # Setup cameras
        camera_config = setup_cameras()
        
        # Create unified record configuration for recording mode
        record_config = unified_record_config(
            robot_type=robot_type,
            leader_port=leader_port,
            follower_port=follower_port,
            camera_config=camera_config,
            mode="recording",
            dataset_repo_id=dataset_repo_id,
            task_description=task_description,
            episode_time=episode_time,
            num_episodes=num_episodes,
            push_to_hub=push_to_hub,
            fps=30,
            should_resume=should_resume,
        )
        
        mode_text = "Resuming" if should_resume else "Starting"
        typer.echo(f"🎬 {mode_text} recording... Follow the on-screen instructions.")
        
        if should_resume:
            typer.echo("📝 Note: Recording will continue from existing dataset")
        
        typer.echo("💡 Tips:")
        typer.echo("   • Move the leader arm to control the follower")
        typer.echo("   • Press 'q' to stop current episode")
        typer.echo("   • Press 's' to stop recording completely")
        typer.echo("   • Press 'r' to re-record current episode")
        
        # Start recording
        dataset = record(record_config)
        
        mode_text = "resumed and completed" if should_resume else "completed"
        typer.echo(f"✅ Recording {mode_text}!")
        typer.echo(f"📊 Dataset: {dataset_repo_id}")
        typer.echo(f"📈 Total episodes in dataset: {dataset.num_episodes}")
        
        if push_to_hub:
            typer.echo(f"🚀 Dataset pushed to HuggingFace Hub: https://huggingface.co/datasets/{dataset_repo_id}")
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Recording stopped by user.")
    except Exception as e:
        error_msg = str(e)
        if "Cannot create a file when that file already exists" in error_msg:
            typer.echo(f"❌ Dataset already exists: {dataset_repo_id}")
            typer.echo("Please try running the command again.")
        else:
            typer.echo(f"❌ Recording failed: {e}")
            typer.echo("Please check your robot connections and try again.")

def inference_mode(config: dict):
    """Handle LeRobot inference mode"""
    typer.echo("🔮 Starting LeRobot inference mode...")
    
    # Validate configuration using utility function
    leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type = validate_lerobot_config(config)
    
    if not (follower_port and follower_calibrated):
        typer.echo("❌ Follower arm is not properly calibrated.")
        display_calibration_error()
        return
    
    typer.echo("✅ Found calibrated follower arm:")
    typer.echo(f"   • Robot type: {robot_type.upper()}")
    typer.echo(f"   • Follower arm: {follower_port}")
    
    # Check if leader arm is available for teleoperation
    use_teleoperation = False
    if leader_port and leader_calibrated:
        typer.echo(f"✅ Leader arm also available: {leader_port}")
        use_teleoperation = Confirm.ask("Would you like to teleoperate during inference?", default=False)
        if use_teleoperation:
            typer.echo("🎮 Teleoperation enabled - you can override the policy using the leader arm")
        else:
            typer.echo("🤖 Pure autonomous inference mode - policy will run without teleoperation")
    else:
        typer.echo("ℹ️  No leader arm available - running in pure autonomous mode")
    
    # Step 1: HuggingFace authentication
    typer.echo("\n📋 Step 1: HuggingFace Authentication")
    login_success, hf_username = authenticate_huggingface()
    
    if not login_success:
        typer.echo("❌ Cannot proceed with inference without HuggingFace authentication.")
        typer.echo("💡 HuggingFace authentication is required to download pre-trained models.")
        return
    
    # Step 2: Get policy path
    typer.echo("\n🤖 Step 2: Policy Configuration")
    policy_path = Prompt.ask("Enter policy path (HuggingFace model ID or local path)")
    
    # Step 3: Inference configuration
    typer.echo("\n⚙️ Step 3: Inference Configuration")
    
    # Get inference duration
    inference_time = float(Prompt.ask("Duration of inference session in seconds", default="60"))
    
    # Get task description (optional for some policies)
    task_description = Prompt.ask("Enter task description", default="")
    
    # Import lerobot inference components
    try:
        from lerobot.record import record
        import os
    except ImportError as e:
        typer.echo(f"❌ Error importing lerobot inference components: {e}")
        return
    
    try:
        # Setup cameras
        camera_config = setup_cameras()

        # Set up Windows-specific environment variables for HuggingFace Hub
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        typer.echo(f"📥 Loading model: {policy_path}")

        # Step 4: Start inference
        typer.echo("\n🔮 Step 4: Starting Inference")
        typer.echo("Configuration:")
        typer.echo(f"   • Policy: {policy_path}")
        typer.echo(f"   • Inference duration: {inference_time}s")
        typer.echo(f"   • Task: {task_description or 'Not specified'}")
        typer.echo(f"   • Robot type: {robot_type.upper()}")
        typer.echo(f"   • Teleoperation: {'Enabled' if use_teleoperation else 'Disabled'}")
        
        # Create unified record configuration for inference mode
        record_config = unified_record_config(
            robot_type=robot_type,
            leader_port=leader_port,
            follower_port=follower_port,
            camera_config=camera_config,
            mode="inference",
            policy_path=policy_path,
            task_description=task_description,
            inference_time=inference_time,
            fps=30,
            use_teleoperation=use_teleoperation,
        )
        
        typer.echo("✅ Policy and robot configuration loaded successfully!")
        typer.echo("🔮 Starting inference... Follow the robot's movements.")
        typer.echo("💡 Tips:")
        if use_teleoperation:
            typer.echo("   • The robot will execute the policy autonomously")
            typer.echo("   • Move the leader arm to override the policy")
            typer.echo("   • Release the leader arm to let the policy take control")
        else:
            typer.echo("   • The robot will execute the policy autonomously")
        typer.echo("   • Press 'q' to stop inference")
        typer.echo("   • Press 'Ctrl+C' to force stop")
        
        # Start inference using unified record function (without dataset)
        record(record_config)
        
        typer.echo("\n✅ Inference completed successfully!")
        
    except PermissionError as e:
        typer.echo(f"❌ Permission error loading policy: {e}")
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Inference stopped by user.")
    except Exception as e:
        typer.echo(f"❌ Inference failed: {e}")
        typer.echo("💡 Troubleshooting tips:")
        typer.echo("   • Check if the model path is correct")
        typer.echo("   • Ensure you have internet connection for HuggingFace models")
        typer.echo("   • Verify HuggingFace authentication is working")
        typer.echo("   • For local paths, ensure the file exists and is accessible")

def training_mode(config: dict):
    """Handle LeRobot training mode"""
    typer.echo("🎓 Starting LeRobot training mode...")
    
    dataset_repo_id = Prompt.ask("Enter dataset repository ID", default="lerobot/svla_so101_pickplace")
    
    # Check if dataset exists locally
    if check_dataset_exists(dataset_repo_id):
        typer.echo(f"✅ Found local dataset: {dataset_repo_id}")
    
    typer.echo("Select policy type:")
    typer.echo("1. SmolVLA (Vision-Language-Action model)")
    typer.echo("2. ACT (Action Chunking with Transformers)")
    typer.echo("3. PI0 (Policy Iteration Zero)")
    typer.echo("4. TDMPC (Temporal Difference MPC)")
    typer.echo("5. Diffusion Policy (good for most tasks)")
    
    policy_choice = Prompt.ask("Enter policy type", default="1")
    policy_name_map = {
        "1": "smolvla",
        "2": "act", 
        "3": "pi0",
        "4": "tdmpc",
        "5": "diffusion"
    }
    policy_name = policy_name_map[policy_choice]
    
    # Step 2: Training configuration
    typer.echo(f"\n⚙️ Step 2: Training Configuration")
    
    # Get training parameters
    training_steps = int(Prompt.ask("Number of training steps", default="20000"))
    batch_size = int(Prompt.ask("Batch size", default="8"))
    
    # Output directory with conflict resolution
    default_output_dir = f"outputs/train/{dataset_repo_id.replace('/', '_')}_{policy_name}"
    output_dir = Prompt.ask("Output directory for checkpoints", default=default_output_dir)
    
    # Check if output directory exists and handle conflicts
    output_path = Path(output_dir)
    resume_training = False
    
    if output_path.exists() and output_path.is_dir():
        typer.echo(f"\n⚠️  Output directory already exists: {output_dir}")
        
        # Check if there are checkpoints (indicating a previous training run)
        checkpoint_files = list(output_path.glob("**/*checkpoint*")) + list(output_path.glob("**/*.pt"))
        has_checkpoints = len(checkpoint_files) > 0
        
        if has_checkpoints:
            typer.echo("📁 Found existing checkpoints in directory.")
            choice = Prompt.ask(
                "What would you like to do?",
                choices=["resume", "overwrite", "new_dir"],
                default="resume"
            )
        else:
            typer.echo("📁 Directory exists.")
            choice = Prompt.ask(
                "What would you like to do?", 
                choices=["overwrite", "new_dir"],
                default="overwrite"
            )
        
        if choice == "resume":
            resume_training = True
            typer.echo("🔄 Will resume training from existing checkpoints")
        elif choice == "overwrite":
            import shutil
            shutil.rmtree(output_path)
            typer.echo("🗑️  Removed existing directory")
        elif choice == "new_dir":
            # Generate a unique directory name
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"{output_dir}_{timestamp}"
            output_path = Path(output_dir)  # Update output_path too
            typer.echo(f"📁 Using new directory: {output_dir}")
    else:
        typer.echo(f"✅ Directory ready: {output_dir}")
    
    # Step 3: Hub pushing configuration
    typer.echo(f"\n🚀 Step 3: HuggingFace Hub Configuration")
    push_to_hub = Confirm.ask("Push trained model to HuggingFace Hub?", default=True)
    policy_repo_id = ""
    hf_username = ""
    
    if push_to_hub:
        # HuggingFace authentication for hub pushing
        typer.echo("\n🔐 HuggingFace Authentication for Model Upload")
        login_success, hf_username = authenticate_huggingface()
        
        if not login_success:
            typer.echo("❌ Cannot push to hub without HuggingFace authentication.")
            push_to_hub = False
        else:
            # Get policy repository ID
            policy_name_clean = policy_name.replace("_", "-")
            dataset_name_clean = dataset_repo_id.split("/")[-1].replace("_", "-")
            default_policy_repo = f"{hf_username}/{policy_name_clean}-{dataset_name_clean}"
            
            policy_repo_id = Prompt.ask("Enter policy repo id", default=default_policy_repo)
    
    # Step 4: WandB logging configuration
    typer.echo(f"\n📊 Step 4: Weights & Biases Configuration")
    use_wandb = Confirm.ask("Enable Weights & Biases logging?", default=True)
    wandb_project = ""
    if use_wandb:
        # Login to wandb first
        typer.echo("🔐 Logging into Weights & Biases...")
        try:
            result = subprocess.run(["wandb", "login"], check=False)
            if result.returncode != 0:
                typer.echo("❌ WandB login failed. Continuing without WandB logging.")
                use_wandb = False
            else:
                typer.echo("✅ Successfully logged into WandB")
                wandb_project = Prompt.ask("WandB project name", default="lerobot-training")
        except FileNotFoundError:
            typer.echo("❌ wandb CLI not found. Please install with: pip install wandb")
            typer.echo("Continuing without WandB logging.")
            use_wandb = False
        except Exception as e:
            typer.echo(f"❌ Error during WandB login: {e}")
            typer.echo("Continuing without WandB logging.")
            use_wandb = False
    
    # Step 5: Start training
    typer.echo(f"\n🎓 Step 5: Starting Training")
    typer.echo("Configuration:")
    typer.echo(f"   • Dataset: {dataset_repo_id}")
    typer.echo(f"   • Policy: {policy_name}")
    typer.echo(f"   • Training steps: {training_steps}")
    typer.echo(f"   • Batch size: {batch_size}")
    typer.echo(f"   • Output directory: {output_dir}")
    typer.echo(f"   • Resume training: {resume_training}")
    typer.echo(f"   • Push to Hub: {push_to_hub}")
    if push_to_hub:
        typer.echo(f"   • Policy repository: {policy_repo_id}")
    typer.echo(f"   • WandB logging: {use_wandb}")
    if use_wandb:
        typer.echo(f"   • WandB project: {wandb_project}")
    

    # Import lerobot training components
    try:
        from lerobot.scripts.train import train
        from lerobot.configs.train import TrainPipelineConfig
        from lerobot.configs.default import DatasetConfig, WandBConfig
        from lerobot.policies.diffusion.configuration_diffusion import DiffusionConfig
        from lerobot.policies.act.configuration_act import ACTConfig
        from lerobot.policies.tdmpc.configuration_tdmpc import TDMPCConfig
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.pi0.configuration_pi0 import PI0Config
    except ImportError as e:
        typer.echo(f"❌ Error importing lerobot training components: {e}")
        return
    
    try:
        # Create output directory only if resuming (LeRobot will create it otherwise)
        if resume_training:
            output_path.mkdir(parents=True, exist_ok=True)
        
        # Create dataset config
        dataset_config = DatasetConfig(repo_id=dataset_repo_id)
        
        # Create policy config based on choice
        if policy_name == "diffusion":
            policy_config = DiffusionConfig()
        elif policy_name == "act":
            policy_config = ACTConfig()
        elif policy_name == "tdmpc":
            policy_config = TDMPCConfig()
        elif policy_name == "smolvla":
            policy_config = SmolVLAConfig()
        elif policy_name == "pi0":
            policy_config = PI0Config()
        else:
            raise ValueError(f"Unknown policy type: {policy_name}")
        
        # Set repo_id for hub pushing if configured
        if policy_repo_id:
            # Add repo_id as an attribute to the policy config
            policy_config.repo_id = policy_repo_id
        policy_config.push_to_hub = push_to_hub
        
        # Create WandB config
        wandb_config = WandBConfig(
            enable=use_wandb,
            project=wandb_project if use_wandb else None
        )
        
        # Create training config
        train_config = TrainPipelineConfig(
            dataset=dataset_config,
            policy=policy_config,
            output_dir=output_path,
            steps=training_steps,
            batch_size=batch_size,
            save_freq=10000,  # Save checkpoints regularly
            wandb=wandb_config,
            seed=1000,
            resume=resume_training,  # Use the resume flag we determined above
        )
        
        typer.echo("🎓 Starting training... This may take a while.")
        typer.echo("💡 Tips:")
        typer.echo("   • Training progress will be logged to the console")
        if use_wandb:
            typer.echo(f"   • Monitor progress at https://wandb.ai/{wandb_project}")
        typer.echo("   • Checkpoints will be saved to the output directory")
        typer.echo("   • Press Ctrl+C to stop training early")
        
        # Start training
        train(train_config)
        
        typer.echo(f"✅ Training completed!")
        typer.echo(f"📊 Dataset: {dataset_repo_id}")
        typer.echo(f"🤖 Policy: {policy_name}")
        typer.echo(f"💾 Checkpoints saved to: {output_dir}")
        
        if push_to_hub and policy_repo_id:
            typer.echo(f"🚀 Model pushed to HuggingFace Hub: https://huggingface.co/{policy_repo_id}")
        
        if use_wandb:
            typer.echo(f"📈 Training logs: https://wandb.ai/{wandb_project}")
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Training stopped by user.")
        typer.echo("💾 Partial checkpoints may have been saved to the output directory.")
    except Exception as e:
        import traceback
        typer.echo(f"❌ Training failed: {e}")
        typer.echo("\n🔍 Full error traceback:")
        typer.echo(traceback.format_exc())
        typer.echo("Please check your dataset and configuration.")

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

def teleoperation(leader_port: str, follower_port: str, robot_type: str = "so100", camera_config: Dict = None) -> bool:
    """
    Start teleoperation between leader and follower arms with optional camera support
    """
    typer.echo(f"\n🎮 Starting teleoperation...")
    typer.echo(f"Leader arm port: {leader_port}")
    typer.echo(f"Follower arm port: {follower_port}")
    
    if not LEROBOT_AVAILABLE:
        typer.echo("❌ LeRobot modules are not available.")
        typer.echo("Please ensure lerobot is properly installed.")
        return False
    
    # Setup cameras if not provided
    if camera_config is None:
        use_camera = Confirm.ask("Would you like to setup cameras?", default=True)
        if use_camera:
            camera_config = setup_cameras()
    
    try:
        # Determine config classes based on robot type
        leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
        
        if leader_config_class is None or follower_config_class is None:
            typer.echo(f"❌ Unsupported robot type for teleoperation: {robot_type}")
            return False
        
        # Create configurations
        leader_config = leader_config_class(port=leader_port, id=f"{robot_type}_leader")
        
        # Create robot config with cameras if enabled
        follower_config = create_follower_config(follower_config_class, follower_port, robot_type, camera_config)
        
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

def calibration() -> Dict:
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

def find_cameras_by_type(camera_class, camera_type_name: str) -> List[Dict]:
    """Find cameras of a specific type and handle errors gracefully."""
    try:
        typer.echo(f"🔍 Searching for {camera_type_name} cameras...")
        
        # Special handling for RealSense cameras
        if camera_type_name == "RealSense":
            try:
                import pyrealsense2 as rs
                cameras = camera_class.find_cameras()
            except ImportError:
                typer.echo(f"⚠️  pyrealsense2 library not installed, skipping RealSense camera search")
                return []
            except Exception as rs_error:
                typer.echo(f"⚠️  RealSense library error: {rs_error}")
                return []
        elif camera_type_name == "OpenCV":
            # Special handling for OpenCV cameras to reduce errors
            try:
                # Suppress OpenCV error messages temporarily
                import cv2
                cv2.setLogLevel(0)  # Suppress OpenCV logs
                
                cameras = camera_class.find_cameras()
                
                # Restore normal logging
                cv2.setLogLevel(2)
            except Exception as opencv_error:
                typer.echo(f"⚠️  OpenCV camera error: {opencv_error}")
                return []
        else:
            cameras = camera_class.find_cameras()
            
        typer.echo(f"✅ Found {len(cameras)} {camera_type_name} cameras")
        return cameras
    except ImportError:
        typer.echo(f"⚠️  {camera_type_name} library not available, skipping {camera_type_name} camera search")
        return []
    except Exception as e:
        typer.echo(f"⚠️  Error finding {camera_type_name} cameras: {e}")
        return []

def find_available_cameras() -> List[Dict]:
    """
    Find all available cameras (OpenCV and RealSense)
    Returns list of camera information dictionaries
    """
    if not CAMERAS_AVAILABLE:
        typer.echo("❌ Camera modules are not available.")
        return []
    
    all_cameras = []
    
    # Find OpenCV cameras
    opencv_cameras = find_cameras_by_type(OpenCVCamera, "OpenCV")
    all_cameras.extend(opencv_cameras)
    
    # Find RealSense cameras
    realsense_cameras = find_cameras_by_type(RealSenseCamera, "RealSense")
    all_cameras.extend(realsense_cameras)
    
    return all_cameras

def display_cameras(cameras: List[Dict]) -> None:
    """Display available cameras in a formatted way"""
    if not cameras:
        typer.echo("❌ No cameras detected")
        return
    
    typer.echo("\n📷 Available Cameras:")
    typer.echo("=" * 50)
    
    for i, cam_info in enumerate(cameras):
        typer.echo(f"\nCamera #{i}:")
        typer.echo(f"  Type: {cam_info.get('type', 'Unknown')}")
        typer.echo(f"  ID: {cam_info.get('id', 'Unknown')}")
        
        # Display additional camera info
        if 'product_name' in cam_info:
            typer.echo(f"  Product: {cam_info['product_name']}")
        if 'serial_number' in cam_info:
            typer.echo(f"  Serial: {cam_info['serial_number']}")
        
        # Display stream profile if available
        if 'default_stream_profile' in cam_info:
            profile = cam_info['default_stream_profile']
            typer.echo(f"  Resolution: {profile.get('width', '?')}x{profile.get('height', '?')}")
            typer.echo(f"  FPS: {profile.get('fps', '?')}")
        
        typer.echo("-" * 30)

def setup_camera_mapping(cameras: List[Dict]) -> Dict:
    """
    Setup camera angle mapping and selection for teleoperation
    Returns configuration with selected cameras and their angles
    """
    if not cameras:
        return {}
    
    display_cameras(cameras)
    
    # Handle single camera case 
    if len(cameras) == 1:
        cam_info = cameras[0]
        cam_id = cam_info.get('id', 0)
        cam_type = cam_info.get('type', 'Unknown')
        
        typer.echo(f"\n🎯 Single camera detected: {cam_type} (ID: {cam_id})")
        angle = Prompt.ask("Enter viewing angle for this camera (front, top, side, wrist, etc.)", 
                          default="front")
        
        selected_config = {
            'enabled': True,
            'cameras': [{
                'camera_id': cam_id,
                'camera_type': cam_type,
                'angle': angle.lower(),
                'camera_info': cam_info
            }]
        }
        
        typer.echo(f"\n✅ Using camera: {cam_type} (ID: {cam_id}) - {angle} view")
        return selected_config
    
    # Handle multiple cameras - original logic
    camera_angles = {}
    typer.echo("\n🎯 Camera Angle Mapping")
    typer.echo("Please specify the viewing angle for each camera (front, top, side, wrist, etc.)")
    
    for i, cam_info in enumerate(cameras):
        cam_id = cam_info.get('id', i)
        cam_type = cam_info.get('type', 'Unknown')
        
        angle = Prompt.ask(f"Enter viewing angle for Camera #{i} ({cam_type} - ID: {cam_id})", 
                          default="front")
        camera_angles[i] = {
            'camera_id': cam_id,
            'camera_type': cam_type,
            'angle': angle.lower(),
            'camera_info': cam_info
        }
    
    # Select cameras for teleoperation
    typer.echo("\n📹 Camera Selection for Teleoperation")
    typer.echo("Enter the camera numbers you want to use for teleoperation")
    typer.echo("(separate multiple cameras with commas or spaces)")
    typer.echo("Example: '0,2' or '0 1 3' or just '0' for single camera")
    
    while True:
        try:
            selection = Prompt.ask("Select cameras", default="0")
            
            # Parse camera selection (handle both comma and space separation)
            selected_cameras = []
            if ',' in selection:
                selected_cameras = [int(x.strip()) for x in selection.split(',')]
            else:
                selected_cameras = [int(x.strip()) for x in selection.split()]
            
            # Validate selection
            valid_cameras = []
            for cam_num in selected_cameras:
                if 0 <= cam_num < len(cameras):
                    valid_cameras.append(cam_num)
                else:
                    typer.echo(f"⚠️  Camera #{cam_num} is not valid (available: 0-{len(cameras)-1})")
            
            if valid_cameras:
                break
            else:
                typer.echo("❌ No valid cameras selected. Please try again.")
                
        except ValueError:
            typer.echo("❌ Invalid input. Please enter camera numbers separated by commas or spaces.")
    
    # Build final camera configuration
    selected_config = {
        'enabled': True,
        'cameras': []
    }
    
    for cam_num in valid_cameras:
        cam_config = camera_angles[cam_num].copy()
        selected_config['cameras'].append(cam_config)
    
    # Display final selection
    typer.echo("\n✅ Selected cameras for teleoperation:")
    for cam_config in selected_config['cameras']:
        typer.echo(f"  • Camera #{cam_config['camera_id']} ({cam_config['camera_type']}) - {cam_config['angle']} view")
    
    return selected_config

def setup_cameras() -> Dict:
    """
    Complete camera setup workflow for teleoperation
    Returns camera configuration or empty dict if no cameras
    """
    
    if not CAMERAS_AVAILABLE:
        typer.echo("❌ Camera functionality not available. Please ensure lerobot is properly installed.")
        return {'enabled': False, 'cameras': []}
    
    # Find available cameras
    cameras = find_available_cameras()
    
    if not cameras:
        typer.echo("❌ No cameras detected. Continuing without camera support.")
        return {'enabled': False, 'cameras': []}
    
    # Setup camera mapping and selection
    camera_config = setup_camera_mapping(cameras)
    
    return camera_config