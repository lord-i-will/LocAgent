;; go.scm - Tree-sitter 查询文件（Go 语言全覆盖版，适配 tree-sitter-go 0.19.1+ 语法节点）
;; 语法规范参考：https://github.com/tree-sitter/tree-sitter-go/blob/master/src/grammar.json

;; ============================== 注释 ==============================
;; 匹配所有注释（单行//和多行/**/）
(comment) @root @definition.comment

;; ============================== 包声明 ==============================

;; 包声明
(package_clause
  "package" @keyword.package
  (package_identifier) @reference.identifier) @root @definition.package

;; ============================== 导入声明 ==============================

;; 单行导入 - 基础形式（import "fmt"）
(import_declaration
  "import" @keyword.import
  (import_spec
    (interpreted_string_literal) @reference.identifier @identifier)) @root @definition.import

;; 单行导入 - 带别名（import m "math"）
(import_declaration
  "import" @keyword.import
  (import_spec
    name: (package_identifier) @identifier
    path: (interpreted_string_literal) @reference.identifier)) @root @definition.import

;; 单行导入 - 点导入 (import . "package")
;; 将目标包的导出内容直接注入当前作用域（无需通过包名访问），. 是一个特殊操作符，标记为 @operator.dot。
(import_declaration
  "import" @keyword.import
  (import_spec
    name: (dot) @identifier
    path: (interpreted_string_literal) @reference.identifier)) @root @definition.import

;; 单行导入 - 空白标识符 (import _ "package")
;; 仅执行目标包的 init() 函数，不导入任何符号。
(import_declaration
  "import" @keyword.import
  (import_spec
    name: (blank_identifier) @identifier
    path: (interpreted_string_literal) @reference.identifier)) @root @definition.import

;; 原始字符串导入 (反引号)
;; 匹配 无别名、直接使用反引号路径 的导入语句：import `github.com/user/project`
(import_declaration
  "import" @keyword.import
  (import_spec
    (raw_string_literal) @reference.identifier @identifier)) @root @definition.import

;; 带别名的原始字符串导入：import mypkg `github.com/user/project`
(import_declaration
  "import" @keyword.import
  (import_spec
    name: (package_identifier) @identifier
    path: (raw_string_literal) @reference.identifier)) @root @definition.import

;; 多行导入 - 基础形式
;; (import_spec ...)* 表示匹配括号内的 0 个或多个导入项（* 表示重复），每个 import_spec 中的路径字符串标记为 @string.import）。
;; 示例：
;; import (
;;    "fmt"
;;    "math/rand"
;;    "strings"
;;)
(import_declaration
  "import" @keyword.import
  (import_spec_list
    "(" @punctuation.bracket
    (import_spec
      (interpreted_string_literal) @reference.identifier @identifier)*
    ")" @punctuation.bracket)) @root @definition.import

;; 多行导入 - 混合形式 (包含直接导入、别名、点导入、空白导入)
;; 导入时的引号分类：
;;  interpreted_string_literal：双引号字符串（如 "fmt"），支持转义字符。
;;  raw_string_literal：反引号字符串（如 `my/pkg`），不处理转义。
(import_declaration
  "import" @keyword.import
  (import_spec_list
    "(" @punctuation.bracket
    (import_spec
      [
        (interpreted_string_literal) @reference.identifier @identifier
        (raw_string_literal) @reference.identifier @identifier
      ])*
    (import_spec
      name: (package_identifier) @identifier
      path: [
        (interpreted_string_literal) @reference.identifier
        (raw_string_literal) @reference.identifier
      ])*
    (import_spec
      name: (dot) @identifier
      path: [
        (interpreted_string_literal) @reference.identifier
        (raw_string_literal) @reference.identifier
      ])*
    (import_spec
      name: (blank_identifier) @identifier
      path: [
        (interpreted_string_literal) @reference.identifier
        (raw_string_literal) @reference.identifier
      ])*
    ")" @punctuation.bracket)) @root @definition.import

;; ============================== 类型定义 ==============================

;; 顶层类型声明（type 关键字入口）
;; 1. 单类型定义 (type T struct{})
;; 2. 类型别名 (type T = string)
;; 示例：type UUID = string                // @type.alias
;; 3. 分组类型声明 (type ( T1 struct{}; T2 int ))
;; 示例：
;; type (                       // @type.group
;;   Counter int                // @type.declaration
;;   StringList []string        // @type.declaration
;; )
(type_declaration
  "type" @keyword.type
  [
    (type_spec
      name: (type_identifier) @type.name
      type_parameters: (type_parameter_list)? @type.parameters
      type: (_) @type.definition
    ) @type.declaration
    (type_alias
      name: (type_identifier) @type.name
      "=" @operator
      type: (_) @type.definition
    ) @type.alias
    (
      "(" @punctuation.bracket
      (
        [
          (type_spec) @type.declaration
          (type_alias) @type.alias
        ]
        [
          "\n" @punctuation.delimiter
          ";" @punctuation.delimiter
        ]
      )*
      ")" @punctuation.bracket
    ) @type.group
  ]
) @root @definition.type

;; 结构体类型定义细节，包括：具名字段（含多字段声明）、嵌入字段（匿名/指针嵌入）
;; 示例：
;; type ApiResponse[T any] struct {
;;     Code    int         `json:"code"` // Code->@field.name, int->@type.field, `json:"code"`->@tag
;;     Data    T           `json:"data"`
;;     Errors  []Error     `json:"errors,omitempty"`
;;     *logging.Logger     // 指针嵌入
;;     io.ReadCloser       // 接口嵌入
;;     Metadata
;; }
(struct_type
  "struct" @keyword.struct
  (field_declaration_list
    "{" @punctuation.bracket
    (
      (field_declaration
        [
          (
            (field_identifier) @field.name
            ("," @punctuation.delimiter
             (field_identifier) @field.name)*
            type: (_) @type.field
          )
          (
            (type_identifier) @type.embedded
            (qualified_type) @type.embedded
            (generic_type) @type.embedded
            (
              "*" @operator
              [
                (type_identifier) @type.embedded
                (qualified_type) @type.embedded
                (generic_type) @type.embedded
              ]
            )
          )
        ]
        tag: (raw_string_literal)? @tag
      )
      [
        "\n" @punctuation.delimiter
        ";" @punctuation.delimiter
      ]?
    )*
    "}" @punctuation.bracket
  ) @type.body
) @type.definition

;; 接口类型定义细节
;; 示例：
;; type Correct interface {
;;     // 方法声明
;;     Get(id string) (T, error)  ; @method.name + @parameters + @return.types
;;     // 类型组合
;;     io.Reader | json.Marshaler ; @embedded.interface + @operator
;; }
(interface_type
  "interface" @keyword.interface
  "{" @punctuation.bracket
  (
    [
      ; 情况1：方法声明（使用原始字段定义）
      (
        (field_identifier) @method.name
        (parameter_list)? @parameters
        [
          (parameter_list) @return.types  ; 多返回值
          (_simple_type) @return.type     ; 单返回值
        ]?
      )
      ; 情况2：类型元素（直接使用_type匹配）
      (
        (_) @embedded.interface
        ("|" @operator
         (_) @embedded.interface)*
      )
    ]
    ["\n" @punctuation.delimiter
     ";" @punctuation.delimiter]?
  )*
  "}" @punctuation.bracket
) @interface.definition

;; ============================== 函数/方法 ==============================
;; 支持通用参数列表、泛型类型参数、多返回值、单返回值
(function_declaration
  "func" @keyword.function
  name: (identifier) @identifier
  type_parameters: (type_parameter_list)? @parameter.type
  parameters: (parameter_list
    (parameter_declaration
      name: (identifier)? @parameter.identifier
      type: (_) @parameter.type
    )*
    ","? @punctuation.delimiter
  )
  result: [
    (parameter_list
      (parameter_declaration
        name: (identifier)? @reference.identifier
        type: (_) @reference.type
      )*
    ) @return.region
    (_simple_type) @reference.type
  ]?
  body: (block
    "{" @punctuation.bracket
    .
    [
      (
        (comment) @child.first
        .
        (_) @child.first
      )
      (_) @child.first
    ]
    "}" @punctuation.bracket
  )
) @root @definition.function

;; 支持通用参数列表、泛型类型参数（Go 1.18+）、多返回值、单返回值、方法体处理（兼容接口声明）
(method_declaration
  "func" @keyword.function
  receiver: (parameter_list
    "(" @punctuation.bracket
    (parameter_declaration
      name: (identifier)? @identifier
      type: (_) @receiver.type
    )
    ")" @punctuation.bracket
  ) @receiver.region
  name: (field_identifier) @identifier
  type_parameters: (type_parameter_list)? @parameter.type
  parameters: (parameter_list
    (parameter_declaration
      name: (identifier)? @parameter.identifier
      type: (_) @parameter.type
    )*
    ","? @punctuation.delimiter
  )
  result: [
    (parameter_list
      "(" @punctuation.bracket
      (parameter_declaration
        name: (identifier)? @reference.identifier
        type: (_) @reference.type
        ","? @punctuation.delimiter
      )*
      ")" @punctuation.bracket
    )
    (_simple_type) @reference.type
  ]?
  body: (block
    "{" @punctuation.bracket
    .
    [
      (
        (comment) @child.first
        .
        (_) @child.first
      )
      (_) @child.first
    ]
    "}" @punctuation.bracket
  )
) @root @definition.function


;; ============================== 赋值语句 ==============================

;; 示例：
;; a += 5          // @operator.assignment 匹配 +=
;; b, c = fn()     // 匹配两个@variable.left和一个@value.right
(assignment_statement
  left: (expression_list
    (_expression) @variable.left
    ("," @punctuation.delimiter
     (_expression) @variable.left)*
  ) @assignment.lhs
  ; 使用通配符_匹配所有赋值运算符
  operator: _ @operator.assignment
  right: (expression_list
    (_expression) @value.right
    ("," @punctuation.delimiter
     (_expression) @value.right)*
  ) @assignment.rhs
) @assignment.statement

;; ============================== 函数调用 ==============================


