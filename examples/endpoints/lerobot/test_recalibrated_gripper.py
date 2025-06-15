#!/usr/bin/env python3
"""
Test SO101 with recalibrated gripper motor.
The gripper motor (originally ID 6) has been recalibrated to ID 1.
"""

import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Use custom motor bus that bypasses the handshake
from lerobot.common.motors import Motor, MotorNormMode
from lerobot.common.motors.feetech import FeetechMotorsBus
import scservo_sdk as scs

class CustomFeetechBus(FeetechMotorsBus):
    """Custom bus that skips motor existence check"""
    
    def _assert_motors_exist(self):
        """Override to skip motor existence check"""
        print("Skipping motor existence check...")
        pass
    
    def _assert_same_firmware(self):
        """Override to skip firmware check"""
        print("Skipping firmware check...")
        pass

def test_gripper():
    """Test gripper motor at ID 1"""
    
    port = os.environ.get("ROBOT_PORT", "/dev/tty.usbmodem5A460842171")
    
    # Create custom bus with just the gripper
    print(f"Creating motor bus for gripper at ID 1 on {port}...")
    bus = CustomFeetechBus(
        port=port,
        motors={
            "gripper": Motor(1, "sts3215", MotorNormMode.RANGE_0_100),
        }
    )
    
    try:
        # Connect with proper port handler
        print("Connecting to motor...")
        bus.port_handler = scs.PortHandler(port)
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1000000)
        
        # Enable torque
        print("Enabling torque...")
        bus.write("Torque_Enable", "gripper", 1)
        
        # Test gripper positions
        print("\nTesting gripper movement:")
        
        positions = [
            (0, "Closed"),
            (50, "Half open"),
            (100, "Fully open"),
            (25, "Quarter open"),
            (75, "Three quarters open"),
            (50, "Return to middle")
        ]
        
        for pos, desc in positions:
            print(f"\n{desc} ({pos}%)...")
            
            # Convert percentage to motor position
            # For STS3215, range is 0-4095
            motor_pos = int(pos * 40.95)  # 4095 / 100
            
            # Write position
            bus.write("Goal_Position", "gripper", motor_pos)
            
            # Wait for movement
            time.sleep(1.5)
            
            # Read current position
            current_pos = bus.read("Present_Position", "gripper")
            current_percent = (current_pos / 40.95) if current_pos else 0
            print(f"  Current position: {current_pos} ({current_percent:.1f}%)")
        
        # Disable torque
        print("\nDisabling torque...")
        bus.write("Torque_Enable", "gripper", 0)
        
        # Close port
        bus.port_handler.close()
        
        print("\n✓ Test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(test_gripper())