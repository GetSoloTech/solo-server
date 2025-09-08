import time
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
from lerobot.teleoperators.so101_leader.so101_leader import SO101Leader
from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
from lerobot.robots.so101_follower.so101_follower import SO101Follower

# 1) Leader (uses the calibration saved under teleop.id)
leader = SO101Leader(SO101LeaderConfig(
    # Keep changing the port depending on it
    port="/dev/ttyACM0",
    id="leader_01",
    use_degrees=True,  # or False; match your preference
))
leader.connect(calibrate=True)

# 2) Followers (each with its own port + id that you calibrated above)
followers = [
    # This will be the followers;
    SO101Follower(SO101FollowerConfig(port="/dev/ttyACM1", id="follower_A")),
    SO101Follower(SO101FollowerConfig(port="/dev/ttyACM2", id="follower_B")),
]
for r in followers:
    r.connect(calibrate=True)

# Optional: per-arm trims (if one arm needs an offset or inversion)
def map_action_for(r, action):
    # Example: invert wrist roll if your build differs
    # a = dict(action); a["wrist_roll.pos"] *= -1
    return action

TARGET_HZ = 60
dt = 1.0 / TARGET_HZ

try:
    while True:
        action = leader.get_action()           # {"shoulder_pan.pos": ..., ...}
        for r in followers:
            r.send_action(map_action_for(r, action))
        time.sleep(dt)
finally:
    for r in followers:
        r.disconnect()
    leader.disconnect()
# You should basically calibrate the files, make the motors connected to each and also just run

# python multi_teleop.py
