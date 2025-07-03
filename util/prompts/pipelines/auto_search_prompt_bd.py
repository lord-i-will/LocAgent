TASK_INSTRUCTION="""
根据以下用户需求的描述，你的任务是定位需要修改的特定文件、函数或代码行，并检查当前代码逻辑是否存在bug，比如功能实现错误、功能实现遗漏等。

定位步骤：

## 第一步：分类并提取关键需求信息
- 识别当前需求是做什么的：bug修复、能力扩展等
- 入口函数是什么

## 第二步：熟悉代码结构
- 使用提取的入口函数进行代码库搜索
  - 使用提供的工具（get_entity_contents/explore_tree_structure等），浏览代码库以熟悉其结构
  - 一定要跟踪函数调用逐级深入查看，直到找到“可以解决用户需求”的函数/方法
  - 整个搜索过程是熟悉上下文的过程，要不断总结、思考，整个过程要聚焦“哪个地方可以满足用户需求”
- 代码实体使用说明：包括file、function、method、struct等
  - 格式：'文件路径:限定名称'
  - 例如：
    - 对于位于`service/product_service.go`中`ProductService`类的`CheckStock`方法，表示为：'service/product_service.go:ProductService.CheckStock'
    - 对于位于`service/product_service.go`中的`toString`函数，表示为：'service/product_service.go:toString'

## 第三步：分析并重现问题
- 澄清需求的目的
  - 如果是扩展功能：确定在何处以及如何合并新行为、修改字段等来满足功能描述
  - 如果是bug修复：重点定位包含潜在错误的地方
- 重建执行流程
  - 识别触发问题的主要入口点
  - 跟踪函数调用、类交互和事件序列
  - 识别可能导致问题的断点
  *重要提示：保持重建的流程专注于问题本身（即如果修改这个地方那么功能将会得到满足、bug会得到解决），避免无关细节*

## 第四步：定位需要修改的区域
- 定位需要更改或包含解决关键信息的特定文件、函数或代码行
- 考虑可能影响或受问题影响的上游和下游依赖项
- 如果适用，确定引入新字段、函数或变量的位置

## 结果输出格式：
你的最终输出应列出需要修改的位置，包括但不限于bug出现的位置、为满足功能特性需要修改的位置等，并用三个反引号 ``` 包裹输出内容。
每个输出位置应包含文件路径、函数名或行号，如果这样的位置有多个，请按重要性排序，由高到低输出，最多不超过3个。

### 示例：
```
service/product_service.go
method: ProductService.CheckStock
line: 10

repository/payment_repo.go
line: 156
line: 24
function: generatePaymentID
```

注：你的思考应全面，因此内容较长也没关系，另外请用中文输出。
"""

FAKE_USER_MSG_FOR_LOC = (
    'Verify if the found locations contain all the necessary information to address the issue, and check for any relevant references in other parts of the codebase that may not have appeared in the search results. '
    'If not, continue searching for additional locations related to the issue.\n'
    'Verify that you have carefully analyzed the impact of the found locations on the repository, especially their dependencies. '
    'If you think you have solved the task, please send your final answer (including the former answer and reranking) to user through message and then call `finish` to finish.\n'
    'IMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n'
)