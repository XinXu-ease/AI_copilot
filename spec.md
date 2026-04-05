
# AI Product Team Copilot v1 系统设计文档

## 1. 项目概述

### 1.1 项目名称

AI Product Team Copilot

### 1.2 项目目标

构建一个面向产品早期探索与 MVP 定义阶段的多智能体系统，帮助用户从一个模糊的产品想法出发，逐步完成问题定义、用户研究、UX 方案设计与 MVP 开发建议。

系统通过四个核心 agent 协同工作，模拟一个小型产品团队的流程：

PM / Supervisor Agent
Research Agent
UX Designer Agent
Developer Agent

系统接收用户输入的初始产品想法，通过多轮交互补全关键信息，再组织各 agent 按阶段完成分析、输出和反馈，最终生成一版结构化的产品方案与 MVP 开发建议。

### 1.3 v1 范围

v1 聚焦以下能力：

输入产品想法并通过 PM agent 补全 brief
进行市场与问题空间研究
输出 insights、opportunities 与 DVF 初步分析
生成 UX deliverables，如 persona、journey、IA、核心流程
生成 MVP 功能建议、技术实现建议和开发任务拆解
以 Streamlit 提供交互界面
以 Python 作为后端主语言
以 PostgreSQL 存储项目状态、产物与历史版本

v1 暂不包含：

真实网页自动爬虫规模化系统
复杂长期记忆
多人协作
真正可运行的完整前后端产品代码生成
自动化访谈录音转写
高度自治的 agent 自由对话

---

## 2. 产品定位

### 2.1 核心价值主张

让一个用户从“我想做一个什么东西”出发，得到一套接近真实产品团队产出的阶段性成果，包括：

问题定义
市场与竞品认知
目标用户洞察
产品机会点
UX 结构方案
MVP 范围与开发建议

### 2.2 目标用户

适合三类用户：

设计或产品学生，用于课程项目和 portfolio
独立开发者或创业者，用于前期探索和梳理
产品经理或 UX researcher，用于加速 early-stage discovery

### 2.3 核心使用场景

用户输入一个初步想法，例如：
“我想做一个帮助国际学生找室友和协调合租沟通的产品。”

系统会：

先通过 PM agent 追问并补全 brief
组织 Research agent 做市场、竞品、问题空间研究
由 PM、UX、Developer 对 research 输出做反馈与验证
Research agent 根据反馈进行第二轮研究
UX agent 生成结构化 UX 输出
其他 agent 对 UX 输出进行反馈
UX agent 根据反馈进行第二轮研究
Developer agent 根据 UX 输出定义 MVP
PM agent 汇总并输出阶段性决策与建议

---

## 3. 系统角色设计

## 3.1 PM / Supervisor Agent

### 职责

PM agent 是系统的 orchestrator，不负责重度专业产出，而负责流程推进、任务拆解、质量检查和状态管理。

### 核心能力

理解用户自然语言输入
识别缺失信息并追问用户
把用户输入转成结构化 project brief
向其他 agent 下达任务
整合其他 agent 输出
从 DVF（desiability、visbility、feasibility） 和 business 角度做阶段性判断
决定下一轮 workflow

### 输入

用户自然语言产品想法
历史状态
各 agent 产出

### 输出

结构化 project brief
agent task instructions
阶段性总结
DVF 分析
优先级建议
下一步 action plan

### PM 追问维度

What are you trying to build?
Why build it?
What problem does it solve?
Who are the possible users?
What alternatives already exist?
What constraints do you have?
What stage are you at now?
What kind of output do you want?

### 示例输出结构

```json
{
  "project_brief": {
    "idea_summary": "",
    "problem_statement": "",
    "target_users": [],
    "existing_alternatives": [],
    "business_goal": "",
    "constraints": [],
    "desired_outputs": []
  }
}
```

---

## 3.2 Research Agent

### 职责

负责外部信息搜集、研究总结、洞察归纳和机会点提炼。

### 核心能力

市场研究
竞品分析
用户问题空间分析
访谈提纲生成
研究发现整理
insight 与 opportunity 提炼

### 输入

PM 分发的 research task
project brief
已有 research history

### 输出

market landscape
competitor analysis
user pain points
research insights
opportunity areas
open questions

### 输出原则

不直接给“大而空”的产品建议
必须区分 evidence、interpretation、hypothesis
尽量以结构化格式输出，便于下一 agent 使用

### 示例输出结构

```json
{
  "research_output": {
    "market_summary": [],
    "competitors": [
      {
        "name": "",
        "positioning": "",
        "strengths": [],
        "weaknesses": []
      }
    ],
    "user_pain_points": [],
    "insights": [],
    "opportunities": [],
    "risks_or_unknowns": []
  }
}
```

---

## 3.3 UX Designer Agent

### 职责

把研究结果转化为 UX 层面的交付物。

### 核心能力

定义 persona
绘制 journey
建立 IA
设计 task flow
梳理 interaction principles
输出低保真产品结构说明

### 输入

validated research insights
opportunity areas
product hypothesis
business and feasibility constraints

### 输出

persona
journey map
information architecture
task flow
interaction design recommendations
wireframe-level MVP structure

### 输出原则

必须基于研究，不凭空创造
强调结构清晰与 MVP 导向
避免过度视觉化描述，优先逻辑和信息组织

### 示例输出结构

```json
{
  "ux_output": {
    "personas": [],
    "journey_map": [],
    "information_architecture": {},
    "core_user_flows": [],
    "interaction_principles": [],
    "mvp_screen_spec": []
  }
}
```

---

## 3.4 Developer Agent

### 职责

将 UX 输出和产品定义转为 MVP 开发建议与技术实现方案。

### 核心能力

功能模块拆解
技术栈建议
前后端模块划分
数据库 schema 初步设计
API 结构建议
开发任务拆解

### 输入

UX output
project constraints
MVP scope
PM priority

### 输出

feature breakdown
system modules
technical architecture
DB schema draft
API endpoints draft
development task list

### 输出原则

面向 MVP，而不是完整商业产品
优先低复杂度可落地方案
明确实现风险与依赖

### 示例输出结构

```json
{
  "dev_output": {
    "mvp_features": [],
    "tech_stack": [],
    "frontend_modules": [],
    "backend_modules": [],
    "database_tables": [],
    "api_drafts": [],
    "dev_tasks": []
  }
}
```

---

## 4. 整体工作流设计

v1 采用“阶段式多轮协作”而不是完全自由协商。

## 4.1 Workflow 总览

### Phase 0：Project Intake

用户输入初始产品想法
PM agent 判断信息是否充分
如不足，向用户追问
生成结构化 brief

### Phase 1：Research Round 1

PM 向 Research agent 下达第一轮 research task
Research agent 输出初步研究结果
PM、UX、Developer 对结果进行反馈
PM 汇总反馈，决定是否进入第二轮研究

### Phase 2：Research Round 2

Research agent 根据反馈进行补充研究
PM 评估问题定义、机会点与 DVF 初步判断
形成相对稳定的 insight/opportunity package

### Phase 3：UX Design

PM 向 UX agent 分发任务
UX agent 生成 persona、journey、IA、task flow 等
PM、Research、Developer 对 UX 输出做反馈
UX agent 根据反馈迭代一轮

### Phase 4：MVP Definition

PM 将验证后的 UX 输出交给 Developer agent
Developer agent 生成 MVP 功能与实现建议
PM 从 business 和 DVF 角度做最终汇总

### Phase 5：Final Output

输出项目报告，包含：
问题定义
研究摘要
insights 和 opportunities
UX deliverables
MVP 范围
技术建议
风险与下一步验证建议

---

## 4.2 LangGraph 风格节点设计

虽然你说后端用 LangChain，但这里更推荐用 LangGraph 处理 orchestration，因为你的流程很明显是有状态、有节点、有条件分支的。

可以设计成这些节点：

`intake_node`
`pm_clarification_node`
`research_round1_node`
`cross_feedback_on_research_node`
`research_round2_node`
`pm_dvf_checkpoint_node`
`ux_design_node`
`cross_feedback_on_ux_node`
`ux_revision_node`
`developer_mvp_node`
`final_summary_node`

### 条件边

如果 brief 不完整，回到 clarification
如果 research 信心不足，进入第二轮 research
如果 UX 结构不一致，进入 UX revision
如果到达 MVP 定义标准，进入 developer 阶段

---

## 5. 用户交互设计

## 5.1 Streamlit 前端定位

前端不是单纯聊天框，而是一个“项目工作台”。

### 页面建议

第一页：Project Intake
第二页：Research Workspace
第三页：UX Deliverables
第四页：MVP Plan
第五页：Project History / Versions

## 5.2 Intake 页面

PM agent 引导式提问：

What do you want to build?
What problem are you trying to solve?
Who may experience this problem?
What solutions already exist?
Why is this worth building now?
Do you have any constraints?
What output do you want most?

### 输入形式

文本框
可选标签
多轮问答
Brief summary preview

### 输出

确认后的 project brief

---

## 5.3 Research 页面

展示：

PM 分发给 Research 的任务
Research 输出
其他 agent 的反馈
当前未解决问题
继续 research 的按钮

---

## 5.4 UX 页面

展示：

persona
journey
IA
core flows
各 agent 对 UX 的评论与修订建议

---

## 5.5 MVP 页面

展示：

功能优先级
模块划分
技术栈建议
开发任务列表
MVP 风险说明

---

## 6. 数据与状态设计

## 6.1 全局状态对象

整个 workflow 应维护一个统一 ProjectState。

```python
class ProjectState(TypedDict):
    project_id: str
    brief: dict
    clarification_history: list
    research_rounds: list
    validated_insights: list
    opportunities: list
    dvf_analysis: dict
    ux_outputs: list
    dev_outputs: list
    decisions_log: list
    current_phase: str
    next_action: str
```

## 6.2 关键状态字段说明

### brief

用户目标、问题、用户、替代方案、约束等

### research_rounds

每轮 research 的输出、反馈和 revision notes

### validated_insights

经过 PM 判断可用于后续设计的核心 insight

### opportunities

基于 insight 提炼出的设计与产品机会点

### dvf_analysis

desirability, viability, feasibility 三个维度的判断与风险

### ux_outputs

所有 UX 结构化交付物及版本历史

### dev_outputs

MVP 功能、技术方案、任务拆解

### decisions_log

记录每个阶段为什么这样推进，便于追溯

---

## 7. 数据库存储设计（PostgreSQL）

建议不要只存最终结果，而是存“项目、轮次、agent 输出、版本”。

## 7.1 表设计

### projects

存项目主信息

字段：
id
title
created_at
updated_at
status
owner_id
initial_idea

### project_briefs

存结构化 brief 版本

字段：
id
project_id
version
brief_json
created_at

### agent_runs

记录每次 agent 执行

字段：
id
project_id
agent_name
phase
input_json
output_json
created_at
status

### research_rounds

记录每轮研究

字段：
id
project_id
round_number
task_instruction
research_output_json
feedback_json
created_at

### ux_versions

记录 UX 版本

字段：
id
project_id
version
ux_output_json
feedback_json
created_at

### dev_versions

记录开发方案版本

字段：
id
project_id
version
dev_output_json
created_at

### decision_logs

记录 PM 决策日志

字段：
id
project_id
phase
decision_type
decision_content
created_at

---

## 8. Agent 通信方式设计

所有 agent 都通过 PM agent 间接协作
PM 读取 state 后向某 agent 发 instruction
agent 输出结构化结果
PM 再把需要的结果传给下一个 agent

### 原因

更可控
更容易 debug
更适合课程项目和 MVP
避免 agent 之间无边界漂移

### 通信格式建议

统一用结构化任务对象：

```json
{
  "task_type": "research_analysis",
  "objective": "Identify user pain points and market gaps",
  "context": {...},
  "constraints": [...],
  "expected_output_format": {...}
}
```

---

## 9. Prompt 设计原则

## 9.1 PM Agent Prompt

强调其角色是 orchestrator，而不是内容生成器。
必须做到：

先判断信息是否足够
必要时追问
把模糊需求转成结构化任务
基于其他 agent 输出做决策
显式记录 DVF 和 business 视角判断

## 9.2 Research Agent Prompt

强调 evidence-first。
必须区分：

what is observed
what is inferred
what remains uncertain

## 9.3 UX Agent Prompt

强调 research-grounded。
不允许无依据地生成 persona 或流程。
所有设计输出应可追溯到 insight 或约束。

## 9.4 Developer Agent Prompt

强调 MVP-first。
优先简单、可行、低耦合实现。
输出中必须标明 assumed constraints 和 implementation risks。

---

## 10. 核心模块实现建议

## 10.1 Orchestrator 模块

负责：

读取状态
调用 agent
更新状态
决定下一节点

可命名为：
`workflow_manager.py`

## 10.2 Agent Wrapper 模块

每个 agent 一个 class：

`pm_agent.py`
`research_agent.py`
`ux_agent.py`
`developer_agent.py`

每个 class 至少有：
`build_prompt()`
`run()`
`validate_output()`

## 10.3 State Manager 模块

负责状态读写、版本记录和数据库同步。

`state_manager.py`

## 10.4 Output Parser 模块

负责将 agent 文本输出解析成结构化对象。

`parsers.py`

## 10.5 Streamlit UI 模块

负责页面、用户输入、状态展示。

`app.py`

---

## 11. 目录结构建议

```bash
ai-product-team-copilot/
├── app.py
├── requirements.txt
├── README.md
├── src/
│   ├── agents/
│   │   ├── pm_agent.py
│   │   ├── research_agent.py
│   │   ├── ux_agent.py
│   │   └── developer_agent.py
│   ├── workflows/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── router.py
│   ├── state/
│   │   ├── schemas.py
│   │   ├── state_manager.py
│   │   └── serializers.py
│   ├── db/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── crud.py
│   ├── prompts/
│   │   ├── pm_prompt.py
│   │   ├── research_prompt.py
│   │   ├── ux_prompt.py
│   │   └── dev_prompt.py
│   ├── utils/
│   │   ├── parsers.py
│   │   ├── validators.py
│   │   └── formatters.py
│   └── ui/
│       ├── intake_page.py
│       ├── research_page.py
│       ├── ux_page.py
│       └── mvp_page.py
└── migrations/
```

---

## 12. 典型执行流程示例

### Step 1

用户输入：
“I want to build a product that helps young adults feel more confident when making first-time investment decisions.”

### Step 2

PM 判断 brief 不完整，追问：
What specific decision moments matter most?
Who exactly are the target users?
What alternatives do they use now?
Do you want a research-heavy or MVP-heavy output?

### Step 3

PM 生成结构化 brief 并分发给 Research

### Step 4

Research 输出：
市场现状
主要竞品
用户痛点
可能机会点
未解决问题

### Step 5

PM、UX、Developer 对 research 做反馈：
痛点是否足够具体
是否支持 UX 结构设计
是否有可行 MVP 路线

### Step 6

Research 二轮补充

### Step 7

PM 做 DVF checkpoint

### Step 8

UX agent 输出 persona、journey、IA、flow

### Step 9

其他 agent 对 UX 输出进行反馈与修订

### Step 10

Developer 输出 MVP feature spec、模块、API、数据结构建议

### Step 11

PM 汇总为最终项目报告

---

## 13. MVP 输出格式建议

最终可以给用户一个结构化结果页，包含以下部分：

### 13.1 Project Summary

一句话概括产品方向

### 13.2 Problem Definition

目标问题
目标用户
已有替代方案
为什么值得解决

### 13.3 Research Summary

市场分析
竞品对比
用户痛点
核心 insights
opportunities

### 13.4 DVF Analysis

Desirability
Viability
Feasibility
关键风险

### 13.5 UX Deliverables

persona
journey
IA
task flow
MVP screen structure

### 13.6 MVP Development Plan

功能优先级
模块拆解
技术建议
数据库与 API 草案
开发任务列表

### 13.7 Next Validation Steps

建议做的用户测试
需要验证的关键假设
下一轮迭代建议

---

## 14. 风险与边界

### 14.1 研究真实性风险

如果没有真实用户数据，Research 和 UX 输出可能偏假设性。
解决方式：明确标注哪些是 evidence，哪些是 hypothesis。

### 14.2 Agent 漂移风险

多个 agent 容易重复、跑偏或自相矛盾。
解决方式：PM 中控 + 结构化输出 + 统一 state。

### 14.3 输出过大过空

agent 容易产生很长但不 actionable 的内容。
解决方式：要求 JSON-like 结构输出，并限制每阶段 deliverable 范围。

### 14.4 Developer 输出不贴合 UX

如果 UX spec 不清晰，dev agent 会产生泛泛技术建议。
解决方式：要求 UX 输出包含 screen spec、flow 和 feature boundaries。

---

## 15. 第一阶段开发建议

你可以按这个顺序做。

### A1

搭项目基础结构
完成 Streamlit intake 页面
实现 PM agent 的提问和 brief 生成
定义 ProjectState schema

### A2

实现 Research agent
完成第一轮 research workflow
实现状态存储到 Postgres
做 research 结果展示页

### A3

实现 UX agent
完成 UX 输出展示
实现 cross-feedback 机制

### A4

实现 Developer agent
完成 MVP 输出模块
完成 PM 最终总结页

### A5

优化 prompt
加版本记录
加导出 markdown 或 pdf

---

## 16. 推荐的 v1 成功标准

如果 v1 达到下面这些，就已经是一个成立的项目：

用户可以输入一个产品想法
PM 能够自动追问并整理 brief
Research 能输出结构化洞察
UX 能基于 insight 输出 IA 和 flow
Developer 能输出一版合理的 MVP 方案
所有阶段结果可在 Streamlit 中查看和回溯
项目状态可保存到 Postgres

---
