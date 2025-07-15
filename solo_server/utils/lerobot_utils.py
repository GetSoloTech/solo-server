"""
LeRobot utilities for Solo Server
Handles port detection, calibration, teleoperation setup, and data recording
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
    from lerobot.common.cameras.opencv.camera_opencv import OpenCVCamera
    from lerobot.common.cameras.realsense.camera_realsense import RealSenseCamera
    from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.common.cameras.realsense.configuration_realsense import RealSenseCameraConfig
    LEROBOT_AVAILABLE = True
    CAMERAS_AVAILABLE = True
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
    OpenCVCamera = None
    RealSenseCamera = None
    OpenCVCameraConfig = None
    RealSenseCameraConfig = None
    LEROBOT_AVAILABLE = False
    CAMERAS_AVAILABLE = False

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
    from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.common.cameras.realsense.configuration_realsense import RealSenseCameraConfig
    
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
            from lerobot.common.constants import HF_LEROBOT_HOME
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
            # User is logged in, extract username
            username = result.stdout.strip().split('\n')[0]
            return True, username
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
    
    # Not logged in, prompt for login
    typer.echo("🔐 You need to log in to HuggingFace to record data.")
    should_login = Confirm.ask("Would you like to log in now?", default=True)
    
    if not should_login:
        typer.echo("❌ HuggingFace login required for data recording.")
        return False, ""
    
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

def recording_mode(config: dict):
    """Handle LeRobot recording mode"""
    typer.echo("🎬 Starting LeRobot recording mode...")
    
    # Check if arms are already calibrated
    lerobot_config = config.get('lerobot', {})
    leader_port = lerobot_config.get('leader_port')
    follower_port = lerobot_config.get('follower_port')
    leader_calibrated = lerobot_config.get('leader_calibrated', False)
    follower_calibrated = lerobot_config.get('follower_calibrated', False)
    robot_type = lerobot_config.get('robot_type', 'so100')
    
    if not (leader_port and follower_port and leader_calibrated and follower_calibrated):
        typer.echo("❌ Arms are not properly calibrated.")
        typer.echo("Please run one of the following first:")
        typer.echo("   • 'solo robo --type lerobot --calibrate' - Configure arms only")
        typer.echo("   • 'solo robo --type lerobot' - Full setup (motors + calibration + teleoperation)")
        return
    
    typer.echo("✅ Found calibrated arms:")
    typer.echo(f"   • Robot type: {robot_type.upper()}")
    typer.echo(f"   • Leader arm: {leader_port}")
    typer.echo(f"   • Follower arm: {follower_port}")
    
    # Step 1: HuggingFace authentication
    typer.echo("\n📋 Step 1: HuggingFace Authentication")
    login_success, hf_username = huggingface_login_flow()
    
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
        from lerobot.record import record, DatasetRecordConfig, RecordConfig
    except ImportError as e:
        typer.echo(f"❌ Error importing lerobot recording components: {e}")
        return
    
    try:
        # Setup cameras
        camera_config = setup_cameras_for_teleoperation()
        
        # Create robot and teleoperator configurations
        leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
        
        if leader_config_class is None or follower_config_class is None:
            typer.echo(f"❌ Unsupported robot type: {robot_type}")
            return
        
        # Create configurations
        leader_config = leader_config_class(port=leader_port, id=f"{robot_type}_leader")
        
        # Create robot config with cameras if enabled
        follower_config = create_follower_config(follower_config_class, follower_port, robot_type, camera_config)
        
        # Create dataset configuration
        dataset_config = DatasetRecordConfig(
            repo_id=dataset_repo_id,
            single_task=task_description,
            episode_time_s=episode_time,
            num_episodes=num_episodes,
            push_to_hub=push_to_hub,
            fps=30,  # Default FPS
            video=True,  # Enable video encoding
        )
        
        # Create recording configuration
        record_config = RecordConfig(
            robot=follower_config,
            teleop=leader_config,
            dataset=dataset_config,
            display_data=True,  # Show camera feed during recording
            play_sounds=True,   # Enable audio cues
            resume=should_resume,  # Resume from existing dataset if needed
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
        camera_config = setup_cameras_for_teleoperation()
    
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

def find_available_cameras() -> List[Dict]:
    """
    Find all available cameras (OpenCV and RealSense)
    Returns list of camera information dictionaries
    """
    if not CAMERAS_AVAILABLE:
        typer.echo("❌ Camera modules are not available.")
        return []
    
    all_cameras = []
    
    try:
        # Find OpenCV cameras
        typer.echo("🔍 Searching for OpenCV cameras...")
        opencv_cameras = OpenCVCamera.find_cameras()
        all_cameras.extend(opencv_cameras)
        typer.echo(f"✅ Found {len(opencv_cameras)} OpenCV cameras")
    except Exception as e:
        typer.echo(f"⚠️  Error finding OpenCV cameras: {e}")
    
    try:
        # Find RealSense cameras
        typer.echo("🔍 Searching for RealSense cameras...")
        realsense_cameras = RealSenseCamera.find_cameras()
        all_cameras.extend(realsense_cameras)
        typer.echo(f"✅ Found {len(realsense_cameras)} RealSense cameras")
    except ImportError:
        typer.echo("⚠️  RealSense library not available, skipping RealSense camera search")
    except Exception as e:
        typer.echo(f"⚠️  Error finding RealSense cameras: {e}")
    
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

def setup_cameras_for_teleoperation() -> Dict:
    """
    Complete camera setup workflow for teleoperation
    Returns camera configuration or empty dict if no cameras
    """
    # Ask if user wants to use cameras
    use_cameras = Confirm.ask("Would you like to use cameras?", default=True)
    
    if not use_cameras:
        typer.echo("📷 Cameras disabled for teleoperation")
        return {'enabled': False, 'cameras': []}
    
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