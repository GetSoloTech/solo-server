#!/usr/bin/env python3
"""
Direct SO101 motor test - bypasses LeRobot's detection
"""
import os
import time

def test_direct_control():
    """Test motor control with minimal setup"""
    
    print("🤖 SO101 Direct Motor Test")
    print("=" * 50)
    
    port = os.environ.get("ROBOT_PORT", "/dev/tty.usbmodem5A460842171")
    
    try:
        from lerobot.common.motors.feetech import FeetechMotorsBus
        from lerobot.common.motors import Motor, MotorNormMode
        
        print(f"Creating motor bus on {port}...")
        
        # Create bus with just one motor to test
        bus = FeetechMotorsBus(
            port=port,
            motors={
                "gripper": Motor(6, "sts3215", MotorNormMode.DEGREES),
            }
        )
        
        # Connect without handshake to avoid detection issues
        print("Connecting to motor bus...")
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
        bus._is_connected = True
        
        print("✅ Connected!")
        
        # Try to read position
        print("\nReading gripper position...")
        try:
            data = bus.read("present_position")
            print(f"Current position: {data}")
        except Exception as e:
            print(f"Read error: {e}")
        
        # Try a small movement
        print("\nMoving gripper +10 degrees...")
        try:
            bus.write("goal_position", {"gripper": 10.0}, True)
            time.sleep(1)
            
            # Read new position
            new_data = bus.read("present_position")
            print(f"New position: {new_data}")
        except Exception as e:
            print(f"Write error: {e}")
        
        bus.port_handler.closePort()
        print("\n✅ Test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_control()