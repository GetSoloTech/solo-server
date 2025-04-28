# Solo Server

<div align="center">

<img src="assets/logo/logo.png" alt="Solovision Logo" width="200"/>

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/pypi/l/solo-server)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/solo-server)](https://pypi.org/project/solo-server/)
[![PyPI - Version](https://img.shields.io/pypi/v/solo-server)](https://pypi.org/project/solo-server/)

Solo Server is a lightweight server to manage hardware aware inference.

</div>


```bash
# Install the solo-server package using pip
pip install solo-server

# Run the solo server setup in simple mode
solo setup
```
<div align="center">
  <img src="assets/logo/solostart.gif" alt="SoloStart">
</div>


## Features

- **Seamless Setup:** Manage your on device AI with a simple CLI and HTTP servers
- **Open Model Registry:** Pull models from registries like  Ollama & Hugging Face
- **Cross-Platform Compatibility:** Deploy AI models effortlessly on your hardware
- **Configurable Framework:** Auto-detect hardware (CPU, GPU, RAM) and sets configs


## Table of Contents

- [Features](#-features)
- [Installation](#installation)
- [Commands](#commands)
- [Contribution](#contribution)
- [ Inspiration](#inspiration)

## Installation

### **🔹Prerequisites** 

- **🐋 Docker:** Required for containerization 
  - [Install Docker](https://docs.docker.com/get-docker/)

### **🔹 Install with `uv` (Recommended)**
Install 'uv' using these docs:
https://docs.astral.sh/uv/getting-started/installation/
```sh
# Install uv
# On Windows (PowerShell)
iwr https://astral.sh/uv/install.ps1 -useb | iex
# If you have admin use, consider: https://github.com/astral-sh/uv/issues/3116
powershell -ExecutionPolicy Bypass -c "pip install uv" 

# On Unix/MacOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Unix/MacOS
# OR
.venv\Scripts\activate     # On Windows
```
```
uv pip install solo-server
```
Creates an isolated environment using `uv` for performance and stability.

Run the **interactive setup** to configure Solo Server:
```sh
solo setup
```
### **🔹 Setup Features**
✔️ **Detects CPU, GPU, RAM** for **hardware-optimized execution**  
✔️ **Auto-configures `solo.conf` with optimal settings**  
✔️ **Recommends the compute backend OCI (CUDA, HIP, SYCL, Vulkan, CPU, Metal)**  

---

**Example Output:**
```sh
╭────────────────── System Information ──────────────────╮
│ Operating System: Windows │
│ CPU: AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD │
│ CPU Cores: 8 │
│ Memory: 15.42GB │
│ GPU: NVIDIA │
│ GPU Model: NVIDIA GeForce GTX 1660 Ti │
│ GPU Memory: 6144.0GB │
│ Compute Backend: CUDA │
╰────────────────────────────────────────────────────────╯
🔧 Starting Solo Server Setup...
📊 Available Server Options:
• Ollama
• vLLM
• Llama.cpp

✨ Ollama is recommended for your system
Choose server [ollama]:
```

---
## **Solo Server Block Diagram**
<div align="center">
  <img src="assets/Solo Server.svg" width="1000"/>
</div>

## **Commands**
---

### **Serve a Model**
```sh
solo serve -s ollama -m llama3.2
```

**Command Options:**
```
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --server  -s      TEXT     Server type (ollama, vllm, llama.cpp) [default: ollama]                                  │
│ --model   -m      TEXT     Model name or path [default: None]                                                       │
│ --port    -p      INTEGER  Port to run the server on [default: None]                                                │
│ --help                     Show this message and exit.                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### **Test Inference**
The test command checks if your Solo server is running correctly by performing a live inference test against your active model. It automatically detects your active model and server type from the configuration.

```sh
solo test
```

To modify the request timeout for slower models:
```sh
solo test --timeout 120
```

**Example Output:**
```
Testing Solo server connection...
Checking server at http://localhost:5070...
Testing inference  [####################################]  100%
✅ Server is running and responded to inference request
Model  - llama3.2:1b
URL    - http://localhost:5070
Inference time: 64.51 seconds

Test prompt: What is machine learning? Keep it very brief.
Response:
Machine learning is a subset of artificial intelligence that enables computers to learn from data, make predictions or decisions without being explicitly programmed. It involves algorithms that analyze patterns and relationships in data, allowing machines to improve their performance over time.
```
---

## REST API

Solo Server provides consistent REST API endpoints across different server types (Ollama, vLLM, llama.cpp). The exact API endpoint and format differs slightly depending on which server type you're using.

### API Endpoints by Server Type

#### Ollama API 

```shell
# Generate a response
curl http://localhost:5070/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

# Chat with a model
curl http://localhost:5070/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    { "role": "user", "content": "why is the sky blue?" }
  ]
}'
```

#### vLLM and llama.cpp API 
Both use OpenAI-compatible endpoints:

```shell
# Chat completion
curl http://localhost:5070/v1/chat/completions -d '{
  "model": "llama3.2",
  "messages": [
    { "role": "user", "content": "Why is the sky blue?" }
  ],
  "max_tokens": 50,
  "temperature": 0.7
}'

# Text completion
curl http://localhost:5070/v1/completions -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "max_tokens": 50,
  "temperature": 0.7
}'
```

### **List Available Models**
View all downloaded models in your HuggingFace cache and Ollama:

```sh
solo list
```

**Example Output:**
```
🔍 Scanning for available models...
                              HuggingFace Models                               
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ MODEL                                        ┃ SIZE      ┃ LAST MODIFIED    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF │ 1.04 GB   │ 2025-04-25 17:13 │
│ bartowski/Llama-3.2-1B-Instruct-GGUF         │ 770.28 MB │ 2025-04-24 23:28 │
│ GetSoloTech/gemma-3-1b-endocronology         │ 1.86 GB   │ 2025-04-21 22:02 │
│ GetSoloTech/Llama-3.2-1B-Endocronology       │ 2.30 GB   │ 2025-04-24 23:07 │
│ GetSoloTech/Llama-3.2-1B-Endocronology-GGUF  │ 770.28 MB │ 2025-04-24 23:30 │
│ GetSoloTech/Llama-3.2-3B-Reasoning           │ 0.00 B    │ 2025-04-16 10:03 │
│ meta-llama/Llama-3.2-1B-Instruct             │ 2.30 GB   │ 2025-04-25 10:29 │
│ unsloth/Llama-3.2-1B-Instruct                │ 2.30 GB   │ 2025-04-25 11:02 │
└──────────────────────────────────────────────┴───────────┴──────────────────┘
                                    Ollama Models
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ NAME                                              ┃ SIZE   ┃ MODIFIED     ┃ TAGS   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━┩
│ hf.co/GetSoloTech/Llama-3.2-1B-Endocronology-GGUF │ 807 MB │ 2 days ago   │ Q4_K_M │
│ endor                                             │ 1.1 GB │ 7 days ago   │ latest │
│ hf.co/GetSoloTech/gemma-3-1b-endocronology-GGUF   │ 1.1 GB │ 8 days ago   │ latest │
│ hf.co/GetSoloTech/Llama-3.2-3B-Reasoning-GGUF     │ 2.0 GB │ 12 days ago  │ latest │
│ llama3.2                                          │ 1.3 GB │ 4 weeks ago  │ 1b     │
│ hf.co/GetSoloTech/gemma-3-1b-it-GGUF              │ 1.1 GB │ 4 weeks ago  │ latest │
│ solo                                              │ 3.6 GB │ 2 months ago │ latest │
└───────────────────────────────────────────────────┴────────┴──────────────┴────────┘
```

This command:
- Scans your HuggingFace cache directory for model files (.bin, .gguf, .safetensors)
- Checks Ollama for downloaded models
- Displays detailed information including model size and last modified date

### **Check Model Status**
```sh
solo status
```
**Example Output:**
```sh
📊 Solo Server Configuration:
                                   Configuration                                   
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ CATEGORY ┃ PROPERTY         ┃ VALUE                                             ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Hardware │ CPU Model        │ AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD │
│ Hardware │ CPU Cores        │ 8                                                 │
│ Hardware │ Memory (GB)      │ 15.42                                             │
│ Hardware │ GPU Vendor       │ NVIDIA                                            │
│ Hardware │ GPU Model        │ NVIDIA GeForce GTX 1660 Ti                        │
│ Hardware │ GPU Memory       │ 6144.0                                            │
│ Hardware │ GPU Enabled      │ Yes                                               │
│ Hardware │ Operating System │ Windows                                           │
│          │                  │                                                   │
│ Server   │ Default Server   │ ollama                                            │
│ Server   │ Default Port     │ 5070                                              │
│ Server   │ Default Model    │ llama3.2:1b                                       │
│          │                  │                                                   │
│ User     │ Domain           │ Personal                                          │
│ User     │ Role             │ Student                                           │
└──────────┴──────────────────┴───────────────────────────────────────────────────┘

🚀 Running Services:
                     Running Services                      
┏━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ SERVICE ┃ MODEL       ┃ URL                   ┃ STATUS  ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Ollama  │ llama3.2:1b │ http://localhost:5070 │ Running │
└─────────┴─────────────┴───────────────────────┴─────────┘
```

---

### **Stop a Model**
```sh
solo stop 
```
**Example Output:**
```sh
🔍 Checking running Solo servers...
Found 1 running Solo services:
  • llama.cpp (PID: 21112)

🛑 Stopping Solo Server...
✅ Stopped llama.cpp (PID: 21112)
✅ Successfully stopped 1 Solo service.
```

## **⚙️ Configuration (`solo.json`)**
After setup, all settings are stored in:
```sh
~/.solo_server/solo.json
```
Example:
```ini
# Solo Server Configuration

{
    "hardware": {
        "use_gpu": true,
        "cpu_model": "AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD",
        "cpu_cores": 8,
        "memory_gb": 15.42,
        "gpu_vendor": "NVIDIA",
        "gpu_model": "NVIDIA GeForce GTX 1660 Ti",
        "gpu_memory": 6144.0,
        "compute_backend": "CUDA",
        "os": "Windows"
    },
    "user": {
        "domain": "Personal",
        "role": "Student"
    },
    "server": {
        "type": "ollama"
    },
    "active_model": {
        "server": "llama.cpp",
        "name": "llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "full_model_name": "bartowski/Llama-3.2-1B-Instruct-GGUF/llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "last_used": "2025-04-26 21:17:31"
    }
}
```
---

## 📝 Highlight Apps 
Refer example_apps for sample applications.
1. [ai-chat](https://github.com/GetSoloTech/solo-server/tree/main/example_apps/ai-chat)


### **🔹 To Contribute, Setup in Dev Mode**

```sh
# Clone the repository
git clone https://github.com/GetSoloTech/solo-server.git

# Navigate to the directory
cd solo-server

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/MacOS
# OR
.venv\Scripts\activate     # On Windows

# Install in editable mode
pip install -e .
```



## 📝 Project Inspiration 

This project wouldn't be possible without the help of other projects like:

* uv
* llama.cpp
* ramalama
* ollama
* whisper.cpp
* vllm
* podman
* huggingface
* aiaio
* llamafile
* cog

Like using Solo, consider leaving us a ⭐ on GitHub

