import os
import openai
from typing import List, Dict, Optional


class LLMClient:
    """
    一个封装好的 LLM 交互类，支持多模型调用（OpenAI/Anthropic/Ollama等）。

    初始化参数:
        model (str): 模型名称（如 "gpt-3.5-turbo", "claude-2"）
        api_key (str, optional): 各平台的API Key，默认从环境变量读取
        api_base (str, optional): 自定义API端点（如本地Ollama）
        timeout (int, optional): 请求超时时间（秒）
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            api_base: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("BD_GPT_AK")  # 默认从环境变量读取
        self.api_base = api_base or os.getenv("BD_GPT_BASE_URL")
        self.client = openai.AzureOpenAI(
            azure_endpoint=self.api_base,
            api_version="2024-03-01-preview",
            api_key=self.api_key,
        )

    def get_llm_client(self):
        return self.client

    def chat_for_test(
            self,
            model: str,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            repetition_penalty: Optional[float] = None,
            **kwargs
    ) -> str:
        """
        与大模型对话

        Args:
            model: 模型名称
            messages: 对话消息列表，格式如 [{"role": "user", "content": "你好"}]
            temperature: 生成多样性（0-1，越高越随机）
            top_p: 核采样阈值（0-1，与temperature二选一）
            repetition_penalty: 重复惩罚（>1时降低重复内容）
            **kwargs: 其他litellm支持的参数（如max_tokens）

        Returns:
            str: 模型生成的回复内容
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=temperature,
                top_p=top_p,
                presence_penalty=repetition_penalty,
                timeout=kwargs.get("timeout", 30),
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM调用失败: {str(e)}") from e


if __name__ == "__main__":
    # 初始化客户端
    openai_client = LLMClient()

    # 发起对话
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手"},
        {"role": "user", "content": "请用中文自我介绍"}
    ]
    reply = openai_client.chat_for_test(
        model="gpt-4o-2024-05-13",
        messages=messages,
        temperature=0.8
    )
    print("模型回复:", reply)
