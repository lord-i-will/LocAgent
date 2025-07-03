ISSUE_DETECT_TASK_INSTRUCTION = """
# 任务:
你将收到一个功能特性的描述。你的任务是根据功能特性描述、入口函数等信息，在代码中定位分析可能存在的问题，比如功能实现错误、功能实现遗漏等。

1. 分析用户要实现的功能特性，提取关键信息。
2. 提取入口函数作为关键词，调用相关函数(比如 get_entity_contents)获取代码内容，分析代码主流程，并按需查看上下游依赖函数，逐步深入分析。
3. 定位问题代码：根据功能特性描述，在代码中定位可能存在问题的代码位置。
"""

OUTPUT_FORMAT_LOC = """
# 缺陷检测结果输出样式:
你的最终输出应列出 bug 发生的位置，并用三个反引号 ``` 包裹输出内容。
每个输出位置应包含文件路径、函数名或行号，如果问题 bug 发生的位置有多个，请按重要性排序，由高到低输出。

## 样例:
```
service/product_service.go
method: ProductService.CheckStock
line: 10

repository/payment_repo.go
line: 156
line: 24
function: generatePaymentID
```

只返回相关位置信息。
"""

FAKE_USER_MSG_FOR_ISSUE_DETECT = (
    '若确认任务已完成，请将最终答案发送给用户，同时请务必调用 `finish` 工具结束整个流程。\n'
    '重要：禁止寻求人工帮助，禁止回复空的内容。\n'
)
