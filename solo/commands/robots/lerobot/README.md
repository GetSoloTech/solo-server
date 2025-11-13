## LeRobot with Solo CLI:

Use `solo robo` command to run a complete robotics workflow with LeRobot: motor setup, calibration, teleoperation, data recording, training, and inference.

### Quick start

```bash
# 1) Setup motor IDs (both arms)
solo robo --motors all   # leader, follower, all

# 2) Calibrate (both arms)
solo robo --calibrate all  # leader, follower, all

# 3) Teleoperate
solo robo --teleop

# 4) Record dataset
solo robo --record

# 5) Train a policy
solo robo --train

# 6) Run inference
solo robo --inference
```

## How configuration and prompts work

- **Stateful config**: Settings are saved to the main config (e.g., ports, ids, robot type, and per-mode arguments) and reused automatically. You will be asked whether to reuse when launching a mode again.
- **Preconfigured mode settings**: For Teleop/Record/Train/Inference, previously saved arguments can be reused without re-entering them.
- **Ports**: Ports are auto-detected and retried when connections fail. If devices move to different ports, the tool guides you to re-detect and updates the config.
- **Cameras**: You can add OpenCV and RealSense cameras, map them to viewing angles (front/top/side/wrist), and select which to display.
- **IDs**: You can pick and reuse friendly `leader_id` and `follower_id` identifiers.

---

## 1) Motors

Most arms provided by Solo Tech already have motor IDs set up, so you can usually skip this step and proceed directly to calibration. Only run this command if you encounter a "missing motor ids" error or if you need to reassign motor IDs for the leader and/or follower arm.

```bash
# Setup both arms 
solo robo --motors all

# Setup only leader
solo robo --motors leader

# Setup only follower
solo robo --motors follower
```

### Interactive flow
- Select or reuse the **robot type** (`SO100` or `SO101`).
- Auto-detect the **leader** and/or **follower** port(s); unplug/replug guidance is provided if needed.
- For each selected arm, the tool launches LeRobot's device and runs `setup_motors()`.

### Tips/Notes
- You will be prompted to connect the arm when the tool searches for its port, so it's best to connect and power on the arm when instructed during the process.
- If auto-detection finds multiple ports, you can select the correct one from a list.
- After successful setup, you'll see a success message and a hint to run calibration next.

---

## 2) Calibrate

Calibrate the leader and/or follower arm(s) after motor IDs are set.

```bash
# Calibrate both
solo robo --calibrate all

# Calibrate only leader
solo robo --calibrate leader

# Calibrate only follower
solo robo --calibrate follower
```

### Interactive flow
- Optionally reuse saved `robot_type` and ports or re-detect them.
- Choose or confirm `leader_id` and `follower_id` (stored for later reuse).
- For each arm selected, LeRobot's calibration is launched and you follow on-screen instructions.

### Tips/Notes
- Calibrate in a safe, clear workspace; follow the on-screen instructions carefully.
- If either arm fails to calibrate, you can rerun calibration for that arm only.
- Once both arms are calibrated, you're ready for Teleop and Recording.

---

## 3) Teleop

Teleoperate the follower arm using the leader arm. Requires both arms calibrated.

```bash
solo robo --teleop
```

### Interactive flow
- If saved Teleop settings exist, choose to reuse or enter new ones.
- Confirm or detect `leader_port` and `follower_port`, confirm `robot_type`.
- Optionally set up cameras (OpenCV/RealSense), assign viewing angles, and select which cameras to display.
- Optionally choose/confirm `leader_id` and `follower_id`.
- Teleoperation starts; move the leader arm to control the follower.

### Tips/Notes
- If a connection error occurs, the tool can auto-detect new ports and retry once.
- Camera setup is optional; if no cameras are found or selected, Teleop will still work.
- Press Ctrl+C to stop Teleop at any time.

---

## 4) Record

Record datasets for training while teleoperating the follower. Requires both arms calibrated.

```bash
solo robo --record
```

### Interactive flow
- Reuse saved Recording settings or enter new ones.
- Confirm `robot_type`, `leader_port`, `follower_port`, and IDs, then set up cameras.
- Choose whether to push to HuggingFace Hub; if yes, you will be prompted to authenticate.
- Enter dataset repository name; if it already exists, choose whether to resume or rename.
- Enter task description, episode duration, and number of episodes.
- Recording starts and follows LeRobot's standard UI/controls.

### Tips/Notes
- Use `local/<name>` or a bare `<name>` to keep datasets local; pushing to Hub is optional.
- Controls during recording:
  - Right Arrow (→): early stop/reset and move to next
  - Left Arrow (←): cancel current episode and re-record
  - Escape (ESC): stop session, encode videos, and upload (if enabled)
- If ports change mid-session, the tool can detect new ports and retry once.

---

## 5) Train

Train a policy on recorded data.

```bash
solo robo --train
```

### Interactive flow
- Reuse saved Training settings or enter new ones.
- Provide `dataset_repo_id` (local or Hub dataset ID).
- Select policy type: SmolVLA, ACT, PI0, TDMPC, or Diffusion Policy.
- Set training steps and batch size.
- Choose output directory; if it exists, pick: resume, overwrite, or new directory.
- Choose whether to push the trained model to HuggingFace Hub (prompts for auth and repo name).
- Optionally enable Weights & Biases logging (prompts to login and set project).
- Training starts using LeRobot's training pipeline.

### Tips/Notes
- Some policies can start from a pretrained checkpoint; SmolVLA defaults to `lerobot/smolvla_base` if not provided.
- Video backend auto-falls back to PyAV if TorchCodec is unavailable.
- Checkpoints are saved regularly; you can resume later if needed.
- Press Ctrl+C to stop early; partial checkpoints may be saved.

---

## 6) Inference

Run a trained policy on the follower arm. Requires the follower to be calibrated. Teleoperation override is optional if the leader is calibrated and available.

```bash
solo robo --inference
```

### Interactive flow
- Reuse saved Inference settings or enter new ones.
- Validates calibrated follower; optionally enables Teleop override if leader is calibrated.
- Prompts to authenticate with HuggingFace (required to download remote models).
- Enter `policy_path` (HuggingFace model ID or local path), task description, and duration.
- Set up cameras (optional) and start inference.

### Tips/Notes
- If Teleop override is enabled, moving the leader arm temporarily overrides the policy.
- Same keyboard controls apply as in recording (→/←/ESC) for session control.
- If ports change, the tool can detect new ports and retry once.

---

## Cameras and ports

- **Ports**: Auto-detection works on Windows and Unix. If `pyserial` is missing, it is installed automatically. If the arm was already connected, you'll be guided to unplug/replug to identify the correct port.
- **Cameras**: Both OpenCV and RealSense cameras are supported. RealSense requires `pyrealsense2`. You can map each camera to a viewing angle and pick which ones to display during Teleop/Record/Inference.

## Troubleshooting

- **Connection failed / wrong port**: The tool will attempt to re-detect ports and retry once. If it still fails, unplug/replug each arm and re-run the mode.
- **Dataset already exists**: You will be prompted to resume or rename. Resuming continues appending episodes to the existing dataset.
- **HuggingFace authentication required**: Needed for downloading trained policies (Inference) and optionally for pushing datasets/models (Record/Train).
- **Windows symlink warnings**: Symlink warnings are suppressed for HF Hub downloads by the tool when needed.
- **No cameras detected**: You can proceed without cameras; functionality remains available.

