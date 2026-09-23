"""Gayatri Chemistry Tutor — Google Colab 3B Model Training Script.

Fine-tunes Qwen2.5-3B-Instruct on the Gayatri Chemistry curriculum dataset.
Includes automatic Google Drive backup, GGUF Q4_K_M conversion, and download.
"""
import os
import sys
import shutil
from pathlib import Path

# ── 1. Configuration ────────────────────────────────────────────────────────
BASE_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "./gayatri_3b_checkpoints"
GGUF_NAME = "Gayatri-Tutor-v3-Q4_K_M.gguf"
DRIVE_BACKUP_DIR = "/content/drive/MyDrive/GayatriAI/models/gayatri/"

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
MAX_SEQ_LENGTH = 2048
LEARNING_RATE = 2e-4
NUM_TRAIN_EPOCHS = 3
PER_DEVICE_BATCH_SIZE = 2
GRADIENT_ACCUMULATION_STEPS = 4


def check_gpu():
    """Verify CUDA GPU is active."""
    import torch
    if not torch.cuda.is_available():
        print("[WARN] CUDA GPU not detected! Training will be slow. Enable T4 GPU in Colab Runtime.")
    else:
        print(f"[OK] Detected GPU: {torch.cuda.get_device_name(0)} with {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB VRAM")


def mount_google_drive():
    """Mount Google Drive if running inside Google Colab."""
    try:
        from google.colab import drive
        print("[*] Mounting Google Drive for automatic model backup...")
        drive.mount('/content/drive')
        os.makedirs(DRIVE_BACKUP_DIR, exist_ok=True)
        print(f"[OK] Google Drive ready at: {DRIVE_BACKUP_DIR}")
        return True
    except Exception as exc:
        print(f"[INFO] Running in local environment or Drive mount skipped: {exc}")
        return False


def load_dataset_splits():
    """Load train and validation jsonl datasets."""
    from datasets import load_dataset
    
    train_file = "train.jsonl" if os.path.exists("train.jsonl") else "PRIVATE_WORK/training/exported/train.jsonl"
    val_file = "validation.jsonl" if os.path.exists("validation.jsonl") else "PRIVATE_WORK/training/exported/validation.jsonl"
    
    if not os.path.exists(train_file):
        raise FileNotFoundError(f"Training dataset not found at {train_file}. Please upload train.jsonl.")
        
    print(f"[*] Loading training data from: {train_file}")
    dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})
    print(f"[OK] Loaded {len(dataset['train'])} train examples, {len(dataset['validation'])} validation examples.")
    return dataset


def train_slm():
    """Fine-tune Qwen2.5-0.5B-Instruct with LoRA adapters."""
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model
    from trl import SFTTrainer

    check_gpu()
    has_drive = mount_google_drive()
    dataset = load_dataset_splits()

    # Ensure incompatible Colab pre-installed torchao doesn't break PEFT
    try:
        import torchao
        if getattr(torchao, "__version__", "0") < "0.16.0":
            os.system("pip uninstall -y torchao")
    except Exception:
        pass

    print(f"[*] Loading base model: {BASE_MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype_arg = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    try:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            dtype=dtype_arg,
            device_map="auto",
            trust_remote_code=True,
        )
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            torch_dtype=dtype_arg,
            device_map="auto",
            trust_remote_code=True,
        )

    # Configure PEFT LoRA
    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    def format_chatml(example):
        messages = example["messages"]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    formatted_dataset = dataset.map(format_chatml)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_TRAIN_EPOCHS,
        per_device_train_batch_size=PER_DEVICE_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=formatted_dataset["train"],
        eval_dataset=formatted_dataset["validation"],
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("\n[STEP] Starting LoRA fine-tuning...")
    trainer.train()
    print("[OK] Fine-tuning complete!")

    # Merge LoRA weights into base model
    print("[*] Merging LoRA weights for GGUF quantization...")
    merged_model = model.merge_and_unload()
    merged_output_dir = "./gayatri_slm_merged"
    merged_model.save_pretrained(merged_output_dir)
    tokenizer.save_pretrained(merged_output_dir)
    print(f"[OK] Merged model saved to: {merged_output_dir}")

    # Convert to GGUF using llama.cpp
    print("\n[STEP] Converting to GGUF Q4_K_M...")
    if not os.path.exists("llama.cpp"):
        os.system("git clone --depth 1 https://github.com/ggerganov/llama.cpp.git")
        os.system("pip install --quiet gguf")
        os.system("pip install -r llama.cpp/requirements.txt")
        os.system("cd llama.cpp && cmake -B build && cmake --build build --config Release -j --target llama-quantize")

    # 1. Convert to f16 GGUF
    f16_gguf = "./gayatri_slm_f16.gguf"
    os.system(f"python llama.cpp/convert_hf_to_gguf.py {merged_output_dir} --outfile {f16_gguf} --outtype f16")

    # 2. Quantize to Q4_K_M
    quant_binary = "./llama.cpp/build/bin/llama-quantize" if os.path.exists("./llama.cpp/build/bin/llama-quantize") else "./llama.cpp/llama-quantize"
    os.system(f"{quant_binary} {f16_gguf} {GGUF_NAME} Q4_K_M")

    if os.path.exists(GGUF_NAME):
        file_size_mb = os.path.getsize(GGUF_NAME) / (1024 * 1024)
        print(f"\n==================================================================")
        print(f"  GGUF MODEL READY: {GGUF_NAME} ({file_size_mb:.1f} MB)")
        print(f"==================================================================")

        # Save to Google Drive if mounted
        if has_drive and os.path.exists("/content/drive/MyDrive"):
            drive_dest = os.path.join(DRIVE_BACKUP_DIR, GGUF_NAME)
            shutil.copy(GGUF_NAME, drive_dest)
            print(f"[+] Successfully backed up model to Google Drive: {drive_dest}")

        # Trigger direct browser download in Colab
        try:
            from google.colab import files
            print("[*] Triggering direct browser download...")
            files.download(GGUF_NAME)
        except Exception:
            pass


if __name__ == "__main__":
    train_slm()
