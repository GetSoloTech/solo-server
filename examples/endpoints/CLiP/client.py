import requests
from PIL import Image
import json
from io import BytesIO

def send_image_to_server(image_path, server_url):
    """
    Sends an image to the server and prints the server's response.

    Args:
    image_path (str): The file path of the image to send.
    server_url (str): The URL of the server that will process the image.
    """
    # Open the image, convert it to RGB (in case it's not in that mode)
    image = Image.open(image_path).convert("RGB")

    # Convert the image to bytes
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    image_bytes = buffered.getvalue()

    # Send a POST request to the server with the image
    response = requests.post(
        server_url,
        json={"image_bytes": image_bytes.hex()}  # Convert bytes to hex string for JSON serialization
    )

    # Print the response from the server
    if response.status_code == 200:
        print("Server response:", response.json())
    else:
        print("Failed to get response from the server, status code:", response.status_code)

if __name__ == "__main__":
    # Specify the path to your image and the URL of the server
    import os
    cwd = os.getcwd()
    image_path = f"{cwd}/ny_example_image.jpeg"
    server_url = "http://127.0.0.1:5070/predict"

    # Send the image to the server
    send_image_to_server(image_path, server_url)