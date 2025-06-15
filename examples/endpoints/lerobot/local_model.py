"""
Local LeRobot Model Implementation
Uses LeRobot without downloading models from HuggingFace
"""
import torch
import numpy as np
from typing import Dict, Any, Optional
import os

# Import LeRobot components
try:
    from lerobot.common.policies.diffusion.configuration_diffusion import DiffusionConfig
    from lerobot.common.policies.diffusion.modeling_diffusion import DiffusionPolicy
    from lerobot.common.policies.act.configuration_act import ACTConfig
    from lerobot.common.policies.act.modeling_act import ACTPolicy
    from lerobot.common.datasets.lerobot_dataset import LeRobotDatasetMetadata
    LEROBOT_AVAILABLE = True
except ImportError:
    LEROBOT_AVAILABLE = False
    print("[Warning] LeRobot not available, using mock implementation")


class LocalLeRobotModel:
    """
    LeRobot model that works without internet/downloads
    Creates policies from scratch with proper configurations
    """
    
    def __init__(self, robot_type: str = "so101", policy_type: str = "act", device: str = "cpu"):
        self.robot_type = robot_type
        self.policy_type = policy_type
        self.device = device
        self.mock_mode = os.environ.get("MOCK_HARDWARE", "true").lower() == "true"
        
        # Define robot configurations
        self.robot_configs = {
            "so101": {
                "action_dim": 6,
                "state_dim": 6,
                "camera_names": ["top"],
                "input_features": ["state", "top"],
                "output_features": ["action"],
            },
            "so100": {
                "action_dim": 6,
                "state_dim": 6,
                "camera_names": ["top"],
                "input_features": ["state", "top"],
                "output_features": ["action"],
            },
            "aloha": {
                "action_dim": 14,
                "state_dim": 14,
                "camera_names": ["cam_high", "cam_left_wrist", "cam_right_wrist"],
                "input_features": ["state", "cam_high", "cam_left_wrist", "cam_right_wrist"],
                "output_features": ["action"],
            }
        }
        
        # Get robot config
        self.config = self.robot_configs.get(robot_type, self.robot_configs["so101"])
        
        # Create policy
        if LEROBOT_AVAILABLE and not self.mock_mode:
            self.policy = self._create_policy()
        else:
            try:
                from .model import MockPolicy  # Fallback to mock
            except ImportError:
                from model import MockPolicy
            self.policy = MockPolicy(f"local_{robot_type}_{policy_type}", device)
            
    def _create_policy(self):
        """Create a policy from scratch without downloading"""
        # Create feature specifications
        input_features = []
        for feature in self.config["input_features"]:
            if feature == "state":
                input_features.append({
                    "name": "observation.state",
                    "shape": (self.config["state_dim"],),
                    "dtype": "float32"
                })
            elif feature in self.config["camera_names"]:
                input_features.append({
                    "name": f"observation.images.{feature}",
                    "shape": (3, 480, 640),  # Standard camera resolution
                    "dtype": "uint8"
                })
        
        output_features = [{
            "name": "action",
            "shape": (self.config["action_dim"],),
            "dtype": "float32"
        }]
        
        # Create mock dataset stats for normalization
        dataset_stats = self._create_mock_stats()
        
        # Create policy based on type
        if self.policy_type == "act":
            config = ACTConfig(
                input_features=input_features,
                output_features=output_features,
                chunk_size=100,  # ACT specific
                n_obs_steps=1,
                n_action_steps=100,
            )
            policy = ACTPolicy(config, dataset_stats=dataset_stats)
        elif self.policy_type == "diffusion":
            config = DiffusionConfig(
                input_features=input_features,
                output_features=output_features,
                num_inference_steps=10,
                horizon=16,
                n_obs_steps=2,
                n_action_steps=8,
            )
            policy = DiffusionPolicy(config, dataset_stats=dataset_stats)
        else:
            # Default to ACT
            config = ACTConfig(
                input_features=input_features,
                output_features=output_features,
                chunk_size=100,
                n_obs_steps=1,
                n_action_steps=100,
            )
            policy = ACTPolicy(config, dataset_stats=dataset_stats)
        
        # Move to device and set to eval mode
        policy = policy.to(self.device)
        policy.eval()
        
        # Initialize with random weights (or load from local checkpoint)
        if os.path.exists("local_checkpoints/policy.pt"):
            print("Loading from local checkpoint...")
            checkpoint = torch.load("local_checkpoints/policy.pt", map_location=self.device)
            policy.load_state_dict(checkpoint)
        else:
            print("Using random initialization (no pre-trained weights)")
            
        return policy
    
    def _create_mock_stats(self):
        """Create mock dataset statistics for normalization"""
        stats = {}
        
        # State statistics
        stats["observation.state"] = {
            "mean": np.zeros(self.config["state_dim"]),
            "std": np.ones(self.config["state_dim"]),
            "min": np.ones(self.config["state_dim"]) * -1.0,
            "max": np.ones(self.config["state_dim"]),
        }
        
        # Camera statistics (if used)
        for cam in self.config["camera_names"]:
            stats[f"observation.images.{cam}"] = {
                "mean": np.array([[[0.485]], [[0.456]], [[0.406]]]),  # ImageNet means
                "std": np.array([[[0.229]], [[0.224]], [[0.225]]]),   # ImageNet stds
                "min": np.array([[[0.0]], [[0.0]], [[0.0]]]),
                "max": np.array([[[1.0]], [[1.0]], [[1.0]]]),
            }
        
        # Action statistics
        stats["action"] = {
            "mean": np.zeros(self.config["action_dim"]),
            "std": np.ones(self.config["action_dim"]) * 0.1,  # Small actions
            "min": np.ones(self.config["action_dim"]) * -1.0,
            "max": np.ones(self.config["action_dim"]),
        }
        
        return stats
    
    def predict(self, observation: Dict[str, Any]) -> np.ndarray:
        """Run inference"""
        # Convert observation to policy format
        batch = self._prepare_batch(observation)
        
        # Run policy
        with torch.no_grad():
            if hasattr(self.policy, 'select_action'):
                action = self.policy.select_action(batch)
            else:
                action = self.policy(batch)["action"]
        
        # Convert to numpy
        if isinstance(action, torch.Tensor):
            action = action.cpu().numpy()
            
        # Ensure correct shape
        if action.ndim == 3:  # [batch, time, dim]
            action = action[0, 0]  # Take first timestep
        elif action.ndim == 2:  # [batch, dim]
            action = action[0]
            
        return action
    
    def _prepare_batch(self, observation: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        """Prepare observation for policy"""
        batch = {}
        
        # Add state
        if "state" in observation:
            state = torch.tensor(observation["state"], dtype=torch.float32)
            batch["observation.state"] = state.unsqueeze(0).to(self.device)
        
        # Add images if present
        for cam in self.config["camera_names"]:
            if cam in observation.get("images", {}):
                # Assume image is already preprocessed
                img = observation["images"][cam]
                if isinstance(img, np.ndarray):
                    img = torch.from_numpy(img)
                batch[f"observation.images.{cam}"] = img.unsqueeze(0).to(self.device)
        
        return batch
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "robot_type": self.robot_type,
            "policy_type": self.policy_type,
            "action_dim": self.config["action_dim"],
            "state_dim": self.config["state_dim"],
            "camera_names": self.config["camera_names"],
            "device": str(self.device),
            "using_local": True,
            "mock_mode": self.mock_mode,
        }


# Example usage
if __name__ == "__main__":
    # Create model without downloads
    model = LocalLeRobotModel(robot_type="so101", policy_type="act")
    
    # Test inference
    observation = {
        "state": [0.0] * 6,  # 6 DOF state
    }
    
    action = model.predict(observation)
    print(f"Action: {action}")
    print(f"Info: {model.get_info()}")