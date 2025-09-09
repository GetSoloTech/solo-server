"""
Robotics command for Solo Server
Frameworks: LeRobot, Nvidia GROOT
"""

import json
import os
import typer
import click
from enum import Enum
from solo_server.config import CONFIG_PATH
from solo_server.commands.robots import nvidia_groot
from solo_server.commands.robots.lerobot import lerobot


class RoboticsType(str, Enum):
    LEROBOT = "lerobot"
    GROOT = "groot"

def robo(
    type: RoboticsType = typer.Option(RoboticsType.LEROBOT, "--type", help="Robotics framework to use"),
    motors: str = typer.Option(
        None,
        "--motors",
        help="Setup motor IDs: 'leader', 'follower', or both",
    ),
    calibrate: str = typer.Option(
        None,
        "--calibrate",
        help="Calibrate robot arms: 'leader', 'follower', or both (requires motor setup)",
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
    
    # Route to appropriate handler based on type
    if type == RoboticsType.LEROBOT:
        lerobot.handle_lerobot(config, calibrate, motors, teleop, record, train, inference)
    elif type == RoboticsType.GROOT:
        nvidia_groot.handle_nvidia_groot(config, calibrate, teleop, record, train, inference)
    else:
        typer.echo(f"❌ Unsupported robotics type: {type}") 