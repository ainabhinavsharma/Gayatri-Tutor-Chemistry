import time
import json
from core.providers.local import LocalProvider

def main():
    print("Starting Gayatri AI Performance Benchmark...\n")
    
    # 1. Loading the model
    print("1. Loading Local Model...")
    t0 = time.time()
    LocalProvider.health()
    LocalProvider._load_model()
    t1 = time.time()
    print(f"Model loaded in {t1 - t0:.2f} seconds.\n")

    # 2. Testing prompt tokenization (KV cache warmup)
    print("2. Warm TTFT Benchmark (Short Prompt)...")
    prompt = "Explain recursion in simple terms."
    stream = LocalProvider.stream(prompt, max_tokens=50)
    
    t_start = time.time()
    first_token_time = None
    tokens = 0
    
    for _ in stream:
        if first_token_time is None:
            first_token_time = time.time()
        tokens += 1
        
    t_end = time.time()
    
    ttft_ms = (first_token_time - t_start) * 1000 if first_token_time else 0
    gen_time = t_end - (first_token_time or t_start)
    tps = tokens / gen_time if gen_time > 0 else 0
    
    print(f"TTFT: {ttft_ms:.1f} ms")
    print(f"Tokens/sec: {tps:.1f}")
    print(f"Total time: {t_end - t_start:.2f} s\n")
    
    print("Benchmark complete.")

if __name__ == "__main__":
    main()

