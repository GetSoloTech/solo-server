"""
Camera utilities for LeRobot
"""

import typer
from typing import List, Dict
from rich.prompt import Prompt

# Import lerobot camera modules
from lerobot.cameras.opencv.camera_opencv import OpenCVCamera
from lerobot.cameras.realsense.camera_realsense import RealSenseCamera


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
    except Exception as e:
        typer.echo(f"⚠️  Error finding {camera_type_name} cameras: {e}")
        return []


def find_available_cameras() -> List[Dict]:
    """
    Find all available cameras (OpenCV and RealSense)
    Returns list of camera information dictionaries
    """
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
    
    # Find available cameras
    cameras = find_available_cameras()
    
    if not cameras:
        typer.echo("❌ No cameras detected. Continuing without camera support.")
        return {'enabled': False, 'cameras': []}
    
    # Setup camera mapping and selection
    camera_config = setup_camera_mapping(cameras)
    
    return camera_config
