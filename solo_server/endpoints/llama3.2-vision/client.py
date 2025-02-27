import base64
import requests
from rich import print


# encode an image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


base64_image = encode_image("image.jpg")
payload = {
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"What is this image?"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    ],
    "max_tokens": 50,
    "temperature": 0.2,
}

response = requests.post("http://localhost:5070/v1/chat/completions", json=payload)
print(response.json()["choices"][0])