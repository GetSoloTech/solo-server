## Prerequisites

```bash

# uv package manager installation, skip if uv already exists
# Mac & Linux
curl -LsSf https://astral.sh/uv/install.sh | sh  
# Windows Powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create Python virtual environment, recommended Python version 3.12
uv venv --python 3.12
# Mac & Linux
source .venv/bin/activate
# Windows
source .venv/scripts/activate

```