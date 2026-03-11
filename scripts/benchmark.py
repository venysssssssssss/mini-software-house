import ollama
import time
import json
import sys

MODELS = ["phi3.5:latest", "qwen2.5-coder:7b", "gemma2:2b"]
PROMPT = "Write a simple function to calculate the factorial of a number in Python."

def benchmark_model(model_name):
    print(f"--- Benchmarking {model_name} ---")
    try:
        # First call might trigger model load
        start_time = time.time()
        response = ollama.generate(model=model_name, prompt=PROMPT)
        end_time = time.time()

        eval_count = response.get('eval_count', 0)
        eval_duration = response.get('eval_duration', 0)
        load_duration = response.get('load_duration', 0)
        
        # Ollama duration is in nanoseconds
        eval_duration_sec = eval_duration / 1e9
        load_duration_sec = load_duration / 1e9
        total_duration_sec = end_time - start_time
        
        tps = eval_count / eval_duration_sec if eval_duration_sec > 0 else 0
        
        print(f"Tokens: {eval_count}")
        print(f"Eval Duration: {eval_duration_sec:.2f}s")
        print(f"Tokens/sec: {tps:.2f} t/s")
        print(f"Load Duration: {load_duration_sec:.2f}s")
        print(f"Total Time: {total_duration_sec:.2f}s")
        # print(f"Response: {response['response'][:50]}...")
        print("-" * 30)
        
        return {
            "model": model_name,
            "tokens": eval_count,
            "tps": tps,
            "load_duration": load_duration_sec,
            "total_time": total_duration_sec
        }
    except Exception as e:
        print(f"Error benchmarking {model_name}: {e}")
        return None

if __name__ == "__main__":
    results = []
    print(f"Starting benchmark for {len(MODELS)} models...")
    for model in MODELS:
        res = benchmark_model(model)
        if res:
            results.append(res)
    
    with open("scripts/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nBenchmark results saved to scripts/benchmark_results.json")
