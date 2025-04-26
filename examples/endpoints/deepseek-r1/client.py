import argparse
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:5070/v1",
    api_key="lit",
)


def send_prompt_to_api(prompt: str) -> None:
    SYSTEM_PROMPT = "You are a helpful assistant. \n"
    stream = client.chat.completions.create(
        model="deepseek-r1",
        messages=[
            {"role": "user", "content": SYSTEM_PROMPT + prompt},
        ],
        max_completion_tokens=512,
        temperature=0.6,  # Usage: https://github.com/deepseek-ai/DeepSeek-R1?tab=readme-ov-file#usage-recommendations
        stream=True,
    )
    for chunk in stream:
        print(
            f"\033[92m{chunk.choices[0].delta.content or ''}\033[0m", end="", flush=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a prompt to the Deepseek R1 API server and receive a response."
    )
    parser.add_argument(
        "-p", "--prompt", required=True, help="The prompt to send to the API."
    )
    args = parser.parse_args()

    send_prompt_to_api(args.prompt)