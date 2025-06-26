;; ============================== 模块定义 ==============================

;; 1. module：表示匹配整个 Python 文件（模块）作为根节点，每个.py文件都会被识别为一个module节点
;; 2. . (_)：.表示直接子节点关系，_是通配符匹配任意类型的节点
;; 3. @child.first：捕获模块的第一个顶层元素，通常是模块文档字符串（docstring）、第一个import语句第一个函数/类定义
;; 示例：
;; (1) 带文档字符串的模块：
;; """这是模块文档字符串"""  # <-- 被 @child.first 捕获
;; import sys
;; (2) 以import开头的模块：
;; import os  # <-- 被 @child.first 捕获
;; from sys import path
(module . (_) @child.first @definition.module) @root

;; ============================== 带装饰器的定义 ==============================

;; 匹配被装饰的函数/类
;; 示例：
;; @log_execution_time  # <-- 装饰器
;; def calculate(x):    # <-- 被 @check_child 捕获
;;     return x * 2
;; @dataclass          # <-- 装饰器
;; class User:         # <-- 被 @check_child 捕获
;;     name: str
(decorated_definition [
    (function_definition) @check_child
    (class_definition) @check_child
  ]
) @root

;; ============================== 类定义 ==============================

;; 基础类定义（带注释和首尾节点标记）
;; 1. 类名捕获：(identifier) @identifier 标记类名
;; 2. 类注释捕获：(comment) @child.first 捕获类定义上方的注释，同时标记为 @definition.class（表示这是类定义的入口）
;; 3. 类体最后一个节点：(block (_) @child.last) 捕获类体的最后一个成员
;; 示例：
;; # Class docstring  <-- @child.first @definition.class
;; class Person:      # <-- @identifier
;;     def __init__(self):
;;         pass
;;     def show(self): # <-- @child.last
;;         pass
(class_definition
  (identifier) @identifier
  (comment) @child.first @definition.class
  .
  (block (_) @child.last .)
) @root

;; 带继承的类定义（捕获父类信息）
;; 1. 类名捕获：(identifier) @identifier 标记类名
;; 2. 继承列表捕获：(argument_list (identifier) @reference.type) 捕获所有父类
;; 3. 类体第一个节点：(block . (_) @child.first) 捕获类体的第一个成员
;; 示例：
;; class Vector(Sequence):  # Sequence 被 @reference.type 捕获
;;     """数学向量"""        # <-- @child.first
;;     def __init__(self):
;;         self.data = []
(class_definition
  (identifier) @identifier
  (argument_list
    (
      [
        (identifier) @reference.type
      ]
      (",")?
    )*
  )?
  (":")
  (block . (_) @child.first)
) @root @definition.class

;; ============================== 函数定义 ==============================

(function_definition
  (identifier) @identifier
  (parameters
    ("(")
    (
      [
        (identifier)  @parameter.identifier
        (_
          (identifier) @parameter.identifier
          (":")
          (type
            [
              (identifier) @parameter.type
              (string) @parameter.type
            ]
          )
        )
      ]
      (",")?
    )*
    (")")
  )
  (
    ("->")
    (type
      [
        (identifier) @reference.identifier
        (subscript) @reference.identifier ; TODO: Extract identifiers
      ]
    )
  )?
  (":")
  .
  [
    (
      (comment) ? @child.first
      (block
        (_)
      )
    )
    (
      (block
        . (_) @child.first
      )
    )
  ]
) @root @definition.function

;; ============================== 注释 ==============================

(comment) @root @definition.comment

;; ============================== 导入语句 ==============================

;; 普通导入（带或不带别名）
;; 1. aliased_import（带别名的导入）
;; (dotted_name) → 被导入的模块名（如 numpy、pandas），标记为 @reference.identifier（表示这是一个外部引用）
;; (identifier) → 别名（如 pd），标记为 @identifier（表示这是一个本地定义的变量名）
;; 示例：import pandas as pd
;;  pandas → @reference.identifier
;;  pd → @identifier
;; 2. dotted_name（不带别名的导入）
;; 直接导入的模块名（如 numpy、os.path），同时标记为 @reference.identifier 和 @identifier（因为模块名可以直接使用）
;; 示例：import numpy/import os.path
;;  numpy → @reference.identifier + @identifier
;;  os.path → @reference.identifier + @identifier
;; 3. 整个导入语句
;; 被标记为 @root（表示这是一个完整的语法节点）
;; 标记为 @definition.import（表示这是一个导入定义）
(import_statement [
  (aliased_import
    (dotted_name) @reference.identifier
    (identifier) @identifier
  )
  (dotted_name) @reference.identifier @identifier
  ]
) @root @definition.import

;; from ... import 语句
;; 1. 带相对导入的 from ... import
;; 示例：
;; from .utils import helper
;; from ..parent import config
;; 提取的信息
;;  (relative_import)
;;      相对路径（如 .utils、..parent），标记为 @reference.module（表示这是一个模块引用）
;;  (dotted_name)
;;      导入的变量/函数名（如 helper），标记为：
;;          @reference.identifier（表示这是一个外部引用）
;;          @identifier（表示这是一个本地可用的变量名）
;;          @reference.type（用于类型推断）
(import_from_statement
  ("from")
  .
  (relative_import) @reference.module
  ("import")
  (dotted_name) @reference.identifier @identifier @reference.type
) @root @definition.import

;; 2. 绝对导入 from ... import
;; 示例：
;; from numpy import array
;; from os.path import join, basename
;; from math import sin, cos, tan
;; 提取的信息
;;  (dotted_name)（模块部分）
;;      模块名（如 numpy、os.path），标记为 @reference.module
;;  (dotted_name)（导入部分）
;;      导入的变量/函数名（如 array、join），标记为 @reference.identifier
;;      如果是多个导入（如 sin, cos, tan），每个都会单独匹配
(import_from_statement
  ("from")
  .
  (dotted_name) @reference.module
  ("import")
  (
    (dotted_name) @reference.identifier
    (",")*
  )*
) @root @definition.import

;; from __future__ import ... 语句（用于启用 Python 新特性）
;; 示例：
;; from __future__ import annotations
;; from __future__ import print_function
;; 整个 __future__ 导入语句被标记为 @root 和 @definition.import
(future_import_statement) @root @definition.import
;; 兜底规则：匹配所有未被前面规则覆盖的 from ... import 语句
;; 确保所有 import_from_statement 都能被解析
(import_from_statement) @root @definition.import

;; ============================== 赋值语句 ==============================

;; 提取赋值左右两侧的各种信息
;; 左侧（left）匹配模式：
;; 1. 简单变量名：x = 10
;;      (identifier) @identifier → x 被标记为定义的标识符
;; 2. 属性赋值（带显式点操作）：obj.attr = 10
;;  (attribute (identifier) "." (identifier)) → 整个 obj.attr
;;      标记为 @identifier（作为定义点）
;;      同时标记 @reference.dependency（因为依赖 obj）
;; 3. 通用属性赋值（更复杂的属性表达式）：self.data[0] = x
;;  (attribute) @identifier → 捕获整个属性访问表达式
;; 4. 匹配可能存在的类型注解：x: int = 10
;;  (type (identifier)) → int 被同时标记为：
;;      @reference.identifier（类型标识符）
;;      @reference.type（类型注解）
;;  对于泛型类型：x: List[str] = []
;;      (subscript (identifier)) → List 和 str 都会被捕获
;; 右侧（right）匹配模式：
;; 1. 简单变量引用：y = x
;;  (identifier) → x 被标记为：
;;      @reference.identifier（引用的标识符）
;;      @reference.dependency（依赖关系）
;; 2. 属性引用：y = obj.attr
;;  (attribute) → 整个 obj.attr 被同样标记
;; 3. 其他表达式：y = x + 1
;;  (_) @child.first → 捕获整个表达式（x + 1）
(assignment
  left: [
    (identifier) @identifier
    (attribute
      (identifier)
      (".")
      (identifier)
    ) @identifier @reference.dependency
    (attribute) @identifier
  ]
  (
    (":")
    (type
      [
        (identifier) @reference.identifier @reference.type
        (subscript .
          (identifier) @reference.identifier @reference.type
        )
      ]
    )
  )?
  right: [
    (identifier) @reference.identifier @reference.dependency
    (attribute) @reference.identifier @reference.dependency
    (_) @child.first
  ]?
) @root @definition.assignment

;; ============================== 函数调用 ==============================

;; 提取调用目标和参数中的各种标识符引用。
;; 调用目标匹配：
;; 1. 直接函数名调用：func()
;;  (identifier) @reference.identifier → func 被标记为引用的标识符
;; 2. 方法调用：obj.method()
;;  (attribute) @reference.identifier → obj.method 整个被标记
;; 参数列表解析：
;; 1. 位置参数：func(x, y)
;;  参数 x 和 y 都被标记为 @reference.identifier
;; 2. 关键字参数：func(param=value)
;;  keyword_argument 中的 value 如果是属性/变量也会被捕获
;; 3. 复杂参数：func(obj.attr, x.data)
;;  参数中的 obj.attr 和 x.data 都会被标记
;; 示例：requests.get(url, params=config.data, timeout=10)
;;  调用目标：requests.get → @reference.identifier
;;  参数列表：
;;      url → @reference.identifier
;;      config.data → @reference.identifier
;;      timeout 后的字面量 10 不会被标记
(call
  [
    (identifier) @reference.identifier
    (attribute) @reference.identifier
  ]
  (argument_list
    (
      [
        (identifier) @reference.identifier
        (attribute) @reference.identifier
        (keyword_argument
          (attribute) @reference.identifier
        )
      ]
      (",")?
    )*
  )
) @root @definition.call

;; ============================== 表达式 ==============================

;; 匹配独立的字符串字面量，并将其视为注释（@definition.comment）
;; 1. 开头的 . 表示匹配字符串必须位于表达式语句的起始位置（避免匹配嵌套在其他表达式中的字符串）。
;; 2. string 节点匹配完整的字符串字面量，包括：
;;  (string_start)：字符串起始符号（如 "、'''）。
;;  (string_content)：字符串内容。
;;  (string_end)：字符串结束符号。
;; 示例：
;; 匹配：这是一个独立的字符串表达式（没有赋值或函数调用等操作），会被规则匹配。
;;  "这是一个独立的字符串"  # <- 会被 @definition.comment 捕获
;; 不匹配：这些字符串不会被此规则捕获，因为它们嵌套在其他语法结构中。
;;  x = "字符串"          # 不是独立表达式，是赋值语句
;;  print("Hello")       # 字符串是函数调用的参数
;;  docstring = """多行
;;  字符串"""            # 虽然是字符串，但属于赋值语句
(expression_statement
  . (string
      (string_start)
      (string_content)
      (string_end)
  ) @definition.comment
) @root

;; 匹配任何独立的表达式（如函数调用、赋值、算术运算等），并标记为 @check_child 和 @root。
;; 示例：
;; x + 1          # 算术表达式
;; print("Hello")  # 函数调用
(expression_statement
  (_) @check_child
) @root

;; 捕获 return 语句及其返回值
;; 匹配 return x 中的 x，并标记为 @child.first 和 @definition.statement
;; 示例：return x + 1  # `x + 1` 会被 @child.first 捕获
(return_statement
  ("return")
  (_) @child.first @definition.statement
) @root

;; ============================== 流程控制 ==============================

(if_statement
  (":")
  (block . (_) @child.first)
) @root @definition.compound

(for_statement
  (":")
  (block . (_) @child.first)
) @root @definition.compound

(while_statement
  (":")
  (block . (_) @child.first)
) @root @definition.compound

(with_statement
  (":")
  (block . (_) @child.first)
) @root @definition.compound

(match_statement
  (":")
  (block . (_) @child.first)
) @root @definition.compound

(elif_clause
  (":")
  (block . (_) @child.first)
) @root @definition.dependent_clause

(else_clause
  (":")
  (block . (_) @child.first)
) @root @definition.dependent_clause

(except_clause
  (":")
  (block . (_) @child.first)
) @root @definition.dependent_clause

;; 匹配 finally 子句
;; : 表示匹配 `finally:` 的冒号
;; block 提取 `finally` 代码块的第一个子节点，. 表示直接子节点，确保只匹配 finally 代码块的第一个语句，而不是嵌套在其他结构中的语句。
;; 示例：
;; finally:
;;    file.close()  # <- 被 @child.first 捕获
;;    print("Done") # 不会被此规则捕获
;; @definition.dependent_clause 标记 finally 为 依赖性子句（因为它依赖于 try 或 except 语句）。
(finally_clause
  (":")
  (block . (_) @child.first)
) @root @definition.dependent_clause

;; ============================== 其它（通用兜底规则） ==============================

;; 通用的模式匹配规则，用于捕获 Python 中带有冒号(:)后跟代码块的语法结构，并提取关键信息。
;; (_ 表示匹配任意节点，":"表示匹配的节点必须包含冒号字符，. (_)表示匹配冒号后的第一个子节点，block. (_)表示匹配代码块的第一个子节点。
;; 示例：
;; if x > 0:    # 语法树：
;;              # (if_statement
;;              #   (comparison_operator)
;;              #   ":"
;;              #   (block...))
;;   print(x)
;; : 后面直接就是 (block)，所以：
;;  @child.first → print(x)（block的第一个子节点）
;;  @definition.statement → 同上
(_
  (":")
  . (_) @child.first
  (block . (_)) @definition.statement
) @root

;; 用于捕获 任何包含代码块 的语法结构，并提取该代码块的第一个子节点。
;; (_ 表示匹配任意节点，block 匹配代码块结构（由缩进或花括号界定的语句组），. (_)表示匹配冒号后的第一个子节点
;; 示例：类定义
;; class Bar:
;;    def __init__(self):  # <-- 第一次匹配（class Bar层级，整个类定义块）被 @child.first 捕获
;;        pass             # <-- 第二次匹配（def __init__层级，整个函数定义块）被 @child.first 捕获
;; 注意：
;;  每个 block 都会独立触发规则匹配
;;  外层 block 和内层 block 的 @child.first 指向不同节点
;;  这种设计正是为了支持嵌套结构的精确分析
(_
  (block . (_) @child.first)
) @root @definition.statement
