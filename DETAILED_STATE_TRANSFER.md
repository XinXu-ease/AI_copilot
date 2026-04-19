# 各节点信息传递详解：全局状态 vs 递进式积累

## 完整的状态字段映射

### 你的 ProjectState 包含这些字段

```python
class ProjectState(TypedDict, total=False):
    project_id: str                           # ① 项目标识
    current_phase: str                        # ② 当前阶段（所有节点都更新）
    
    brief: Optional[ProjectBrief]             # ③ 产品简报（全局上下文）
    
    clarification_questions: List[str]        # ④ 澄清问题（只在 intake 中创建）
    clarification_answers: List[str]          # ⑤ 澄清答案（用户输入）
    
    research_cycles: List[Dict[str, Any]]     # ⑥ 研究循环（递进式积累）
    research_iteration: int                   # ⑦ 研究迭代次数（递进式增长）
    research_eval: Dict[str, Any]             # ⑧ 研究评估结果（一次生成）
    risk_flag: Optional[str]                  # ⑨ 风险标记（条件写入）
    
    validated_insights: List[str]             # ⑩ 验证的洞察（由 research_eval 提取）
    opportunities: List[str]                  # ⑪ 机会列表（由 research_eval 提取）
    dvf_summary: List[str]                    # ⑫ DVF 评分摘要（一次生成）
    
    ux_v1: Optional[UXOutput]                 # ⑬ UX 初版（一次生成）
    ux_feedback: List[FeedbackBundle]         # ⑭ UX 反馈（一次生成）
    ux_v2: Optional[UXOutput]                 # ⑮ UX 修订版（一次生成）
    
    dev_output: Optional[DevOutput]           # ⑯ 开发输出（一次生成）
    
    decisions_log: List[DecisionLog]          # ⑰ 决策日志（递进式积累）
    next_action: Optional[str]                # ⑱ 下一步行动（最后更新）
    execution_metrics: Dict[str, Any]         # ⑲ 执行指标（递进式积累）
```

---

## 节点的读写分析矩阵

### 1. intake_node
```
【读】brief, clarification_answers
【写】brief, clarification_questions, current_phase, execution_metrics

特点：首次创建 brief（基于用户初始输入 + 澄清答案）
```

### 2. clarification_router（路由决策，不修改状态）
```
【读】clarification_questions
【写】无（仅返回路由路径）

特点：条件判断函数，决定是否需要继续澄清
```

### 3. research_cycle_node
```
【读】brief, research_cycles, research_iteration
【写】research_cycles, research_iteration, current_phase, execution_metrics

特点：
- 每次循环都会追加新的研究周期（递进式增长）
- research_cycles 是一个列表，每个元素代表一次迭代
- 可能多次运行（循环）
```

### 4. research_evaluator_node
```
【读】brief, research_cycles (提取最新输出), research_iteration, decisions_log
【写】research_eval, dvf_summary, validated_insights, opportunities, 
       decisions_log, current_phase, risk_flag, execution_metrics

特点：
- 基于 brief 验证研究质量
- 从 research_cycles 中提取最新的研究输出
- 生成新的评估结果和洞察
- 追加新的决策到 decisions_log
```

### 5. research_evaluator_router（路由决策）
```
【读】research_eval
【写】无

特点：根据研究评估结果决定是否继续迭代或进入 UX 阶段
```

### 6. ux_design_node
```
【读】brief, dvf_summary, research_cycles (提取最新输出)
【写】ux_v1, current_phase, execution_metrics

特点：
- 基于 brief + DVF + 研究结果设计 UX
- 首次生成 ux_v1
```

### 7. ux_feedback_node
```
【读】ux_v1, brief, research_cycles (提取最新输出)
【写】ux_feedback, current_phase, execution_metrics

特点：
- 基于初版 UX 生成反馈
- ux_feedback 是一个列表，可能有多个反馈源
```

### 8. ux_revision_node
```
【读】brief, dvf_summary, research_cycles (提取最新输出)
【写】ux_v2, current_phase, execution_metrics

特点：
- 基于反馈重新设计 UX
- 生成修订版 ux_v2
```

### 9. developer_node
```
【读】ux_v2, ux_v1, brief, decisions_log
【写】dev_output, decisions_log, current_phase, next_action, execution_metrics

特点：
- 基于最终 UX 版本生成代码
- 同时追加最终决策
```

---

## 信息传递的三种模式

### 模式 1️⃣：全局不变的上下文（Brief）

```
brief: ProjectBrief
  ↓ (created in intake)
  ↓ (read by all subsequent nodes)
  ↓ (never modified)
  ↓
[research] [ux_design] [ux_revision] [developer]
   ↓          ↓           ↓            ↓
都基于同一个 brief 进行工作
```

**节点读取情况**：
- intake: 创建
- research_cycle: 读取（生成研究任务）
- research_evaluator: 读取（验证研究质量）
- ux_design: 读取（生成设计需求）
- ux_revision: 读取（参考原始目标修订）
- developer: 读取（确保实现符合目标）

---

### 模式 2️⃣：递进式积累（列表追加）

#### 2a. research_cycles（可能多次增长）

```python
research_cycles: [
    {
        "iteration": 1,
        "output": {...}
    },
    # ↓ 如果评估不过关，继续循环 ↓
    {
        "iteration": 2,
        "output": {...}
    },
    # ↓ 最终通过或达到上限 ↓
]
```

**节点操作**：
```python
# research_cycle_node
existing_cycles = list(state.get("research_cycles", []) or [])
iteration = len(existing_cycles) + 1  # 计算下一个迭代号
# ... 执行研究 ...
return {
    "research_cycles": [*existing_cycles, cycle_item],  # 追加
    "research_iteration": iteration,
}
```

#### 2b. decisions_log（持续追加）

```python
decisions_log: [
    DecisionLog(phase="research", decision="Proceed to UX", ...),
    DecisionLog(phase="ux_feedback", decision="Revise UX", ...),
    DecisionLog(phase="development", decision="Generate code", ...),
]
```

**节点操作**：
```python
# research_evaluator_node
existing_decisions = state.get("decisions_log", [])
decisions = list(existing_decisions)  # 复制现有决策
decisions.append(DecisionLog(...))    # 追加新决策
return {"decisions_log": decisions}
```

#### 2c. execution_metrics（递进式记录）

```python
execution_metrics: {
    "node_durations_seconds": {
        "intake": 0.1234,
        "research_cycle": 5.6789,        # 第一次
        "research_cycle": 3.2109,        # 第二次（累加）
        "research_evaluator": 2.3456,
        "ux_design": 1.2345,
        ...
    }
}
```

---

### 模式 3️⃣：单次生成的结果（不会重复生成）

#### 3a. 研究阶段输出

```python
research_eval: {
    "passes_gate": True,
    "overall_score": 8.5,
    "next_action": "proceed_to_ux",
    ...
}

dvf_summary: [
    "Desirability (Score 9/10): ...",
    "Viability (Score 8/10): ...",
    "Feasibility (Score 8/10): ...",
    "Overall: ..."
]

validated_insights: ["Insight 1", "Insight 2", ...]
opportunities: ["Opportunity 1", "Opportunity 2", ...]
```

**何时生成**：research_evaluator_node（仅一次）

#### 3b. UX 设计输出

```python
ux_v1: UXOutput(...)  # 初版
ux_v2: UXOutput(...)  # 修订版

ux_feedback: [
    FeedbackBundle(
        source_agent="pm",
        comments=[...],
        cross_team_feedback={...}
    ),
]
```

**何时生成**：
- ux_v1: ux_design_node
- ux_feedback: ux_feedback_node
- ux_v2: ux_revision_node

#### 3c. 开发输出

```python
dev_output: DevOutput(...)
```

**何时生成**：developer_node（仅一次）

---

## 完整的信息流动可视化

```
┌─────────────────────────────────────────────────────────────────┐
│                    初始状态（用户提供）                           │
│  project_id, brief (原始想法)                                  │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
        ┌──────────────────────────────────┘
        │
        ▼
    ┌────────────────────────────────┐
    │  intake_node                   │
    │  ─────────────────────         │
    │  【读】brief, clarification_   │
    │       answers                  │
    │  【写】                         │
    │    • brief ← 更新              │
    │    • clarification_questions   │
    │    • current_phase             │
    │    • execution_metrics         │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  clarification_router          │
    │  ─────────────────────         │
    │  需要澄清？                     │
    │  ├─ YES → 返回前端等答案        │
    │  └─ NO  → 进入研究阶段          │
    └────────────────────┬───────────┘
                         │
                         ▼ (可循环)
    ┌────────────────────────────────┐
    │  research_cycle_node           │
    │  ─────────────────────         │
    │  【读】brief, research_cycles  │
    │  【写】                         │
    │    • research_cycles ← 追加    │
    │    • research_iteration        │
    │    • execution_metrics ← 追加  │
    │                                │
    │  (循环执行，每次追加一个周期)   │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  research_evaluator_node       │
    │  ─────────────────────         │
    │  【读】brief, research_cycles, │
    │       research_iteration,      │
    │       decisions_log            │
    │  【写】                         │
    │    • research_eval             │
    │    • dvf_summary               │
    │    • validated_insights        │
    │    • opportunities             │
    │    • decisions_log ← 追加      │
    │    • risk_flag (条件)          │
    │    • execution_metrics ← 追加  │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  research_evaluator_router     │
    │  ─────────────────────         │
    │  评估结果如何？                 │
    │  ├─ 继续迭代 → 回到 research_ │
    │  │           cycle_node        │
    │  └─ 通过 → 进入 UX 设计        │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  ux_design_node                │
    │  ─────────────────────         │
    │  【读】brief, dvf_summary,     │
    │       research_cycles          │
    │  【写】                         │
    │    • ux_v1                     │
    │    • current_phase             │
    │    • execution_metrics ← 追加  │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  ux_feedback_node              │
    │  ─────────────────────         │
    │  【读】ux_v1, brief,           │
    │       research_cycles          │
    │  【写】                         │
    │    • ux_feedback               │
    │    • current_phase             │
    │    • execution_metrics ← 追加  │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  ux_revision_node              │
    │  ─────────────────────         │
    │  【读】brief, dvf_summary,     │
    │       research_cycles          │
    │  【写】                         │
    │    • ux_v2                     │
    │    • current_phase             │
    │    • execution_metrics ← 追加  │
    └────────────────────┬───────────┘
                         │
                         ▼
    ┌────────────────────────────────┐
    │  developer_node                │
    │  ─────────────────────         │
    │  【读】ux_v2, ux_v1, brief,    │
    │       decisions_log            │
    │  【写】                         │
    │    • dev_output                │
    │    • decisions_log ← 追加      │
    │    • current_phase             │
    │    • next_action               │
    │    • execution_metrics ← 追加  │
    └────────────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  最终状态（完整信息）   │
            │  所有字段都被保留      │
            └────────────────────────┘
```

---

## 关键问题：是否每个节点都读取所有字段？

### ❌ 不是！

每个节点只读取它需要的字段：

| 节点 | 读取的关键字段 | 用途 |
|------|-------------|------|
| **intake** | brief | 补全信息 |
| **clarification_router** | clarification_questions | 决定是否继续 |
| **research_cycle** | brief | 生成研究任务 |
| **research_evaluator** | brief, research_cycles | 验证研究质量 |
| **research_evaluator_router** | research_eval | 决定下一步 |
| **ux_design** | brief, dvf_summary, research_cycles | 设计 UX |
| **ux_feedback** | ux_v1, brief, research_cycles | 生成反馈 |
| **ux_revision** | brief, dvf_summary, research_cycles | 修订 UX |
| **developer** | ux_v2, ux_v1, brief | 生成代码 |

### ✅ 但是所有未被修改的字段都自动传递给下一个节点

这是 LangGraph 的关键特性：

```python
def any_node(state: ProjectState) -> dict:
    # 读取需要的字段
    brief = state.get("brief")
    research_cycles = state.get("research_cycles")
    
    # 处理逻辑...
    
    # 只返回更新的字段
    return {
        "new_field": new_value,
        "another_field": another_value,
    }
    # 未返回的字段（brief, research_cycles 等）自动传递
```

---

## 字段的三种生命周期

### 生命周期类型 A：全局不变上下文
```
brief
  │
  ├─ 【创建】intake_node (第一次) 
  ├─ 【读取】research_cycle_node
  ├─ 【读取】research_evaluator_node
  ├─ 【读取】ux_design_node
  ├─ 【读取】ux_revision_node
  └─ 【读取】developer_node

特点：一次创建，多次读取，永不修改
价值：作为所有决策的参考基准
```

### 生命周期类型 B：递进式积累列表
```
research_cycles, decisions_log, execution_metrics
  │
  ├─ 【初始化】第一个节点
  ├─ 【追加】每个贡献节点
  └─ 【查询】评估/决策节点

示例（research_cycles）：
  iteration 1: research_cycle_node 执行 → 追加
  iteration 2: research_cycle_node 再次执行 → 追加
  查询: research_evaluator_node 获取最新 → 追加评估结果

特点：只追加不删除，形成完整历史
价值：支持循环迭代、完整审计日志、错误恢复
```

### 生命周期类型 C：单次生成的输出
```
research_eval, ux_v1, ux_v2, dev_output
  │
  ├─ 【生成】特定节点（仅一次）
  ├─ 【读取】后续节点（作为输入）
  └─ 【不修改】保持原样

示例：
  research_eval ← 仅由 research_evaluator_node 生成
  ux_v1 ← 仅由 ux_design_node 生成
  ux_v2 ← 仅由 ux_revision_node 生成

特点：里程碑式的检查点
价值：清晰的版本管理、便于对比
```

---

## 实际数据流示例

### 假设流程：需要两轮研究迭代

```
【初始状态】
{
  "project_id": "proj_001",
  "brief": ProjectBrief(title="AI Chat App", ...)
}

        ↓ [intake_node 执行]

【状态 1】
{
  "project_id": "proj_001",
  "brief": ProjectBrief(title="AI Chat App", ...),  # 补全信息
  "clarification_questions": ["Q1", "Q2", ...],
  "current_phase": "brief_ready",
  "execution_metrics": {"node_durations_seconds": {"intake": 0.1234}}
}

        ↓ [用户回答澄清问题，状态接收 clarification_answers]
        
【状态 2】
{
  "project_id": "proj_001",
  "brief": ProjectBrief(title="AI Chat App", ...),
  "clarification_questions": [],  # 清空（或在下一次 intake 中处理）
  "clarification_answers": ["A1", "A2", ...],  # 新增
  "current_phase": "brief_ready",
  "execution_metrics": {...}
}

        ↓ [research_cycle_node - 第 1 次执行]

【状态 3】
{
  "project_id": "proj_001",
  "brief": ProjectBrief(...),
  "clarification_answers": ["A1", "A2", ...],
  "research_cycles": [  # 第一个循环
    {
      "iteration": 1,
      "output": {
        "insights": [...],
        "opportunities": [...],
        "market_analysis": {...}
      }
    }
  ],
  "research_iteration": 1,
  "current_phase": "research_in_progress",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 5.6789
    }
  }
}

        ↓ [research_evaluator_node 执行]

【状态 4】
{
  ...(保持所有前面的字段)...
  "research_eval": {
    "passes_gate": False,  # 不通过，需要迭代
    "overall_score": 6.2,
    "next_action": "iterate_research",
    ...
  },
  "dvf_summary": ["Desirability (Score 6/10): ...", ...],
  "validated_insights": ["Insight A", "Insight B", ...],
  "opportunities": ["Opp 1", ...],
  "decisions_log": [
    DecisionLog(phase="research", decision="Iterate research", ...)
  ],
  "risk_flag": "research_quality_below_threshold",
  "current_phase": "research_evaluated",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 5.6789,
      "research_evaluator": 2.3456
    }
  }
}

        ↓ [research_evaluator_router 返回 "iterate_research"]
        ↓ [回到 research_cycle_node - 第 2 次执行]

【状态 5】
{
  ...(保持所有前面的字段)...
  "research_cycles": [
    {
      "iteration": 1,
      "output": {...}  # 第一次的结果保留
    },
    {
      "iteration": 2,  # 第二次迭代
      "output": {...}  # 新的研究输出
    }
  ],
  "research_iteration": 2,
  "current_phase": "research_in_progress",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 5.6789,  # 第一次的时间保留
      "research_cycle": 4.1234,  # 第二次的时间累加（或覆盖？看实现）
      "research_evaluator": 2.3456
    }
  }
}

        ↓ [research_evaluator_node 再次执行，基于最新的研究输出]

【状态 6】
{
  ...(保持所有字段)...
  "research_eval": {  # 更新
    "passes_gate": True,  # 这次通过了
    "overall_score": 8.1,
    "next_action": "proceed_to_ux",
    ...
  },
  "dvf_summary": ["Desirability (Score 8/10): ...", ...],  # 更新
  "validated_insights": ["Insight A", "Insight B", "Insight C"],  # 更新
  "opportunities": ["Opp 1", "Opp 2"],  # 更新
  "decisions_log": [
    DecisionLog(phase="research", decision="Iterate research", ...),
    DecisionLog(phase="research", decision="Proceed to UX design", ...)  # 新决策
  ],
  "risk_flag": None,  # 清除
  "current_phase": "research_evaluated",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 9.8023,  # 累加 5.6789 + 4.1234
      "research_evaluator": 4.7890  # 2.3456 + 2.4434
    }
  }
}

        ↓ [research_evaluator_router 返回 "proceed_to_ux"]
        ↓ [进入 ux_design_node]

【状态 7】
{
  ...(所有前面的字段保留)...
  "ux_v1": UXOutput(...),  # 新增
  "current_phase": "ux_v1_done",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 9.8023,
      "research_evaluator": 4.7890,
      "ux_design": 3.2109  # 新增
    }
  }
}

        ↓ [继续 ux_feedback_node, ux_revision_node, developer_node...]

【最终状态】
{
  "project_id": "proj_001",
  "brief": ProjectBrief(...),
  "clarification_answers": ["A1", "A2", ...],
  "research_cycles": [
    {"iteration": 1, "output": {...}},
    {"iteration": 2, "output": {...}}
  ],
  "research_iteration": 2,
  "research_eval": {...},
  "dvf_summary": [...],
  "validated_insights": [...],
  "opportunities": [...],
  "risk_flag": None,
  "ux_v1": UXOutput(...),
  "ux_feedback": [FeedbackBundle(...)],
  "ux_v2": UXOutput(...),
  "dev_output": DevOutput(...),
  "decisions_log": [
    DecisionLog(phase="research", decision="Iterate research", ...),
    DecisionLog(phase="research", decision="Proceed to UX design", ...),
    DecisionLog(phase="development", decision="Generate code", ...),
  ],
  "next_action": "Review final report",
  "current_phase": "completed",
  "execution_metrics": {
    "node_durations_seconds": {
      "intake": 0.1234,
      "research_cycle": 9.8023,
      "research_evaluator": 4.7890,
      "ux_design": 3.2109,
      "ux_feedback": 1.8765,
      "ux_revision": 2.4321,
      "developer": 4.5678
    }
  }
}
```

---

## 总结：信息传递的三个关键点

| 问题 | 答案 |
|------|------|
| **都是全局的吗？** | 部分是。`brief` 是全局不变的上下文；`research_cycles`, `decisions_log` 等是全局递进式积累的；`ux_v1`, `dev_output` 等是检查点式的单次生成。|
| **每个节点都读取吗？** | 不。每个节点只读取它需要的字段。但所有未修改的字段自动传递到下一个节点。|
| **状态如何传递？** | 通过 LangGraph 的自动合并机制。节点返回的字典与原状态合并，未返回的字段保持不变，自动传入下一个节点。|

---

## 文件位置参考

- 状态定义：`src/schemas/state.py`
- 节点实现：`src/workflows/nodes.py`
- 工作流配置：`src/workflows/graph.py`
