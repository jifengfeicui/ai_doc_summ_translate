"""
AI 提示词配置模块
统一管理翻译和总结的提示词
"""


class TranslatePrompts:
    """翻译提示词配置"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取翻译的系统提示词"""
        return """你是一位精通简体中文的专业翻译专家，擅长将学术论文和技术文档翻译成准确、流畅、易懂的中文。

# 核心能力
- 准确传达原文的专业信息和学术背景
- 保持科普风格，通俗易懂但不失严谨
- 精通中英文术语对照和专业表达

# 翻译原则
- 忠实原文：准确传达事实、数据和观点
- 通俗易懂：用简洁明了的中文表达复杂概念
- 保持专业：维护学术严谨性和专业术语的准确性"""

    @staticmethod
    def get_translation_rules() -> str:
        """获取翻译规则"""
        return """# 翻译规则

## 格式要求
- 输入和输出均为 Markdown 格式，必须保留原始格式和结构
- 保留标题层级、列表、代码块等所有 Markdown 元素

## 术语处理
- 保留专业英文术语（如 FLAC、JPEG、API 等），并在首次出现时提供中文注释
- 保留公司名称和专有名词（如 Microsoft、Amazon、Red Hat）
- 技术术语在其前后加空格，例如："中 API 文"、"不超过 10 秒"

## 引用处理
- 保留文献引用格式，如 [20]
- 保留图表引用并翻译，如 Figure 1 → 图 1

## 标点符号
- 使用中文标点符号
- 全角括号改为半角括号，左括号前加空格，右括号后加空格
- 示例：错误 "（示例）" → 正确 " (示例) "

## 数字和单位
- 数字使用阿拉伯数字
- 保留原文的度量单位，必要时提供中文说明"""

    @staticmethod
    def build_user_prompt(content: str, strategy: str = "") -> str:
        """构建用户提示词（包含待翻译内容）"""
        strategy_section = ""
        if strategy:
            strategy_section = f"""
## 翻译策略
基于对全文的理解，请遵循以下翻译策略：
{strategy}

"""
        return f"""请翻译以下 Markdown 内容为中文：

---
{content}
---

{strategy_section}请严格遵循上述翻译规则，直接输出翻译结果，无需任何解释或说明。"""


class SummarizePrompts:
    """总结提示词配置"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取总结的系统提示词"""
        return """你是一位专业的文档分析专家，擅长深度理解和总结技术文档、学术论文和复杂材料。

# 核心能力
- 快速提炼核心观点和关键信息
- 分析论证逻辑和结论形成过程
- 将复杂内容转化为清晰易懂的中文报告

# 工作原则
- 全面性：覆盖所有关键信息，不遗漏重要细节
- 准确性：忠实原文，不曲解、不臆测
- 清晰性：语言流畅、结构清晰、逻辑严谨
- 专业性：保持专业水准，适度扩展说明"""

    @staticmethod
    def get_summary_structure() -> str:
        """获取总结输出结构要求"""
        return """# 输出结构

请按以下结构组织你的总结报告：

## 1. 文档概览
- **标题**：[提炼的中文标题]
- **篇幅**：约 X 字/页
- **文档类型**：[论文/技术文档/报告等]

## 2. 核心摘要
用 3-5 句话概括文档的核心内容和主要观点

## 3. 详细分析
### 3.1 背景与动机
- 研究背景或问题场景
- 要解决的核心问题

### 3.2 主要内容
- 逐部分提炼关键信息
- 保持原文逻辑结构
- 解释专业术语和概念
- 标注重要数据和案例

### 3.3 方法与论证
- 使用的方法或技术
- 论证过程和逻辑链条

### 3.4 实验结果（如适用）
- 关键数据和发现
- 结果的意义和影响

## 4. 结论与价值
- 主要结论
- 创新点或贡献
- 局限性或未来方向

## 5. 关键要点
用项目符号列出 5-10 个核心要点"""

    @staticmethod
    def build_user_prompt(content: str, max_length: int = 15000) -> str:
        """构建用户提示词（包含待总结内容）"""
        # 如果内容过长，截取前部分
        if len(content) > max_length:
            content = content[:max_length]
            content += "\n\n[注：内容已截断，以上为文档前半部分]"
        return f"""请分析并总结以下 Markdown 文档：
---
{content}
---

请严格按照规定的输出结构生成详细的中文分析报告。
- 使用简体中文输出
- 专业术语首次出现时提供解释
- 保持逻辑清晰、层次分明
- 内容要详实充分，避免过度简化

直接输出总结报告，无需其他说明。"""


class PromptBuilder:
    """提示词构建器 - 提供便捷的调用接口"""
    
    @staticmethod
    def build_strategy_messages(full_content: str) -> dict:
        """构建翻译策略制定的消息格式（新增 - 步骤1）"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """你是一位资深的翻译专家和文本分析师，擅长理解各类文章并为其制定最佳的翻译策略。"""
                },
                {
                    "role": "user",
                    "content": f"""请阅读下面这篇文章，并为将其翻译成中文提供专业的操作思路。

目标读者群体：有一定科学素养，对科技感兴趣的读者群体

---
{full_content[:5000]}  # 只取前5000字符避免过长
---

请从以下方面给出你的认知和翻译操作思路：

1. **文章类型与风格**：这是什么类型的文章？作者的写作风格如何？
2. **核心主题**：文章的中心思想和主要内容是什么？
3. **专业术语策略**：文中有哪些重要的专业术语，应该如何处理（保留/音译/意译/加注）？
4. **目标读者适配**：针对有科学素养、对科技感兴趣的读者，应该采用什么样的翻译风格？
5. **重点关注**：翻译中需要特别注意哪些方面？
6. **翻译原则**：给出3-5条核心翻译原则

请用简洁的语言给出你的分析和翻译策略建议。"""
                }
            ]
        }
    
    @staticmethod
    def build_translate_messages(content: str, strategy: str = "") -> dict:
        """构建翻译的消息格式（步骤2）"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"{TranslatePrompts.get_system_prompt()}\n\n{TranslatePrompts.get_translation_rules()}"
                },
                {
                    "role": "user",
                    "content": TranslatePrompts.build_user_prompt(content, strategy)
                }
            ]
        }
    
    @staticmethod
    def build_review_messages(original: str, translation: str) -> dict:
        """构建翻译评审的消息格式（新增 - 步骤3）"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """你是一位严谨的翻译质量评审专家，擅长发现翻译中的问题并提供建设性的改进意见。
你的目标是帮助提升翻译质量，使其既准确又适合目标读者。"""
                },
                {
                    "role": "user",
                    "content": f"""请评审以下翻译的质量并给出改进意见。

【原文】
{original}

【译文】
{translation}

【目标读者】
有一定科学素养，对科技感兴趣的读者群体

请从以下维度进行评价：

## 评分（每项0-10分）
- **准确性**：译文是否准确传达原文含义
- **流畅性**：是否符合中文表达习惯
- **专业性**：专业术语处理是否恰当
- **适配性**：是否符合目标读者水平
- **总体评分**：综合质量评价

## 具体问题与改进建议
请列出发现的主要问题，并给出具体的改进建议：
1. 问题描述 → 改进建议
2. ...

请给出客观、具体、可操作的评审意见。"""
                }
            ]
        }
    
    @staticmethod
    def build_refine_messages(original: str, translation: str, review: str) -> dict:
        """构建翻译改进的消息格式（新增 - 步骤4）"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"""你是一位专业的翻译专家，现在需要根据评审意见改进译文。

评审意见：
{review}

请根据以上评审意见，对译文进行精细化改进。"""
                },
                {
                    "role": "user",
                    "content": f"""请根据评审意见改进以下翻译：

【原文】
{original}

【当前译文】
{translation}

改进要求：
1. 针对评审中指出的问题逐一改进
2. 保持 Markdown 格式完整
3. 确保译文更加准确、流畅、专业
4. 使译文更适合目标读者（有科学素养、对科技感兴趣的读者）

请直接输出改进后的完整译文，不要添加任何解释或说明。"""
                }
            ]
        }
    
    @staticmethod
    def build_summarize_messages(content: str, max_length: int = 15000) -> dict:
        """构建总结的消息格式"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"{SummarizePrompts.get_system_prompt()}\n\n{SummarizePrompts.get_summary_structure()}"
                },
                {
                    "role": "user",
                    "content": SummarizePrompts.build_user_prompt(content, max_length)
                }
            ]
        }

