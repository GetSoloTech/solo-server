import requests
import json
import argparse

# Replace this URL with your exposed URL from the API builder.
# For example:
# SERVER_URL = 'https://8000-01hxj54gh5yry3bpaw5k8s5t5j.cloudspaces.litng.ai'
SERVER_URL = 'http://127.0.0.1:5070'

def main():
    parser = argparse.ArgumentParser(description="Send a query to the server.")
    parser.add_argument("--query", type=str, required=True, help="The query text to send to the server.")
        
    args = parser.parse_args()
        
    payload = {
        "query": args.query
    }
        
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes

        try:
            response_data = response.json()
        except json.decoder.JSONDecodeError:
            # If the response is not JSON formatted
            print(f"Non-JSON response received:\n{response.text}")
            return

        # Check if response_data is a dictionary
        if isinstance(response_data, dict):
            # Adjust according to the actual structure of your response
            result = response_data.get('response', response_data.get('output', response_data))
        else:
            # If it's not a dict, just use the response data directly
            result = response_data

        print(json.dumps(result, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")

if __name__ == "__main__":
    main()