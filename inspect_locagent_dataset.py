from datasets import load_dataset, Split, Dataset


def print_sample_structure(sample, index):
    print(f"=== Sample {index} ===")
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


def print_sample(ds):
    for i, sample in enumerate(ds):
        if i >= 3:
            break
        print_sample_structure(sample, i)


if __name__ == "__main__":
    print("📦 Loading dataset 'czlll/Loc-Bench_V1' (test split)...")
    dataset = load_dataset("czlll/Loc-Bench_V1", split="test[:1]")
    print(f"✅ Loaded {len(dataset)} samples.")
    print_sample(dataset)

    print("\nLoading dataset from list....")
    data = [{
        "repo": "product_tree_data_cleaning",
        "instance_id": "product_tree_data_cleaning-1",
        "base_commit": "60d74556dae217be2dedaf25747dd57d0fdfb0e8",
        "patch": "",
        "problem_statement": "支付最大金额不应该超过9000",
        "edit_functions": ["bug_gen.py:pay"],
        "edit_functions_length": 1,
    }]
    dataset = Dataset.from_list(mapping=data, split=Split.TEST)
    print(f"✅ Loaded {len(dataset)} samples.")
    print_sample(dataset)

    print("\nLoading dataset from json....")
    dataset = Dataset.from_json(path_or_paths='./dataset/product_tree_data_cleaning.json', split=Split.TEST)
    print(f"✅ Loaded {len(dataset)} samples.")
    print_sample(dataset)
