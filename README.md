# Solo Server

<div align="center">

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/pypi/l/solo-server)](https://opensource.org/licenses/MIT)
[![PyPI Version](https://img.shields.io/pypi/v/solo-server)](https://pypi.org/project/solo-server/)

**Production-ready server for Physical AI inference with FastMCP integration**

Add specialized AI capabilities to any inference server with modular Python components

</div>

## Quick Start

```bash
# Install and setup
pip install solo-server

# Or Install from github repo
git clone https://github.com/GetSoloTech/solo-server.git
cd solo-server
pip install -e .

# Start server with SML models
solo serve --server ollama --model llama3.2 --mcp CropHealthMCP --mcp VitalSignsMCP

## Developer Setup

```bash
# Install and setup
uv install solo-server

# Or Install from github repo
git clone https://github.com/GetSoloTech/solo-server.git
cd solo-server
pip install -e .

# Solo Commands
solo --help

# Start lerobot with solo
solo robo --type lerobot
```


## Interactive Lerobot With Solo Server
```bash
# Motors (both) → Calibrate (both) → Teleop
solo robo --type lerobot --motors both
solo robo --type lerobot --calibrate both
solo robo --type lerobot --teleop

# Record a new local dataset with prompts
solo robo --type lerobot --record

# Train Diffusion Policy on a recorded dataset and push to Hub
solo robo --type lerobot --train

# Inference with a hub model id (with optional Teleop override)
solo robo --type lerobot --inference
```

Find more details here: [Solo Robo Documentation](solo_server/commands/robots/lerobot/README.md) 

## What is FastMCP?

FastMCP lets you attach specialized AI modules to any inference server. Each module handles specific tasks like medical imaging, crop analysis, or robot control through a simple Python API.

**Benefits:**
- **Modular**: Add capabilities without rebuilding your system
- **Production Ready**: Built-in monitoring, scaling, error handling
- **50+ Pre-built Modules**: Ready-to-use for common Physical AI tasks
- **Simple API**: Easy to create custom modules


## Creating FastMCP Modules

Simple Python API for custom modules:

```python
from pydantic import BaseModel
from litserve.mcp import MCP
import litserve as ls

class AnalysisRequest(BaseModel):
    data_path: str
    threshold: float = 0.5

class CustomMCP(ls.LitAPI):
    def setup(self, device: str):
        self.model = self.load_model()
        
    def decode_request(self, request: AnalysisRequest):
        return {"data": request.data_path, "threshold": request.threshold}
        
    def predict(self, inputs: dict):
        # Your inference logic here
        result = self.model.process(inputs["data"])
        return {"result": result, "confidence": 0.95}
        
    def encode_response(self, output: dict):
        return {"result": output["result"], "confidence": output["confidence"]}

# Package and publish
if __name__ == "__main__":
    mcp = MCP(name="CustomMCP", version="1.0.0")
    api = CustomMCP(mcp=mcp)
    server = ls.LitServer(api, port=8001)
    server.run()
```

## MCP Module Catalog

### Medical & Healthcare (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
| **VitalSignsMCP** | Real-time patient monitoring | Sensor streams, video | Heart rate, SpO2, alerts | ICU monitoring, telemedicine | Free |
| **MedicalImagingMCP** | CT/MRI/X-ray analysis | Medical scans | Diagnosis, annotations | Radiology, emergency medicine | Free |
| **RehabTrackingMCP** | Physical therapy progress | Motion capture | Exercise tracking, recovery metrics | Physical therapy, sports medicine | Free |
| **SurgicalGuidanceMCP** | OR instrument tracking | Video feeds, RFID | Tool identification, workflow | Operating room management | Pro |
| **DrugInteractionMCP** | Medication safety analysis | Prescription data | Interaction warnings, dosing | Pharmacy, clinical decision support | Pro |

### Agricultural & Environment (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
| **CropHealthMCP** | Precision agriculture analysis | Drone imagery, sensors | Disease detection, yield prediction | Farm management, crop insurance | Free |
| **SoilAnalysisMCP** | Soil condition monitoring | Sensor networks | pH, nutrients, moisture levels | Precision farming, sustainability | Free |
| **WeatherPredictionMCP** | Localized weather forecasting | Meteorological data | Micro-climate predictions | Irrigation planning, harvest timing | Free |
| **LivestockManagementMCP** | Animal health and tracking | RFID, cameras, sensors | Health status, location, behavior | Ranch management, veterinary care | Pro |
| **SupplyChainMCP** | Agricultural logistics | Market data, inventory | Pricing, routing, demand forecasting | Food distribution, commodity trading | Pro |

### Industrial & Manufacturing (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
| **PredictiveMaintenanceMCP** | Equipment failure prediction | Vibration, thermal, acoustic | Failure alerts, maintenance schedules | Manufacturing, oil & gas | Free |
| **QualityControlMCP** | Automated defect detection | Product images, measurements | Pass/fail, defect classification | Assembly lines, quality assurance | Free |
| **EnergyOptimizationMCP** | Smart power management | Smart meters, usage patterns | Cost reduction, efficiency gains | Factory automation, green manufacturing | Free |
| **RoboticsControlMCP** | Multi-robot coordination | Robot states, task queues | Work allocation, path planning | Automated warehouses, assembly | Pro |
| **DigitalTwinMCP** | Real-time process mirroring | Production telemetry | Performance insights, optimization | Process industries, smart factories | Pro |

### Robotics & Automation (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
| **NavigationMCP** | SLAM and path planning | LiDAR, cameras, IMU | Maps, waypoints, obstacle avoidance | Autonomous vehicles, service robots | Free |
| **ManipulationMCP** | Object detection and grasping | RGB-D cameras | Grasp poses, object properties | Pick-and-place, warehouse automation | Free |
| **HumanRobotMCP** | Social interaction and safety | Cameras, microphones | Emotion recognition, voice commands | Service robots, eldercare | Free |
| **SwarmControlMCP** | Multi-agent coordination | Network communications | Formation control, task allocation | Drone swarms, distributed robotics | Pro |
| **AutonomousVehicleMCP** | Self-driving capabilities | Vehicle sensors | Steering, braking, route planning | Autonomous cars, delivery robots | Pro |

### Educational & Research (5 modules)

| Module | Description | Input | Output | Use Case | Availability |
|--------|-------------|--------|--------|----------|--------------|
| **LearningAnalyticsMCP** | Student performance tracking | Interaction data, assessments | Progress insights, recommendations | Online education, skill assessment | Free |
| **LabAssistantMCP** | Scientific experiment guidance | Protocols, sensor data | Step-by-step instructions, safety alerts | Research labs, STEM education | Free |
| **AccessibilityMCP** | Inclusive learning support | Text, audio, video | Translations, adaptations | Special needs education, language learning | Free |
| **ResearchAutomationMCP** | Data analysis and hypothesis generation | Research datasets | Statistical insights, literature reviews | Academic research, R&D | Pro |
| **VirtualTutorMCP** | Personalized instruction | Learning patterns, preferences | Adaptive curricula, feedback | Personalized education, corporate training | Pro |

## API Reference

### Primary Server (OpenAI Compatible)

```bash
# Chat with MCP integration
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Analyze sensor data"}],
    "tools": [{"type": "mcp", "name": "VitalSignsMCP"}]
  }'

# Direct MCP module access
curl http://localhost:8080/mcp/CropHealthMCP/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/drone_image.jpg"}'
```

### MCP Module Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/{module}/health` | GET | Module health check |
| `/mcp/{module}/info` | GET | Module information |
| `/mcp/{module}/predict` | POST | Single prediction |
| `/mcp/{module}/batch` | POST | Batch predictions |

## Configuration

```yaml
# solo.conf
server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

compute:
  backend: "ollama"
  device: "auto"

models:
  default: "llama3.2"
  cache_dir: "~/.cache/solo-server"

mcp:
  enabled: true
  registry_url: "https://registry.solotech.ai"
```

## Deployment

### Docker

```yaml
# docker-compose.yml
version: '3.8'
services:
  solo-server:
    image: solotech/solo-server:latest
    ports:
      - "8080:8080"
    volumes:
      - ./models:/app/models
      - ./config:/app/config
    environment:
      - SOLO_COMPUTE_DEVICE=auto
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: solo-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: solo-server
        image: solotech/solo-server:latest
        ports:
        - containerPort: 8080
        resources:
          limits:
            nvidia.com/gpu: 1
```

## Edge Deployment & Quantization

Solo Server supports automatic model quantization and optimization for different edge deployment scenarios:

### Quantization Export Options

```bash
# Export with automatic quantization for target device
solo export --model llama3.2 --target jetson-nano --format onnx
solo export --model llama3.2 --target raspberry-pi --format tflite
solo export --model llama3.2 --target cpu-optimized --format openvino

# Manual quantization settings
solo export --model llama3.2 --quantization int8 --format ggml
solo export --model llama3.2 --quantization fp16 --format tensorrt --batch-size 1
```

### Edge Deployment Configurations

| Target Platform | Quantization | Format | Memory Usage | Throughput | Use Case |
|-----------------|--------------|--------|--------------|------------|----------|
| **NVIDIA Jetson Nano** | INT8 | TensorRT | 2GB | 15 tok/s | Robotics, IoT |
| **NVIDIA Jetson Xavier** | FP16 | TensorRT | 4GB | 45 tok/s | Autonomous vehicles |
| **Raspberry Pi 4** | INT8 | ONNX | 1GB | 3 tok/s | Home automation |
| **Intel NUC** | INT8 | OpenVINO | 4GB | 25 tok/s | Edge computing |
| **Apple M1/M2** | FP16 | CoreML | 3GB | 60 tok/s | Local development |
| **Google Coral** | INT8 | TFLite | 512MB | 8 tok/s | Embedded vision |
| **AMD Ryzen Embedded** | INT8 | ONNX | 2GB | 20 tok/s | Industrial control |
| **Qualcomm Snapdragon** | INT8 | SNPE | 1GB | 12 tok/s | Mobile devices |

### Edge-Optimized MCP Modules

```bash
# Deploy lightweight MCP modules for edge
solo mcp install CropHealthMCP --target edge --quantization int8
solo mcp install VitalSignsMCP --target jetson --optimization fast

# Edge deployment with resource constraints
solo serve --model llama3.2-edge --mcp CropHealthMCP \
  --memory-limit 2GB --cpu-cores 2 --edge-mode
```

### Edge Configuration Examples

```yaml
# jetson-config.yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 2

compute:
  backend: "tensorrt"
  device: "cuda"
  memory_limit: "2GB"
  optimization_level: "edge"

models:
  default: "llama3.2-int8"
  quantization: "int8"
  max_batch_size: 1

mcp:
  enabled: true
  edge_optimized: true
  memory_efficient: true
```

```yaml
# raspberry-pi-config.yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 1

compute:
  backend: "onnx"
  device: "cpu"
  memory_limit: "1GB"
  optimization_level: "ultra_edge"

models:
  default: "llama3.2-quantized"
  quantization: "int8"
  max_batch_size: 1
  cpu_threads: 4

mcp:
  enabled: true
  modules: ["VitalSignsMCP-lite"]
  edge_optimized: true
```

## Development

```bash
# Setup development environment
git clone https://github.com/GetSoloTech/solo-server.git
cd solo-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request

