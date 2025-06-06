from datasets import load_dataset


def print_sample_structure(sample, index):
    print(f"\n=== Sample {index} ===")
    for key, value in sample.items():
        print(f"{key}: {type(value).__name__}")
        if isinstance(value, list):
            preview = value[0] if value else "[]"
            print(f"  - First item: {preview}")
        elif isinstance(value, str):
            preview = value.strip().replace("\n", " ")
            if len(preview) > 100:
                preview = preview[:100] + "..."
            print(f"  - Preview: {preview}")
        else:
            print(f"  - Value: {value}")


if __name__ == "__main__":
    print("📦 Loading dataset 'czlll/Loc-Bench_V1' (test split)...")
    dataset = load_dataset("czlll/Loc-Bench_V1", split="test")

    print(f"✅ Loaded {len(dataset)} samples.")
    for i, sample in enumerate(dataset):
        if i >= 3:
            break
        print_sample_structure(sample, i)
