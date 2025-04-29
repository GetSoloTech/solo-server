# Solo Server

<div align="center">

<img src="assets/logo/logo.png" alt="Solovision Logo" width="200"/>

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/pypi/l/solo-server)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/solo-server)](https://pypi.org/project/solo-server/)
[![PyPI - Version](https://img.shields.io/pypi/v/solo-server)](https://pypi.org/project/solo-server/)

Solo Server is a lightweight and performant server for Physical AI inference.

</div>


```bash
# Install the solo-server package using pip
pip install solo-server

# Run the solo server setup in simple mode
solo setup
```
<div align="center" style={{ marginTop: "20px" }}>
  <video width="900" controls>
    <source src="https://github.com/user-attachments/assets/343fa749-13c4-40b9-abc4-37c8e91f76b3" type="video/mp4" />
    Your browser does not support the video tag.
  </video>
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

### **🔹 Install Solo Server**
```sh
# Install Solo-Server
pip install solo-server
```

Run the **interactive setup** to configure Solo Server:
```sh
# Setup Solo-Server
solo setup
```
### **🔹 Setup Features**
✔️ **Detects CPU, GPU, RAM** for **hardware-optimized execution**  
✔️ **Auto-configures `solo.conf` with optimal settings**  
✔️ **Recommends the compute backend OCI (CUDA, HIP, SYCL, Vulkan, CPU, Metal)**  

---

```sh
╭────────────────── System Information ──────────────────╮
│ Operating System: Windows                              │
│ CPU: AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD │
│ CPU Cores: 8                                           │
│ Memory: 15.42GB                                        │
│ GPU: NVIDIA                                            │
│ GPU Model: NVIDIA GeForce GTX 1660 Ti                  │
│ GPU Memory: 6144.0GB                                   │
│ Compute Backend: CUDA                                  │
╰────────────────────────────────────────────────────────╯

🖥️  Detected GPU: NVIDIA GeForce GTX 1660 Ti (NVIDIA)
✅ NVIDIA GPU drivers and toolkit are correctly installed.
Would you like to use GPU for inference? [y/n] (y): y

🏢 Choose the domain that best describes your field:
  1. Personal
  2. Education
  3. Agriculture
  4. Software
  5. Healthcare
  6. Forensics
  7. Robotics
  8. Enterprise
  9. Custom
Enter the number of your domain (1):
```
## **Commands**
```
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ setup      Set up Solo Server environment with interactive prompts and saves configuration to config.json.                     │
│ serve      Start a model server with the specified model.                                                                      │
│ status     Check running models, system status, and configuration.                                                             │
│ list       List all downloaded models available in HuggingFace cache and Ollama.                                               │
│ test       Test if the Solo server is running correctly. Performs an inference test to verify server functionality.            │
│ stop       Stops Solo Server services. If a server type is specified (e.g., 'ollama', 'vllm', 'llama.cpp'), only that specific │
│            service will be stopped. Otherwise, all Solo services will be stopped.                                              │
│ download   Downloads a Hugging Face model using the huggingface repo id.                                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```
### **Serve a Model**
```sh
solo serve -s ollama -m llama3.2
```
```
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --model   -m      TEXT     Model name or path. Can be: - HuggingFace repo ID (e.g., 'meta-llama/Llama-3.2-1B-Instruct') -      │
│                            Ollama model Registry (e.g., 'llama3.2') - Local path to a model file (e.g., '/path/to/model.gguf') │
│                            If not specified, the default model from configuration will be used.                                │
│                            [default: None]                                                                                     │
│ --server  -s      TEXT     Server type (ollama, vllm, llama.cpp) [default: None]                                               │
│ --port    -p      INTEGER  Port to run the server on [default: None]                                                           │
│ --ui                       Start the UI for the server [default: True]                                                         │
│ --help                     Show this message and exit.                                                                         │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### **List Available Models**
View all downloaded models in your HuggingFace cache and Ollama:

```sh
solo list
```
### **Stop Solo Server**
```sh
solo stop 
```
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

## 📝 Contributions 
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

