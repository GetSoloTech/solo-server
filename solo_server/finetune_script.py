import json
from datasets import Dataset
from unsloth import FastLanguageModel, is_bfloat16_supported, standardize_sharegpt
from pathlib import Path
import typer
from peft import LoraConfig, TaskType
from trl import SFTTrainer
from transformers import TrainingArguments
import torch

def run_training(
    data_path: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
):
    """Run the finetuning process"""

    # Check GPU compatibility
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name()
        compute_capability = torch.cuda.get_device_capability()
        print(f"Found GPU: {gpu_name} with compute capability {compute_capability}")
        
        # Use 8-bit quantization for older GPUs
        use_4bit = compute_capability[0] >= 8  # Use 4-bit only for Ampere (8.0) and newer
    else:
        print("No GPU found, using CPU mode")
        use_4bit = False

    try:
        print("Initializing model and tokenizer...")
        # Initialize model with appropriate quantization
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name="unsloth/DeepSeek-R1-Distill-Qwen-1.5B",
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=use_4bit,  # Use 4-bit quantization only for compatible GPUs
            load_in_8bit=not use_4bit,  # Use 8-bit quantization for older GPUs
        )
        print("Model and tokenizer initialized successfully")

    except Exception as e:
        print(f"Error initializing model: {str(e)}")
        raise

    try:
        print("Applying PEFT configuration...")
        model = FastLanguageModel.get_peft_model(
            model, 
            r=lora_r,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            use_gradient_checkpointing="unsloth",
            use_rslora=False,
            random_state=3407,
        )
        print("PEFT configuration applied successfully")

    except Exception as e:
        print(f"Error applying PEFT configuration: {str(e)}")
        raise

    with open(data_path) as f:
        raw_data = json.load(f)

    dataset = prepare_dataset(raw_data, tokenizer)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        logging_steps=10,
        fp16=is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        warmup_ratio=0.03,
        weight_decay=0.01,
        optim="adamw_8bit",
        lr_scheduler_type="linear",
        seed=3407,
        report_to="none",
    )

    # Initialize SFT trainer with eval_dataset
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=2,
        args=training_args,
        packing=False,
    )

    # Train
    trainer.train()

    # Replace the saving code with this:
    print("Saving model...")
    try:
        merged_path = Path(output_dir) / "merged_model"
        print("Merging and saving full model...")
        model.save_pretrained_merged(
            merged_path,
            tokenizer,
            save_method="merged_16bit",  #
        )
        print(f"✓ Saved merged model to {merged_path}")
    except Exception as e:
        print(f"Warning: Could not save merged model: {e}")
        print("Continuing with GGUF conversion...")

    # Save GGUF version
    try:
        gguf_path = Path(output_dir) / "gguf"
        gguf_path.mkdir(exist_ok=True)
        print("Converting model to GGUF format...")
        
        # Use the adapter model for GGUF conversion
        model.save_pretrained_gguf(
            str(gguf_path / "model"),
            tokenizer,
            quantization_method="q4_k_m",
        )
    except Exception as e:
        print(f"Warning: Could not save GGUF model: {e}")

    print("Training and saving completed!")
    print(tokenizer._ollama_modelfile)
    print(tokenizer._ollama_modelfile.read())


def format_instruction(question: str, answer: str) -> str:
    """Format a single Q&A pair into instruction format"""
    return f"""You are a helpful assistant. Based on the following question, provide a relevant answer:

### Question:
{question}

### Response:
{answer}"""

def prepare_dataset(raw_data: dict, tokenizer):
    """Prepare dataset from raw data"""
    formatted_data = []
    
    for item in raw_data["data"]:
        data_dict = json.loads(item["data"])
        formatted_text = format_instruction(
            data_dict["question"],
            data_dict["answer"]
        )
        formatted_data.append({"text": formatted_text + tokenizer.eos_token})
    # Create dataset
    dataset = Dataset.from_list(formatted_data)

    return dataset

if __name__ == "__main__":
    app = typer.Typer()
    
    @app.command()
    def main(
        data_path: str = typer.Option(..., "--data-path", help="Path to the JSON data file"),
        output_dir: str = typer.Option(..., "--output-dir", help="Directory to save the model"),
        epochs: int = typer.Option(..., "--epochs", help="Number of training epochs"),
        batch_size: int = typer.Option(..., "--batch-size", help="Training batch size"),
        learning_rate: float = typer.Option(..., "--learning-rate", help="Learning rate"),
        lora_r: int = typer.Option(..., "--lora-r", help="LoRA attention dimension"),
        lora_alpha: int = typer.Option(..., "--lora-alpha", help="LoRA alpha parameter"),
        lora_dropout: float = typer.Option(..., "--lora-dropout", help="LoRA dropout value"),
    ):
        run_training(
            data_path=data_path,
            output_dir=output_dir,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
        )
    
    app() 