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
- **Lean Load Testing:** Built-in commands to benchmark endpoints
- **Cross-Platform Compatibility:** Deploy AI models effortlessly on your hardware
- **Configurable Framework:** Auto-detect hardware (CPU, GPU, RAM) and sets configs


## Table of Contents

- [Features](#-features)
- [Installation](#installation)
- [Commands](#commands)
- [Supported Models](#supported-models)
- [Configuration](#configuration)
- [Project Inspiration](#project-inspiration)

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

### **🔹 Install in Dev Mode**
```sh
# Clone the repository
git clone https://github.com/GetSoloTech/solo-server.git

# Navigate to the directory
cd solo-server

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/MacOS
# OR
.venv\Scripts\activate     # Windows

# Install in editable mode
pip install -e .
```
Run the **interactive setup** to configure Solo Server:
```sh
solo setup
```
### **🔹 Setup Features**
✔️ **Detects CPU, GPU, RAM** for **hardware-optimized execution**  
✔️ **Auto-configures `solo.conf` with optimal settings**  
✔️ **Requests API keys for Ngrok and Replicate**  
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
---

## REST API

You can now use the API endpoint created by the Solo Server to interact with the model. You can send a POST request to `http://localhost:11434/api/chat` with a JSON payload containing the model name and the messages you want to send to the model.

### Generate a response

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt":"Why is the sky blue?"
}'
```

### Chat with a model

```shell
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    { "role": "user", "content": "why is the sky blue?" }
  ]
}'
```

## Diagram

```
+-------------------+
|                   |
|    solo serve     |
|                   |
+---------+---------+
          |
          |
          |           +------------------+           +----------------------+
          |           | Pull inferencing |           |   Pull model layer   |
          +-----------| runtime (cuda)   |---------->|       llama3.2       | 
                      +------------------+           +----------------------+
                                                     |     Repo options     |
                                                     ++-----------+--------++
                                                      |           |        |
                                                      v           v        v
                                                +----------+ +----------+ +-------------+
                                                | Ollama   | | vLLM     | | Llama.cpp   |
                                                | Registry | | registry | |  Registry   |
                                                +-----+------+---+------+-++------------+
                                                      |          |         |
                                                      v          v         v
                                                      +---------------------+
                                                      |   Start with        |
                                                      |   cuda runtime      |
                                                      |   and               |
                                                      |   llama3.2          |
                                                      +---------------------+
```
---

### **Check Model Status**
```sh
solo status
```
**Example Output:**
```sh
🔹 Running Models:
-------------------------------------------
| Name      | Model   | Backend | Port |
|----------|--------|---------|------|
| llama3   | Llama3 | CUDA    | 8080 |
| gptj     | GPT-J  | CPU     | 8081 |
-------------------------------------------
```

---

### **Stop a Model**
```sh
solo stop 
```
**Example Output:**
```sh
🛑 Stopping Solo Server...
✅ Solo server stopped successfully.
```

---

## Supported Models
Solo Server supports **multiple model sources**, including **Ollama & Hugging Face**.

| **Model Name**         | **Source**                                                |
|------------------------|----------------------------------------------------------|
| **DeepSeek R1**        | `ollama://deepseek-r1`                                   |
| **IBM Granite 3.1**    | `ollama://granite3.1-dense`                              |
| **Granite Code 8B**    | `hf://ibm-granite/granite-8b-code-base-4k-GGUF`          |
| **Granite Code 20B**   | `hf://ibm-granite/granite-20b-code-base-8k-GGUF`         |
| **Granite Code 34B**   | `hf://ibm-granite/granite-34b-code-base-8k-GGUF`         |
| **Mistral 7B**         | `hf://TheBloke/Mistral-7B-Instruct-v0.2-GGUF`            |
| **Mistral 7B v3**      | `hf://MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF`       |
| **Hermes 2 Pro**       | `hf://NousResearch/Hermes-2-Pro-Mistral-7B-GGUF`        |
| **Cerebrum 1.0 7B**    | `hf://froggeric/Cerebrum-1.0-7b-GGUF`                    |
| **Dragon Mistral 7B**  | `hf://llmware/dragon-mistral-7b-v0`                      |


## **⚙️ Configuration (`solo.json`)**
After setup, all settings are stored in:
```sh
~/.solo_server/solo.json
```
Example:
```ini
# Solo Server Configuration

{
    "hugging_face": {
        "token": ""
    },
    "system_info": {
        "os": "Windows",
        "cpu_model": "AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD",
        "cpu_cores": 8,
        "memory_gb": 15.42,
        "gpu_vendor": "NVIDIA",
        "gpu_model": "NVIDIA GeForce GTX 1660 Ti",
        "gpu_memory": 6144.0,
        "compute_backend": "CUDA"
    },
    "starfish": {
        "api_key": ""
    },
    "hardware": {
        "use_gpu": true
    }
}
```
---

## 📝 Example App 
Refer example_apps for sample applications.
1. [ai-chat](https://github.com/GetSoloTech/solo-server/tree/main/example_apps/ai-chat)

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
* llamafile
* cog

Like using Solo, consider leaving us a ⭐ on GitHub
