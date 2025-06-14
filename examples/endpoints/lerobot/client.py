"""
LeRobot client for Solo Server
Example client code for robot control via the LeRobot endpoint
"""
import requests
import numpy as np
import time
import json
from typing import Dict, List, Optional, Any


class RobotClient:
    """
    Client for LeRobot inference endpoint
    Handles communication with Solo Server for robot control
    """
    
    def __init__(self, server_url: str = "http://localhost:5070"):
        """Initialize client with server URL"""
        self.server_url = server_url.rstrip('/')
        self.predict_url = f"{self.server_url}/predict"
        
        # Check server health
        try:
            response = requests.get(f"{self.server_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Connected to LeRobot server at {self.server_url}")
            else:
                print(f"⚠️  Server returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Could not connect to server: {e}")
    
    def get_observation(self) -> Dict[str, Any]:
        """
        Get current observation from robot
        In a real implementation, this would read from actual sensors
        """
        # Mock implementation - replace with actual sensor reading
        observation = {
            "state": np.random.randn(6).tolist()  # 6 DOF joint positions
        }
        return observation
    
    def predict(self, observation: Dict[str, Any]) -> np.ndarray:
        """
        Send observation to server and get action prediction
        
        Args:
            observation: Dict with 'state' and optionally 'image' and 'task'
        
        Returns:
            numpy array of actions
        """
        try:
            response = requests.post(
                self.predict_url,
                json={"observation": observation},
                timeout=0.1  # 100ms timeout for real-time control
            )
            
            if response.status_code == 200:
                data = response.json()
                return np.array(data["action"])
            else:
                print(f"❌ Prediction failed: {response.status_code}")
                return np.zeros(6)  # Safe default
                
        except requests.exceptions.Timeout:
            print("⚠️  Prediction timeout - returning safe action")
            return np.zeros(6)
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return np.zeros(6)
    
    def execute(self, action: np.ndarray) -> bool:
        """
        Execute action on robot
        In a real implementation, this would send commands to motors
        """
        # Mock implementation - replace with actual motor control
        print(f"Executing action: {action}")
        return True
    
    def reset(self) -> bool:
        """Reset the policy state"""
        # In full implementation, would call reset endpoint
        print("Policy reset")
        return True


def demo_control_loop():
    """
    Demonstrate a simple robot control loop
    """
    print("🤖 LeRobot Control Demo")
    print("=" * 40)
    
    # Initialize client
    robot = RobotClient()
    robot.reset()
    
    # Control loop
    print("\nStarting control loop (10 iterations)...")
    start_time = time.time()
    
    for i in range(10):
        loop_start = time.time()
        
        # Get observation
        obs = robot.get_observation()
        
        # Get action from policy
        action = robot.predict(obs)
        
        # Execute action
        success = robot.execute(action)
        
        # Calculate loop time
        loop_time = (time.time() - loop_start) * 1000  # ms
        
        print(f"Step {i+1}: Loop time: {loop_time:.1f}ms, "
              f"Action norm: {np.linalg.norm(action):.3f}")
        
        # Control at ~30Hz
        sleep_time = max(0, (1/30) - (time.time() - loop_start))
        time.sleep(sleep_time)
    
    total_time = time.time() - start_time
    avg_hz = 10 / total_time
    
    print(f"\nControl loop complete!")
    print(f"Average frequency: {avg_hz:.1f} Hz")
    print(f"Total time: {total_time:.2f}s")


def demo_with_task():
    """
    Demonstrate control with language task (for VLA models)
    """
    print("\n🤖 LeRobot VLA Demo (with language task)")
    print("=" * 40)
    
    robot = RobotClient()
    
    # Define a task
    task = "pick up the red cube"
    print(f"Task: {task}")
    
    # Get observation with task
    obs = robot.get_observation()
    obs["task"] = task
    
    # Get action
    action = robot.predict(obs)
    
    print(f"Policy output for task: {action}")
    print(f"Action magnitude: {np.linalg.norm(action):.3f}")


def demo_batch_inference():
    """
    Demonstrate batch inference for multiple robots
    """
    print("\n🤖 Batch Inference Demo")
    print("=" * 40)
    
    robot = RobotClient()
    
    # Simulate multiple robots with different states
    robots_states = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Robot 1: home position
        [0.5, 0.2, -0.3, 0.1, 0.0, 0.0],  # Robot 2: mid-task
        [-0.2, 0.8, 0.4, -0.1, 0.3, 0.0]  # Robot 3: different pose
    ]
    
    print("Processing 3 robots in parallel...")
    
    for i, state in enumerate(robots_states):
        obs = {"state": state}
        action = robot.predict(obs)
        print(f"Robot {i+1}: State norm={np.linalg.norm(state):.2f}, "
              f"Action norm={np.linalg.norm(action):.2f}")


if __name__ == "__main__":
    # Run demos
    demo_control_loop()
    demo_with_task()
    demo_batch_inference()
    
    print("\n✅ All demos complete!")