import time
from typing import List, Tuple
from datetime import datetime
from llama_cpp import Llama
from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
import typer
import requests
import json

console = Console()

class Message(BaseModel):
    role: str
    content: str

class LlamaResponse(BaseModel):
    model: str
    created_at: datetime
    message: Message
    done: bool
    total_duration: float
    load_duration: float = 0.0
    eval_count: int
    eval_duration: float

def load_model(model_path: str) -> Tuple[Llama, float]:
    console.print(Panel.fit(f"[cyan]Loading model: {model_path}[/]", title="[bold magenta]Solo Server[/]"))
    start_time = time.time()
    model = Llama(model_path=model_path)
    load_duration = time.time() - start_time
    return model, load_duration

def api_response(model: str, prompt: str, url: str, server_type:str = None) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
    }

    if server_type == "ollama":
        payload["model"] = model.lower()
        payload["stream"] = False
    
    if server_type == "vllm":
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
    headers = {"Content-Type": "application/json"}
    start_time = time.time()
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        data = response.json()
        # Add eval_duration if not present
        if "eval_duration" not in data:
            data["eval_duration"] = time.time() - start_time
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def run_benchmark(server_type: str, model: object, model_name: str, prompt: str, load_duration: float) -> LlamaResponse:
    content = ""
    if server_type == "llama.cpp":
        start_time = time.time()
        response = model(prompt, stop=["\n"], echo=False)
        eval_duration = time.time() - start_time
        content = response["choices"][0]["text"]
        print(content)
    else:
        url = "http://localhost:11434/api/generate" if server_type == "ollama" else "http://localhost:8000/v1/chat/completions"
        response = api_response(model_name, prompt, url, server_type)

        if server_type == "vllm":
            if "choices" in response and "message" in response["choices"][0]:
                content = response["choices"][0]["message"]["content"]
            else:
                content = response["choices"][0]["text"]
            print(content)
            eval_duration = response.get("eval_duration", 0.0) 
        else:
            content = response.get("response", "")
            load_duration = response.get("load_duration", 0.0) * 1e-9  # Convert nanoseconds to seconds
            eval_duration = response.get("eval_duration", 0.0) * 1e-9  # Convert nanoseconds to seconds
            
    message = Message(role="assistant", content=content)

    return LlamaResponse(
        model=model_name,
        created_at=datetime.now(),
        message=message,
        done=True,
        load_duration=load_duration,
        total_duration=load_duration + eval_duration,
        eval_count=len(content.split()),
        eval_duration=eval_duration,
    )

def inference_stats(model_response: LlamaResponse):
    # Add checks for zero duration
    response_ts = 0.0 if model_response.eval_duration == 0 else model_response.eval_count / model_response.eval_duration
    total_ts = 0.0 if model_response.total_duration == 0 else model_response.eval_count / model_response.total_duration

    console.print(
        Panel.fit(
            f"[bold magenta]{model_response.model}[/]\n"
            f"[green]Response:[/] {response_ts:.2f} tokens/s\n"
            f"[blue]Total:[/] {total_ts:.2f} tokens/s\n\n"
            f"[yellow]Stats:[/]\n"
            f" - Response tokens: {model_response.eval_count}\n"
            f" - Model load time: {model_response.load_duration:.2f}s\n"
            f" - Response time: {model_response.eval_duration:.2f}s\n"
            f" - Total time: {model_response.total_duration:.2f}s",
            title="[bold cyan]Benchmark Results[/]",
        )
    )

def average_stats(responses: List[LlamaResponse]):
    if not responses:
        console.print("[red]No stats to average.[/]")
        return

    avg_response = LlamaResponse(
        model=responses[0].model,
        created_at=datetime.now(),
        message=Message(role="system", content=f"Average stats across {len(responses)} runs"),
        done=True,
        total_duration=sum(r.total_duration for r in responses) / len(responses),
        load_duration=sum(r.load_duration for r in responses) / len(responses),
        eval_count=sum(r.eval_count for r in responses) // len(responses),
        eval_duration=sum(r.eval_duration for r in responses) / len(responses),
    )
    inference_stats(avg_response)

def benchmark(
    server_type: str = typer.Option(None, "-s", help="Type of server (e.g., ollama, vllm, llama.cpp)."),
    model_name: str = typer.Option(None, "-m", help="Name of the model."),
    prompts: List[str] = typer.Option(["Why is the sky blue?", "Write a report on the financials of Apple Inc.", 
                                       "Tell me about San Francisco"], "-p", help="List of prompts to use for benchmarking."),
):
    if not server_type:
        server_type = typer.prompt("Enter server type (ollama, vllm, llama.cpp)")
    if not model_name:
        model_name = typer.prompt("Enter model name")

    console.print(f"\n[bold cyan]Starting Solo Server Benchmark for {server_type} with model {model_name}...[/]")

    model = None
    load_duration = 0.0
    if server_type == "llama.cpp":
        model, load_duration = load_model(model_name)
    responses: List[LlamaResponse] = []
    for prompt in track(prompts, description="[cyan]Running benchmarks..."):
        response = run_benchmark(server_type, model, model_name, prompt, load_duration)
        responses.append(response)
        inference_stats(response)
    
    average_stats(responses)
