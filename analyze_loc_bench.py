import re
from datasets import load_dataset
from collections import Counter


def analyze_loc_bench():
    print("🔍 Loading dataset...")
    dataset = load_dataset("czlll/Loc-Bench_V1", split="test")

    total_lines = 0
    repo_set = set()
    pr_set = set()
    file_set = set()

    for sample in dataset:
        total_lines += sample["patch"].count("\n") + sample["test_patch"].count("\n")

        # 提取仓库和 PR ID
        instance_id = sample["instance_id"]
        match = re.match(r"(.+)__(.+)-(\d+)", instance_id)
        if match:
            org, repo, pr = match.groups()
            repo_set.add(f"{org}/{repo}")
            pr_set.add(f"{org}/{repo}#{pr}")

        # 提取变动文件路径，存入去重集合
        for line in sample["patch"].splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                file_line = line.strip().replace("+++ b/", "").replace("--- a/", "")
                if file_line != "/dev/null":  # 排除文件新增/删除标记
                    file_set.add(file_line)

    # 💡 现在 file_set 是唯一变动文件集合，基于它做语言分类
    lang_counter = Counter()
    for file_path in file_set:
        if file_path.endswith(".py"):
            lang_counter["Python"] += 1
        elif file_path.endswith(".js"):
            lang_counter["JavaScript"] += 1
        elif file_path.endswith(".java"):
            lang_counter["Java"] += 1
        elif file_path.endswith(".cpp") or file_path.endswith(".cc"):
            lang_counter["C++"] += 1
        elif file_path.endswith(".go"):
            lang_counter["Go"] += 1
        elif file_path.endswith(".rs"):
            lang_counter["Rust"] += 1
        elif file_path.endswith(".ts"):
            lang_counter["TypeScript"] += 1
        elif file_path.endswith(".c"):
            lang_counter["C"] += 1
        else:
            lang_counter["Other"] += 1

    total_lang_files = sum(lang_counter.values())
    lang_distribution = {
        lang: {
            "count": count,
            "percentage": round(count / total_lang_files * 100, 2)
        }
        for lang, count in lang_counter.items()
    }

    # 输出结果
    print("\n📊 Analysis Results:")
    print(f"- 总样本数: {len(dataset)}")
    print(f"- 总变动行数: {total_lines}")
    print(f"- 涉及仓库数: {len(repo_set)}")
    print(f"- Pull Request 数量: {len(pr_set)}")
    print(f"- 变动文件总数: {len(file_set)}")

    print("\n🗂️ 涉及语言分布（按唯一文件统计）:")
    for lang, stats in sorted(lang_distribution.items(), key=lambda x: -x[1]["count"]):
        print(f"  {lang}: {stats['count']} files ({stats['percentage']}%)")


if __name__ == "__main__":
    analyze_loc_bench()
