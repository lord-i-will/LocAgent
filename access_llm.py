import os
from openai import OpenAI


def call_openrouter_qwen():
    # ✅ 设置 OpenRouter API 基础信息
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    # ✅ 检查环境变量是否存在
    if not client.api_key:
        raise ValueError("请先设置 OPENROUTER_API_KEY 环境变量")

    # models = client.models.list()
    # print("✅ 当前 OpenRouter 可用模型列表：\n")
    # for m in models.data:
    #     if m.id.endswith(":free"):
    #         print(m.id.removesuffix(":free"))

    # ✅ 发起请求
    response = client.chat.completions.create(
        model="qwen/qwen3-14b",
        messages=[
            {"role": "user", "content": "你好，请介绍一下你是谁？"}
        ]
    )

    # ✅ 打印回复内容
    print("🤖 Qwen 回复：")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    try:
        call_openrouter_qwen()
    except Exception as e:
        print(f"出错了：{e}")
