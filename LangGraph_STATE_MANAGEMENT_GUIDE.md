# LangGraph 状态管理详解与你的 product_brief 流转机制

## 核心概念

### 什么是 LangGraph 的状态管理？

LangGraph 提供了一个**中央状态存储库**（State Store），在整个工作流执行过程中：
- **单一真实来源（Single Source of Truth）**：所有数据都存储在一个统一的 `ProjectState` 对象中
- **显式流转**：状态在节点之间通过函数返回值自动合并和更新
- **完整可观测性**：每个节点接收完整的状态，处理后返回更新的部分

---

## 你的架构分析

### 1. 中央状态定义：`ProjectState`

```python
# src/schemas/state.py
class ProjectState(TypedDict, total=False):
    project_id: str
    current_phase: str
    
    brief: Optional[ProjectBrief]  # ← 你的 product_brief
    
    clarification_questions: List[str]
    clarification_answers: List[str]
    
    research_cycles: List[Dict[str, Any]]
    research_iteration: int
    
    ux_v1: Optional[UXOutput]
    ux_v2: Optional[UXOutput]
    
    dev_output: Optional[DevOutput]
    
    decisions_log: List[DecisionLog]
    # ... 更多字段
```

**关键点**：这是一个 `TypedDict`，定义了工作流中的所有可能的数据字段。

### 2. product_brief 是全局信息吗？

**是的！** 你的 `brief` 字段就是全局状态：

| 特性 | 说明 |
|------|------|
| **存储位置** | `ProjectState.brief` 中 |
| **可访问性** | 工作流中的所有节点都可以访问 |
| **生命周期** | 在 intake 节点首次创建，之后保持不变（作为上下文） |
| **只读性** | 后续节点读取它，但不修改它 |

```python
# 几乎所有节点都这样读取：
def some_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # 获取全局的 product_brief
    # 使用 brief 作为上下文进行决策
```

---

## product_brief 的完整流转过程

### 阶段 1️⃣：初始化（intake 节点）

```python
def intake_node(state: ProjectState) -> dict:
    brief_obj = state.get("brief")  # 用户初始输入
    
    # PM Agent 处理原始想法，生成完整的 ProjectBrief
    brief = pm.build_brief(
        raw_idea=brief_obj.idea_summary if brief_obj else "",
        history=state.get("clarification_answers", []),  # 合并用户反馈
    )
    
    # 返回更新的状态
    return {
        "brief": brief,  # ← 状态被更新
        "clarification_questions": [...],
        "current_phase": "brief_ready"
    }
```

**状态变化**：
```
输入：brief (原始用户想法)
处理：PM Agent 补全信息
输出：brief (完整的 ProjectBrief)
```

### 阶段 2️⃣：澄清循环

用户可能多次回答澄清问题：

```python
# 前端收集用户答案
state = {
    "brief": {...},  # 保持不变
    "clarification_answers": ["Answer 1", "Answer 2", ...]  # ← 新增
}

# 下一轮 intake_node 运行时
brief = pm.build_brief(
    raw_idea=brief.idea_summary,
    history=clarification_answers  # ← 整合用户反馈
)
```

**状态变化**：
```
brief 保持为基础版本
每次澄清循环后，brief 被重新生成（含新的用户答案）
```

### 阶段 3️⃣：研究阶段（research_cycle 节点）

```python
def research_cycle_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # ← 读取全局 brief
    
    # 基于 brief 生成研究任务
    task = pm.generate_research_task(brief)
    output = research_agent.run(task=task)
    
    # brief 本身不变，但研究结果被添加到状态
    return {
        "research_cycles": [...],  # ← 新增研究数据
        "current_phase": "research_in_progress"
    }
```

**状态变化**：
```
brief → 保持不变（作为上下文）
       → 触发研究任务生成
       → 研究结果存储在 research_cycles 中
```

### 阶段 4️⃣：评估阶段（research_evaluator 节点）

```python
def research_evaluator_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # ← 再次读取 brief
    research_output = _get_latest_research_output(state)
    
    # 基于 brief 和研究结果进行质量评估
    evaluation = pm.evaluate_research_quality(
        brief=brief,  # ← brief 作为评估标准
        research_output=research_output,
        iteration=iteration,
    )
    
    dvf_feedback = pm.generate_dvf_feedback(brief, research_output)
    
    return {
        "research_eval": evaluation,
        "dvf_summary": dvf_summary,
        "decisions_log": [...],  # ← 决策基于 brief
    }
```

**状态变化**：
```
brief → 用于验证研究输出是否满足项目要求
      → 触发 DVF 评分（Desirability, Viability, Feasibility）
      → 生成决策日志
```

### 阶段 5️⃣：UX 设计阶段

```python
def ux_design_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # ← brief 依然被使用
    research_insights = state.get("validated_insights", [])
    
    # UX Agent 基于 brief 和研究洞察设计界面
    ux_output = ux_agent.design(
        brief=brief,  # ← 在所有后续设计中都参考
        insights=research_insights
    )
    
    return {
        "ux_v1": ux_output,
    }
```

### 阶段 6️⃣：开发阶段

```python
def developer_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # ← 开发者也需要理解原始目标
    ux_v2 = state.get("ux_v2")
    
    # 根据 brief、UX 和研究结果生成代码
    dev_output = developer_agent.generate_code(
        brief=brief,  # ← 保证实现符合原始需求
        ux=ux_v2,
        insights=state.get("validated_insights", [])
    )
```

---

## 状态流转与传统方法的对比

### 传统方法的问题（多个文件/变量分散）

```python
# ❌ 问题方法
def traditional_pipeline():
    brief = build_brief(user_input)  # 变量 1
    research = do_research(brief)    # 变量 2
    ux = design_ux(brief, research)  # 变量 3
    dev = generate_code(brief, ux)   # 变量 4
    
    # 问题：
    # 1. 变量分散在内存中
    # 2. 难以调试中间状态
    # 3. 难以持久化和恢复
    # 4. 不支持循环和重试
```

### LangGraph 方式（统一状态存储）

```python
# ✅ LangGraph 方式
class ProjectState(TypedDict):
    brief: ProjectBrief
    research_cycles: List[Dict]
    ux_v1: UXOutput
    dev_output: DevOutput
    decisions_log: List[DecisionLog]
    # ...

# 工作流自动管理状态合并
builder = StateGraph(ProjectState)
builder.add_node("intake", intake_node)
builder.add_node("research_cycle", research_cycle_node)
# ...
graph = builder.compile()

# 执行时：
result = graph.invoke({
    "project_id": "proj_123",
    "brief": ProjectBrief(...),
})

# result 包含完整的最终状态，包括所有中间步骤
```

---

## product_brief 的三大职责

| 职责 | 用途 | 示例 |
|------|------|------|
| **1. 生成任务** | 各个 Agent 根据 brief 生成具体的工作任务 | PM 生成研究任务、UX 生成设计需求 |
| **2. 验证结果** | 评估阶段检查产出是否符合原始目标 | DVF 评分基于 brief 的要求 |
| **3. 保持一致性** | 确保所有 Agent 的工作都围绕同一个目标 | 开发时参考 brief，避免偏离方向 |

---

## 状态更新的规则

### 规则 1：返回值自动合并

```python
def node_a(state: ProjectState) -> dict:
    return {
        "field_x": new_value_x,
        "field_y": new_value_y,
    }
    # LangGraph 自动将这些字段合并到 state 中
    # 其他字段保持不变
```

### 规则 2：同一字段的多次更新

```python
# 第一个节点
def node_1(state: ProjectState) -> dict:
    return {
        "research_cycles": [cycle1]  # 创建列表
    }

# 第二个节点
def node_2(state: ProjectState) -> dict:
    existing = state.get("research_cycles", [])
    return {
        "research_cycles": [*existing, cycle2]  # 追加而非覆盖
    }
```

### 规则 3：brief 通常不被修改

```python
def any_node(state: ProjectState) -> dict:
    brief = state.get("brief")  # 读取
    # 处理...
    return {
        # 返回新数据，但通常不修改 brief
        "new_field": value,
    }
    # brief 保持原样，通过引用传递给下一个节点
```

---

## 可观测性优势

### 1. 完整的执行历史

```python
# 你的代码中已实现
execution_metrics = {
    "node_durations_seconds": {
        "intake": 0.1234,
        "research_cycle": 5.6789,
        "ux_design": 2.3456,
    }
}
```

### 2. 决策日志

```python
# 完整的决策追踪
decisions_log = [
    DecisionLog(
        phase="research",
        decision="Proceed to UX design",
        rationale="Research quality gate passed (8.5/10)."
    ),
    DecisionLog(
        phase="ux_feedback",
        decision="Revise UX based on feedback",
        rationale="Initial design score: 7.2/10, need improvements."
    ),
]
```

### 3. 易于调试和重试

```python
# 保存状态后可以重新运行
final_state = graph.invoke(initial_state)

# 恢复到某个检查点并重新运行研究
saved_state = load_checkpoint("after_research_evaluation")
result = graph.invoke(saved_state, {"resume_from": "ux_design"})
```

---

## 小结：你的 product_brief 流转路径

```
用户输入
    ↓
[intake] → brief 被创建/完善
    ↓
用户澄清（可循环）
    ↓
[clarification_router] → 决定是否继续
    ↓
[research_cycle] → 基于 brief 进行研究 (brief 保持, research_cycles 增长)
    ↓
[research_evaluator] → 根据 brief 验证研究质量 (brief 保持, eval 结果保存)
    ↓
[ux_design] → 基于 brief + 研究结果设计 UI (ux_v1 创建)
    ↓
[ux_feedback] → 评估 UX (ux_feedback 保存)
    ↓
[ux_revision] → 根据 brief 重新设计 (ux_v2 创建)
    ↓
[developer] → 基于 brief 实现代码 (dev_output 创建)
    ↓
完成：所有状态保存在 ProjectState 中
```

**关键洞察**：
- `brief` 是 **不可变的全局上下文**
- 其他字段（`research_cycles`, `ux_v1`, `dev_output` 等）是 **累积增长的结果**
- 每个节点都可以读取完整的历史信息
- 这种设计使得 **多轮迭代、错误恢复、审计跟踪** 都变得简单自然
