"""
Robotics command for Solo CLI
Framework: LeRobot
"""

import json
import os
import typer
from solo.config import CONFIG_PATH
from solo.commands.robots.lerobot import lerobot


def robo(
    motors: str = typer.Option(
        None,
        "--motors",
        help="Setup motor IDs: 'leader', 'follower', or 'all'",
    ),
    calibrate: str = typer.Option(
        None,
        "--calibrate",
        help="Calibrate robot arms: 'leader', 'follower', or 'all' (requires motor setup)",
    ),
    teleop: bool = typer.Option(False, "--teleop", help="Start teleoperation (requires calibrated arms)"),
    record: bool = typer.Option(False, "--record", help="Record data for training (requires calibrated arms)"),
    train: bool = typer.Option(False, "--train", help="Train a model (requires recorded data)"),
    inference: bool = typer.Option(False, "--inference", help="Run inference on a pre-trained model"),
):
    """
    Robotics operations: motor setup, calibration, teleoperation, data recording, training, and inference
    """
    # Load existing config
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            config = {}
    
    # Use LeRobot handler directly
    lerobot.handle_lerobot(config, calibrate, motors, teleop, record, train, inference) 