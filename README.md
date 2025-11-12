# Solo CLI

<div align="center">

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/license/apache-2-0)
[![PyPI Version](https://img.shields.io/pypi/v/solo-server)](https://pypi.org/project/solo-server/)

**Fastest way to deploy Physical AI on your hardware**

CLI for Solo-Server:
*Serving models in the physical world; optimized for on-device operation*

</div>

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="media/LeRobot_Chess.png" alt="LeRobot Chess Match Screenshot" title="LeRobot Chess Match" width="375" height="225"></td>
      <td align="center"><img src="media/LeRobot_Writer.png" alt="LeRobot Writer Screenshot" title="LeRobot Author" width="375" height="225"></td>
    </tr>
  </table>
</div>

## Solo-CLI

Solo-CLI powers users of Physical AI Inference by providing access to efficiency tuned AI models in the real world. From language to vision to action models, Solo-CLI allows you to interact with cutting-edge, on-device AI directly within the terminal. It is tailored for context aware intelligence, specialized for mission-critical tasks, and tuned for the edge.

<p align="center">
  <a href="https://docs.getsolo.tech">Docs</a> |
  <a href="getsolo.tech">About</a>
</p>

## Features & MCP Module Catalog

### Medical & Healthcare (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
|🫀 **VitalSignsMCP** | Real-time patient monitoring | Sensor streams, video | Heart rate, SpO2, alerts | ICU monitoring, telemedicine | Free |
|🩻 **MedicalImagingMCP** | CT/MRI/X-ray analysis | Medical scans | Diagnosis, annotations | Radiology, emergency medicine | Free |
|💪🏾 **RehabTrackingMCP** | Physical therapy progress | Motion capture | Exercise tracking, recovery metrics | Physical therapy, sports medicine | Free |
|💉 **SurgicalGuidanceMCP** | OR instrument tracking | Video feeds, RFID | Tool identification, workflow | Operating room management | Pro |
|💊 **DrugInteractionMCP** | Medication safety analysis | Prescription data | Interaction warnings, dosing | Pharmacy, clinical decision support | Pro |


### Agricultural & Environment (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
|🫛 **CropHealthMCP** | Precision agriculture analysis | Drone imagery, sensors | Disease detection, yield prediction | Farm management, crop insurance | Free |
|🪴 **SoilAnalysisMCP** | Soil condition monitoring | Sensor networks | pH, nutrients, moisture levels | Precision farming, sustainability | Free |
|🌦️ **WeatherPredictionMCP** | Localized weather forecasting | Meteorological data | Micro-climate predictions | Irrigation planning, harvest timing | Free |
|🐄 **LivestockManagementMCP** | Animal health and tracking | RFID, cameras, sensors | Health status, location, behavior | Ranch management, veterinary care | Pro |
|📦 **SupplyChainMCP** | Agricultural logistics | Market data, inventory | Pricing, routing, demand forecasting | Food distribution, commodity trading | Pro |


### Industrial & Manufacturing (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
|🔩 **PredictiveMaintenanceMCP** | Equipment failure prediction | Vibration, thermal, acoustic | Failure alerts, maintenance schedules | Manufacturing, oil & gas | Free |
|✅ **QualityControlMCP** | Automated defect detection | Product images, measurements | Pass/fail, defect classification | Assembly lines, quality assurance | Free |
|⚡️ **EnergyOptimizationMCP** | Smart power management | Smart meters, usage patterns | Cost reduction, efficiency gains | Factory automation, green manufacturing | Free |
|🦾 **RoboticsControlMCP** | Multi-robot coordination | Robot states, task queues | Work allocation, path planning | Automated warehouses, assembly | Pro |
|🤖 **DigitalTwinMCP** | Real-time process mirroring | Production telemetry | Performance insights, optimization | Process industries, smart factories | Pro |


### Robotics & Automation (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
|🛣️ **NavigationMCP** | SLAM and path planning | LiDAR, cameras, IMU | Maps, waypoints, obstacle avoidance | Autonomous vehicles, service robots | Free |
|🦿 **ManipulationMCP** | Object detection and grasping | RGB-D cameras | Grasp poses, object properties | Pick-and-place, warehouse automation | Free |
|👤 **HumanRobotMCP** | Social interaction and safety | Cameras, microphones | Emotion recognition, voice commands | Service robots, eldercare | Free |
|🐝 **SwarmControlMCP** | Multi-agent coordination | Network communications | Formation control, task allocation | Drone swarms, distributed robotics | Pro |
|🚘 **AutonomousVehicleMCP** | Self-driving capabilities | Vehicle sensors | Steering, braking, route planning | Autonomous cars, delivery robots | Pro |


### Educational & Research (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
|📝 **LearningAnalyticsMCP** | Student performance tracking | Interaction data, assessments | Progress insights, recommendations | Online education, skill assessment | Free |
|🥼 **LabAssistantMCP** | Scientific experiment guidance | Protocols, sensor data | Step-by-step instructions, safety alerts | Research labs, STEM education | Free |
|🧏🏼‍♀️ **AccessibilityMCP** | Inclusive learning support | Text, audio, video | Translations, adaptations | Special needs education, language learning | Free |
|👨🏻‍🔬 **ResearchAutomationMCP** | Data analysis and hypothesis generation | Research datasets | Statistical insights, literature reviews | Academic research, R&D | Pro |
|👩🏻‍🏫 **VirtualTutorMCP** | Personalized instruction | Learning patterns, preferences | Adaptive curricula, feedback | Personalized education, corporate training | Pro |

## Installation
First, install the uv package manager and setup a virtual environment as 
explained in [prereq.md](prereq.md)

```bash

#Choose one of the following for solo-server installation
#1. Install solo server from PyPI python manager
uv pip install solo-server

#2. Install solo server from source
git clone https://github.com/GetSoloTech/solo-server.git
cd solo-server
uv pip install -e .

# Solo commands
solo --help

```

## 💻 Solo Tech Installation Demo

![Solo Tech Installation Demo](media/SoloTechInstallationGIF.gif)

---

**For the full video, [click here to watch on YouTube](https://www.youtube.com/embed/x2pVuYr08vk).** 

## Quick Installation for Mac (Automated)

For Mac users, we provide an automated installation script that handles all the setup steps:

```bash
# Clone the repository
git clone https://github.com/GetSoloTech/solo-server.git
cd solo-server

# Make the installation script executable
chmod +x install_mac.sh

# Run the automated installation
./install_mac.sh
```

The script will automatically:
- Install uv package manager (version 0.9.3)
- Create a virtual environment with Python 3.12.12
- Set up environment variables for dependencies
- Install solo-server in development mode with fallback handling for mujoco dependencies

After installation, activate the virtual environment:
```bash
source solo_venv/bin/activate
```

<!-- <details>
<summary><strong>Video: quickstart installation</strong></summary>

[![Video: Mac Quickstart Installation](media/MacQuickInstallThumbnail.png)](https://youtu.be/bGjaIfKvyAA)

</details> -->


## 💻 Quick Installation Demo

![Mac Quickstart Installation Demo](media/MacQuickInstallGIF.gif)

---

**For the full video, [click here to watch on YouTube](https://www.youtube.com/watch?v=bGjaIfKvyAA).** 

## Solo Commands:

```bash
solo --help
                                                                                                           
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ setup      Set up Solo Server environment with interactive prompts and saves configuration to config.json.           │
│ robo       Robotics operations: motor setup, calibration, teleoperation, data recording, training, and inference     │
│ serve      Start a model server with the specified model.                                                            │
│ status     Check running models, system status, and configuration.                                                   │
│ list       List all downloaded models available in HuggingFace cache and Ollama.                                     │
│ test       Test if the Solo server is running correctly. Performs an inference test to verify server functionality.  │
│ stop       Stops Solo Server services. You can specify a server type with 'ollama', 'vllm', or 'llama.cpp'           │
│            Otherwise, all Solo services will be stopped.                                                             │
│ download   Downloads a Hugging Face model using the huggingface repo id.                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```
## Start server with SML models

```bash

# Note that you will need Docker for solo serve
solo setup
solo serve --server ollama --model llama3.2:1b
```

## Interactive Lerobot With Solo Server
Find more details here: [Solo Robo Documentation](solo_server/commands/robots/lerobot/README.md) 

```bash
# Motors (both) → Calibrate (both) → Teleop
solo robo --motors all
solo robo --calibrate all
solo robo --teleop

# Record a new local dataset with prompts
solo robo --record

# Train ACT or SmolVLA Policy on a recorded dataset and push to Hub
solo robo --train

# Inference with a hub model id (with optional Teleop override)
solo robo --inference
```

## API Reference
Find more details here: OpenAI -> [OpenAI API Docs](https://platform.openai.com/docs/api-reference/introduction) Ollama -> [Ollama API Docs](https://docs.ollama.com/api)

### vLLM & llama.cpp (OpenAI Compatible)

```bash
# Chat request endpoint
curl http://localhost:5070/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Analyze sensor data"}],
    "tools": [{"type": "mcp", "name": "VitalSignsMCP"}]
  }'
```

### Ollama
```bash
# Chat request endpoint
curl http://localhost:5070/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "why is the sky blue?"
    }
  ]
}'
```

## Configuration
Navigate to config file
`.solo_server/config.json` 

```json
{
    "hardware": {
        "use_gpu": false,
        "cpu_model": "Apple M3",
        "cpu_cores": 8,
        "memory_gb": 16.0,
        "gpu_vendor": "None",
        "gpu_model": "None",
        "gpu_memory": 0,
        "compute_backend": "CPU",
        "os": "Darwin"
    },
    "user": {
        "domain": "Software",
        "role": "Full-Stack Developer"
    },
    "server": {
        "type": "ollama",
        "ollama": {
            "default_port": 5070
        }
    },
    "active_model": {
        "server": "ollama",
        "name": "llama3.2:1b",
        "full_model_name": "llama3.2:1b",
        "port": 5070,
        "last_used": "2025-10-09 11:30:06"
    }
}
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request 
