import json
from datasets import Dataset
from unsloth import FastLanguageModel
from pathlib import Path
import typer
from peft import LoraConfig, TaskType
from unsloth import is_bfloat16_supported
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

    EOS_TOKEN = tokenizer.eos_token
    # Define prompt template
    qa_prompt = """Based on the following question, provide a relevant answer:

### Question:
{question}

### Response:
{answer}"""

    # Format data using prompt template
    def formatting_func(examples):
        questions = []
        answers = []
        for item in examples["data"]:
            data_dict = json.loads(item["data"])
            questions.append(data_dict["question"])
            answers.append(data_dict["answer"])
        
        texts = []
        for question, answer in zip(questions, answers):
            text = qa_prompt.format(question=question, answer=answer) + EOS_TOKEN
            texts.append(text)
        return {"text": texts}

    # Create initial dataset from raw data
    initial_dataset = Dataset.from_dict({"data": raw_data["data"]})
    
    # Apply formatting
    dataset = initial_dataset.map(formatting_func, batched=True, remove_columns=initial_dataset.column_names)

    # Split dataset into train and eval
    dataset_split = dataset.train_test_split(test_size=0.1, shuffle=True, seed=3407)
    train_dataset = dataset_split['train']
    eval_dataset = dataset_split['test']

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        fp16=is_bfloat16_supported(),
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
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=2,
        args=training_args,
        packing=False,
    )

    # Train
    trainer.train()

    # Save model and adapter
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    model.save_pretrained(Path(output_dir) / "adapter_model")
    
    # Save in GGUF format
    gguf_path = Path(output_dir) / "gguf"
    gguf_path.mkdir(exist_ok=True)
    
    print("Converting model to GGUF format...")
    model.save_pretrained_gguf(
        str(gguf_path / "model"), 
        tokenizer,
        quantization_method="q4_0",
    )

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