import requests

url = "http://localhost:5070/v1/chat/completions"
headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}
data = {
    "messages": [
        {
            "role": "user",
            "content": "how is the weather in London?",
        }
    ],
    "temperature": 0.7,
    "stream": False,
}

response = requests.post(url, headers=headers, json=data)

print(response.json())