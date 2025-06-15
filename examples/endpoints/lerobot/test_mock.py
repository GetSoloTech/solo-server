#!/usr/bin/env python3
"""
Quick test of the mock implementation without needing full dependencies
"""
import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Can we import the modules?
print("Test 1: Importing modules...")
try:
    from model import MockPolicy, MockRobot, create_model
    print("✅ Successfully imported from model.py")
except ImportError as e:
    print(f"❌ Failed to import from model.py: {e}")
    sys.exit(1)

# Test 2: Can we create mock instances?
print("\nTest 2: Creating mock instances...")
try:
    robot = MockRobot()
    print("✅ Created MockRobot")
    
    policy = MockPolicy("lerobot/act_so101", "cpu")
    print("✅ Created MockPolicy")
    print(f"   Model: {policy.model_path}")
    print(f"   Action dim: {policy.action_dim}")
except Exception as e:
    print(f"❌ Failed to create mocks: {e}")
    sys.exit(1)

# Test 3: Can we use the robot?
print("\nTest 3: Testing MockRobot...")
try:
    # Read positions
    positions = robot.read_positions()
    print(f"✅ Read positions: {positions}")
    
    # Write positions
    import numpy as np
    new_positions = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    success = robot.write_positions(new_positions)
    print(f"✅ Write positions: {success}")
    
    # Check state
    state = robot.get_state()
    print(f"✅ Got state with keys: {list(state.keys())}")
except Exception as e:
    print(f"❌ Robot test failed: {e}")
    sys.exit(1)

# Test 4: Can we use the policy?
print("\nTest 4: Testing MockPolicy...")
try:
    # Create mock observation
    class MockTensor:
        def __init__(self, data):
            self.data = data
    
    obs = {
        "observation.state": MockTensor([0.0] * 6),
        "task": "pick up the cube"
    }
    
    # Get action (we'll fake torch.Tensor for now)
    action = policy.select_action(obs)
    print(f"✅ Got action: {action}")
    
    # Reset
    policy.reset()
    print("✅ Reset policy")
except Exception as e:
    print(f"❌ Policy test failed: {e}")
    sys.exit(1)

# Test 5: Can we use the factory?
print("\nTest 5: Testing model factory...")
try:
    # Test SO101
    so101 = create_model("lerobot/act_so101", "cpu")
    print(f"✅ Created SO101 model")
    print(f"   Type: {type(so101).__name__}")
    
    # Test ALOHA
    aloha = create_model("lerobot/act_aloha", "cpu")
    print(f"✅ Created ALOHA model")
    print(f"   Type: {type(aloha).__name__}")
    
    # Test generic
    generic = create_model("lerobot/some_other_model", "cpu")
    print(f"✅ Created generic model")
    print(f"   Type: {type(generic).__name__}")
except Exception as e:
    print(f"❌ Factory test failed: {e}")
    sys.exit(1)

print("\n🎉 All mock tests passed!")
print("\nNote: This only tests the mock implementations.")
print("Full server testing requires torch, numpy, and litserve dependencies.")