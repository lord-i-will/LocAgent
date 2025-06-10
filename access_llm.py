import litellm


def access_model(model_name: str):
    try:
        litellm.set_verbose = True
        # litellm._turn_on_debug()
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": "Hi, can you reply with just 'OK'?"}],
        )
        print(f"✅ Success: Model '{model_name}' responded with:\n{response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Failed: Model '{model_name}' raised an error:\n{e}")


if __name__ == "__main__":
    try:
        access_model('huggingface/together/deepseek-ai/DeepSeek-R1')
    except Exception as e:
        print(f"出错了：{e}")
