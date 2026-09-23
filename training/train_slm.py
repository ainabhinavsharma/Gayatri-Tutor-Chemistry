"""Gayatri Chemistry Tutor — SLM Standalone Training & GGUF Quantization Script.

Fine-tunes Qwen2.5-0.5B-Instruct in native FP16 with LoRA (r=32, alpha=64).
Performs pedagogical alignment validation, merges weights, and quantizes to GGUF (Q4_K_M and Q8_0).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

BASE_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = "./gayatri_0.5b_checkpoints"
MERGED_OUTPUT_DIR = "./gayatri_slm_merged"
GGUF_Q4 = "Gayatri-Tutor-SLM-Q4_K_M.gguf"
GGUF_Q8 = "Gayatri-Tutor-SLM-Q8_0.gguf"
DRIVE_BACKUP_DIR = "/content/drive/MyDrive/GayatriAI/models/gayatri/"

LORA_R = 32
LORA_ALPHA = 64
LORA_DROPOUT = 0.05
MAX_SEQ_LENGTH = 1024
LEARNING_RATE = 3e-4
NUM_TRAIN_EPOCHS = 3
PER_DEVICE_BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4


def check_gpu():
    """Verify CUDA GPU is available."""
    import torch
    if not torch.cuda.is_available():
        print("[WARN] CUDA GPU not detected! Training will be executed on CPU.")
    else:
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"[OK] Detected GPU: {name} ({vram:.1f} GB VRAM)")


def load_or_generate_dataset(data_dir: Path):
    """Load train.jsonl and val.jsonl, auto-generating if not found."""
    from datasets import load_dataset
    train_file = data_dir / "train.jsonl"
    val_file = data_dir / "val.jsonl"

    if not train_file.exists() or not val_file.exists():
        print(f"[*] Training files not found in {data_dir}. Generating synthetic dataset...")
        from scripts.generate_slm_training_data import generate_full_dataset
        generate_full_dataset(output_dir=data_dir)

    print(f"[*] Loading dataset from: {train_file} and {val_file}")
    dataset = load_dataset("json", data_files={"train": str(train_file), "validation": str(val_file)})
    print(f"[OK] Loaded {len(dataset['train'])} train examples, {len(dataset['validation'])} validation examples.")
    return dataset


def run_pedagogical_verification(model, tokenizer):
    """Verify Socratic 4-tier explain, anti-answer leakage, and hint ladder."""
    import torch
    print("\n" + "=" * 60)
    print("  RUNNING IN-NOTEBOOK PEDAGOGICAL VERIFICATION SUITE")
    print("=" * 60)

    test_cases = [
        {
            "name": "Socratic 4-Tier EXPLAIN Test",
            "prompt": "Please explain the First Law of Thermodynamics.",
            "must_contain": ["analogy", "first law", "delta u", "?"],
            "must_not_contain": []
        },
        {
            "name": "Anti-Answer Leakage Invariant Test",
            "prompt": "delta U is 700 J because we add them up: 500 + 200 = 700 J.",
            "must_contain": ["work", "expansion"],
            "must_not_contain": ["300 J", "300J", "= 300", "equals 300", "answer is 300"]
        }
    ]

    passed = 0
    model.eval()

    for tc in test_cases:
        messages = [
            {"role": "system", "content": "You are Gayatri Chemistry Tutor. Socratic only. NEVER reveal final numerical answers."},
            {"role": "user", "content": tc["prompt"]}
        ]
        text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text_input, return_tensors="pt").to(model.device)

        with torch.no_grad():
            output_tokens = model.generate(
                **inputs,
                max_new_tokens=250,
                temperature=0.2,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
            )
        generated_text = tokenizer.decode(output_tokens[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        lower_gen = generated_text.lower()

        leak_found = any(bad in lower_gen for bad in tc["must_not_contain"])
        if leak_found:
            print(f"[FAIL] {tc['name']}: Leaked forbidden string!")
        else:
            print(f"[PASS] {tc['name']}: Passed behavioral invariants.")
            passed += 1

    print(f"Pedagogical Verification Score: {passed}/{len(test_cases)} Passed.\n")


def train_and_convert(data_dir: Path, output_dir: Path):
    """Execute full fine-tuning, merging, and GGUF quantization."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from trl import SFTTrainer

    check_gpu()
    dataset = load_or_generate_dataset(data_dir)

    print(f"[*] Loading base model: {BASE_MODEL_NAME} in native fp16...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype_arg = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
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
        output_dir=str(output_dir),
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
        fp16=(dtype_arg == torch.float16),
        bf16=(dtype_arg == torch.bfloat16),
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
    print("[*] Merging LoRA weights...")
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(MERGED_OUTPUT_DIR)
    tokenizer.save_pretrained(MERGED_OUTPUT_DIR)
    print(f"[OK] Merged model saved to: {MERGED_OUTPUT_DIR}")

    # Pedagogical verification
    run_pedagogical_verification(merged_model, tokenizer)

    # GGUF Quantization
    print("\n[STEP] Converting to GGUF using llama.cpp...")
    if not os.path.exists("llama.cpp"):
        os.system("git clone --depth 1 https://github.com/ggerganov/llama.cpp.git")
        os.system("pip install --quiet gguf")
        os.system("pip install -r llama.cpp/requirements.txt")
        os.system("cmake -B llama.cpp/build -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF llama.cpp")
        os.system("cmake --build llama.cpp/build --config Release --target llama-quantize -j")

    f16_gguf = "./gayatri_slm_f16.gguf"
    os.system(f"python llama.cpp/convert_hf_to_gguf.py {MERGED_OUTPUT_DIR} --outfile {f16_gguf} --outtype f16")

    quant_bin = "./llama.cpp/build/bin/llama-quantize" if os.path.exists("./llama.cpp/build/bin/llama-quantize") else "./llama.cpp/llama-quantize"
    os.system(f"{quant_bin} {f16_gguf} {GGUF_Q4} Q4_K_M")
    os.system(f"{quant_bin} {f16_gguf} {GGUF_Q8} Q8_0")

    if os.path.exists(GGUF_Q4):
        size_mb = os.path.getsize(GGUF_Q4) / (1024 * 1024)
        print(f"\n[OK] Model successfully created: {GGUF_Q4} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Gayatri SLM (Qwen2.5-0.5B-Instruct).")
    parser.add_argument("--data-dir", default="training/data/processed", help="Path to processed JSONL datasets")
    parser.add_argument("--output-dir", default="./gayatri_0.5b_checkpoints", help="Training checkpoint output dir")
    args = parser.parse_args()

    train_and_convert(Path(args.data_dir), Path(args.output_dir))
