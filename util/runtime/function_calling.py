"""This file contains the function calling implementation for different actions.
"""

import json
from litellm import (
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    ModelResponse,
)
from util.actions.action import (
    Action,
    FinishAction,
    # CmdRunAction,
    IPythonRunCellAction,
    MessageAction,
)
from .finish import FinishTool
from .structure_tools import ExploreTreeStructure, ExploreTreeStructure_simple
from .content_tools import SearchEntityTool, SearchRepoTool
import logging

logger = logging.getLogger()

ALL_FUNCTIONS = ['explore_tree_structure', 'search_code_snippets', 'get_entity_contents']

SYSTEM_PROMPT = """You are a helpful assistant that can interact with a computer to solve tasks.
<IMPORTANT>
* If user provides a path, you should NOT assume it's relative to the current working directory. Instead, you should explore the file system to find the file before working on it.
</IMPORTANT>
"""


def combine_thought(action: Action, thought: str) -> Action:
    if hasattr(action, 'raw_content') and thought:
        action.raw_content = thought
    if hasattr(action, 'thought') and thought:
        action.thought += '\n' + thought
    return action


def response_to_actions(response: ModelResponse) -> list[Action]:
    """
    将 LLM function calling 的响应（tool_calls）转换为结构化的 Action 实例列表，供 Agent 后续处理。

    Args:
        response: LLM 的原始响应。
    Returns:
        list[Action]: 包含 Action 实例的列表，Action有 MessageAction、FinishAction、IPythonRunCellAction 三种类型，
        其中IPythonRunCellAction代表要在 Python 环境中执行的动作。
    """
    actions: list[Action] = []
    assert len(response.choices) == 1, 'Only one choice is supported for now'
    assistant_msg = response.choices[0].message
    # tool_calls 是 OpenAI Function Calling 或其他兼容模型的标准字段，表示模型调用了函数。
    if assistant_msg.tool_calls:
        # Check if there's assistant_msg.content. If so, add it to the thought
        # 提取 Assistant 的“思路”（thought）
        thought = ''
        # Function Calling 返回值中除了 tool 调用，还可能包含一段文字说明（即“思路”）。
        if isinstance(assistant_msg.content, str):
            thought = assistant_msg.content
        elif isinstance(assistant_msg.content, list):
            for msg in assistant_msg.content:
                # OpenAI GPT-4-Turbo 返回的可能是富文本形式
                if msg['type'] == 'text':
                    thought += msg['text']

        # Process each tool call to OpenHands action
        for i, tool_call in enumerate(assistant_msg.tool_calls):
            action: Action
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.decoder.JSONDecodeError as e:
                raise RuntimeError(
                    f'Failed to parse tool call arguments: {tool_call.function.arguments}'
                ) from e
            if tool_call.function.name == 'finish':
                if list(arguments.values()):
                    action = FinishAction(thought=list(arguments.values())[0])
                else:
                    action = FinishAction()

            elif tool_call.function.name in ALL_FUNCTIONS:
                # We implement this in agent_skills, which can be used via Jupyter
                func_name = tool_call.function.name
                # 通过 print(...) 包裹函数调用，方便 stdout 获取
                code = f'print({func_name}(**{arguments}))'
                logger.debug(f'TOOL CALL: {func_name} with code: {code}')
                # 构造 IPythonRunCellAction，代表要在 Python 环境中执行的动作。
                action = IPythonRunCellAction(code=code,
                                              function_name=func_name,
                                              tool_call_id=tool_call.id)  # include_extra=False
            else:
                raise RuntimeError(f'Unknown tool call: {tool_call.function.name}')

            # We only add thought to the first action
            if i == 0:
                # 只将 assistant_msg.content 中的文字 thought 附加到第一个 Action，便于保留 LLM 的原始解释/思路。
                action = combine_thought(action, thought)

            actions.append(action)
    else:
        # 如果 tool_calls 不存在（即模型不支持或未启用 function calling），则简单封装为 MessageAction。
        # 这通常意味着：只是一段自然语言或说明性文本，不需要执行。
        actions.append(
            MessageAction(raw_content=assistant_msg.content, content=assistant_msg.content)
        )

    assert len(actions) >= 1
    return actions


def get_tools(
        codeact_enable_search_keyword: bool = False,
        codeact_enable_search_entity: bool = False,
        codeact_enable_tree_structure_traverser: bool = False,
        simple_desc: bool = False,

) -> list[ChatCompletionToolParam]:
    tools = [FinishTool]
    # if codeact_enable_cmd:
    #     tools.append(CmdRunTool)
    if codeact_enable_search_keyword:
        tools.append(SearchRepoTool)
    if codeact_enable_search_entity:
        tools.append(SearchEntityTool)
    if codeact_enable_tree_structure_traverser:
        if simple_desc:
            tools.append(ExploreTreeStructure_simple)
        else:
            tools.append(ExploreTreeStructure)
    return tools
