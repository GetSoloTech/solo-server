import typer
import subprocess

import requests
import json

def generate(prompt: str):
    """
    Serves a model using Ollama and enables interactive chat.
    """

    # prompt = "facts about Gilroy"
    # num_of_records = 10

    data = {
        "prompt": prompt,
        "numOfRecords": 100,
        "model": "gpt-4o-mini-2024-07-18"
    }

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    response = requests.post(
        'https://api.starfishdata.ai/v1/generateData',
        headers=headers,
        data=json.dumps(data)
    )

    if response.status_code == 200:
        typer.echo(f"✅ Successfully generated data for prompt: {prompt}")
        typer.echo(json.dumps(response.json(), indent=2))
    else:
        typer.echo(f"❌ An error occurred: {response.text}", err=True)


def gstatus(job_id: str):
    """
    Get the status of a job.
    """
    # job_id = "67386772-3342-4e51-bf08-5131961afc15"

    data = {
        "jobId": job_id
    }

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    response = requests.post(
        'https://api.starfishdata.ai/v1/jobStatus',
        headers=headers,
        data=json.dumps(data)
    )

    if response.status_code == 200:
        typer.echo(f"✅ Successfully retrieved job status for job: {job_id}")
        typer.echo(json.dumps(response.json(), indent=2))
    else:
        typer.echo(f"❌ An error occurred: {response.text}", err=True)



def gdownload(project_id: str):
    """
    Get the status of a job.
    """
    # job_id = "67386772-3342-4e51-bf08-5131961afc15"

    data = {
        "projectId": project_id
    }

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    response = requests.post(
        'https://api.starfishdata.ai/v1/data',
        headers=headers,
        data=json.dumps(data)
    )

    # convert to unsloth format and save to file
    if response.status_code == 200:
        typer.echo(f"✅ Successfully retrieved job status for job: {project_id}")
        typer.echo(json.dumps(response.json(), indent=2))
    else:
        typer.echo(f"❌ An error occurred: {response.text}", err=True)


EOS_TOKEN = tokenizer.eos_token  # Must add EOS_TOKEN
train_prompt_style = '{"prompt": "{0}", "completion": "{1}"}'

def formatting_prompts_func(examples):
    inputs = examples["Question"]
    outputs = examples["Response"]
    texts = []
    for input, output in zip(inputs, outputs):
        text = train_prompt_style.format(input, output) + EOS_TOKEN
        texts.append(text)
    return {
        "text": texts,
    }

def format_data(path):
    with open(path, 'r') as f:
        data = json.load(f)
    new_data = []
    for item in data:
        item['prompt'] = item['prompt'].replace('{{', '{').replace('}}', '}')
        new_data.append(item)
    with open(path, 'w') as f:
        json.dump(new_data, f)