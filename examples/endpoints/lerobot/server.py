"""
LeRobot LitServe Endpoint for Solo Server

Built by Devinder Sodhi with assistance from Claude

Provides robot control inference with Physical AI models
"""
import torch
import numpy as np
import litserve as ls
import base64
from typing import Dict, Any, Optional
import time
import os

# Import the model implementation
from model import create_model, LeRobotModel


class LeRobotAPI(ls.LitAPI):
    """
    LitServe API for LeRobot inference
    Handles real-time robot control with Physical AI models
    """
    
    def setup(self, device):
        """Initialize the policy and robot connection"""
        # Handle device selection for M4 Mac
        if str(device).lower() in ["cuda", "0"] and not torch.cuda.is_available():
            if torch.backends.mps.is_available():
                device = "mps"
                print(f"CUDA not available, using MPS (Apple Silicon)")
            else:
                device = "cpu"
                print(f"CUDA not available, using CPU")
        
        self.device = device
        
        # Get model path from environment or use default
        model_path = os.environ.get("LEROBOT_MODEL", "local:so101")
        print(f"Loading model: {model_path} on device: {device}")
        
        # Initialize model using the factory
        self.model = create_model(model_path, device)
        
        # Action buffer for temporal smoothing
        self.action_buffer = []
        self.max_buffer_size = 5
        
        # Log initialization (commented out for production)
        # print(f"LeRobot API initialized on {device}")
        # print(f"Model: {model_path}")
        # print(f"Info: {self.model.get_info()}")
    
    def decode_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decode API request into observation format
        
        Expected format:
        {
            "observation": {
                "image": "base64_encoded_image",  # Optional
                "state": [0.1, 0.2, ...],         # Joint positions
                "task": "pick up the cube"        # Optional for VLA models
            }
        }
        """
        return request.get("observation", {})
    
    def predict(self, observation: Dict[str, Any]) -> np.ndarray:
        """
        Run inference and return robot actions
        """
        # Use model to predict action
        action = self.model.predict(observation)
        
        # Add to buffer for temporal smoothing
        self.action_buffer.append(action)
        if len(self.action_buffer) > self.max_buffer_size:
            self.action_buffer.pop(0)
        
        # Return smoothed action (average of buffer)
        if len(self.action_buffer) > 1:
            smoothed_action = np.mean(self.action_buffer, axis=0)
        else:
            smoothed_action = action
        
        return smoothed_action
    
    def encode_response(self, action: np.ndarray) -> Dict[str, Any]:
        """
        Encode the action into API response format
        """
        model_info = self.model.get_info()
        return {
            "action": action.tolist(),
            "timestamp": time.time(),
            "info": {
                "action_dim": len(action),
                "buffer_size": len(self.action_buffer),
                "mock_mode": model_info.get("mock_mode", True),
                "model_type": model_info.get("policy_type", "unknown")
            }
        }


# Additional endpoints for robot control
class LeRobotControlAPI(LeRobotAPI):
    """Extended API with additional robot control endpoints"""
    
    def setup(self, device):
        super().setup(device)
        self.emergency_stop = False
    
    def reset(self) -> Dict[str, Any]:
        """Reset the policy and clear buffers"""
        self.model.reset()
        self.action_buffer.clear()
        self.emergency_stop = False
        return {"status": "reset", "timestamp": time.time()}
    
    def status(self) -> Dict[str, Any]:
        """Get current robot and policy status"""
        model_info = self.model.get_info()
        
        # Get robot state if available
        robot_state = {}
        if hasattr(self.model, 'robot') and hasattr(self.model.robot, 'get_state'):
            robot_state = self.model.robot.get_state()
        
        return {
            "robot": {
                "state": robot_state,
                "emergency_stop": self.emergency_stop
            },
            "model": model_info,
            "timestamp": time.time()
        }
    
    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """Execute action on robot (for manual control)"""
        if not self.emergency_stop:
            # Execute through model's robot if available
            success = False
            if hasattr(self.model, 'robot') and hasattr(self.model.robot, 'write_positions'):
                success = self.model.robot.write_positions(action)
            else:
                # In mock mode, just return success
                success = True
                
            return {
                "success": success,
                "executed_action": action.tolist(),
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "error": "Emergency stop active",
                "timestamp": time.time()
            }
    
    def stop(self) -> Dict[str, Any]:
        """Emergency stop"""
        self.emergency_stop = True
        # In real implementation, would send stop command to motors
        return {"status": "stopped", "timestamp": time.time()}


if __name__ == "__main__":
    # Basic inference API
    api = LeRobotAPI()
    server = ls.LitServer(
        api, 
        accelerator='auto',
        api_path="/predict"  # Main inference endpoint
    )
    
    # For development, add control endpoints
    # In production, these would be separate services
    # control_api = LeRobotControlAPI()
    # control_server = ls.LitServer(control_api, accelerator='auto')
    
    print("Starting LeRobot inference server...")
    print("Endpoints:")
    print("  POST /predict - Run inference")
    print("  GET  /health  - Health check")
    print("\nExample usage:")
    print("  curl -X POST http://localhost:5070/predict \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"observation\": {\"state\": [0, 0, 0, 0, 0, 0]}}'")
    
    server.run(port=5070)