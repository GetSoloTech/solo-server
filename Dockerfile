# Use an official slim Python image as the base.
FROM python:3.10-slim

# Install any system dependencies needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install required Python packages.
RUN pip install --no-cache-dir \
    litserve \
    torch \
    transformers

# Set the working directory.
WORKDIR /app

# Copy the server code into the container.
COPY server.py /app/

# Expose the port that the server will listen on.
EXPOSE 8000

# Command to run the Solo Server.
CMD ["python", "server.py"]
