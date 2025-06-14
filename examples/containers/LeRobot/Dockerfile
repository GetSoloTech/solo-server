# LeRobot for Solo Server
# Decision: Use LeRobot's official Docker approach for ARM64 compatibility

# Start from simple base image (ARM64 compatible)
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

# Configure environment
ENV DEBIAN_FRONTEND=noninteractive
ENV MUJOCO_GL="egl"
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git \
    libglib2.0-0 libgl1-mesa-glx libegl1-mesa ffmpeg \
    libgeos-dev pkg-config \
    libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libswscale-dev libswresample-dev libavfilter-dev \
    && ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python \
    && python -m venv /opt/venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN /opt/venv/bin/pip install --upgrade --no-cache-dir pip wheel

# Clone LeRobot
RUN git clone --branch=main --depth=1 https://github.com/huggingface/lerobot.git /opt/lerobot
WORKDIR /opt/lerobot

# Install PyTorch CPU builds for ARM64 compatibility
RUN /opt/venv/bin/pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install LeRobot with feetech support for SO101
RUN /opt/venv/bin/pip install --no-cache-dir -e ".[feetech]"
    
# Solo Server endpoint integration
COPY examples/endpoints/lerobot/server.py /opt/lerobot/
COPY examples/endpoints/lerobot/model.py /opt/lerobot/

# Install LitServe for API
RUN /opt/venv/bin/pip install --no-cache-dir litserve>=0.2.0

# Configure server environment
ENV PORT=5070
ENV MOCK_HARDWARE=false
ENV LEROBOT_MODEL=lerobot/act_so101
EXPOSE 5070

# Run API server
CMD ["/opt/venv/bin/python", "/opt/lerobot/server.py"]