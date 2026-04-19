# DVF Summary 的时间点分析与重构建议

## 问题 1：dvf_summary 在哪个阶段生成？

### 当前流程

```
【research_cycle_node 执行】
    ↓
research_cycles 列表追加 { iteration: N, output: {...} }
    ↓
【research_evaluator_node 执行】（基于最新的 research_output）
    ├─ 调用 pm.evaluate_research_quality(brief, research_output, iteration)
    ├─ 调用 pm.generate_dvf_feedback(brief, research_output)
    ├─ 生成 dvf_summary
    └─ 生成 research_eval
```

### 时间同步情况

```python
def research_evaluator_node(state: ProjectState) -> dict:
    brief = state.get("brief")
    research_output = _get_latest_research_output(state)  # ← 获取最后一个 research_cycle 的输出
    iteration = int(state.get("research_iteration", 1) or 1)  # ← 当前迭代号
    
    # 基于最新的 research_output 生成评估
    evaluation = pm.evaluate_research_quality(
        brief=brief,
        research_output=research_output,
        iteration=iteration,
    )
    
    dvf_feedback = pm.generate_dvf_feedback(brief, research_output)  # ← 同一个 research_output
```

**答案**：✅ **是的，dvf_summary 是在最后一个 research_cycle 之后立即生成的**

```
research_cycle_node (iteration N)
         ↓
    [状态] research_cycles[N] 创建
         ↓
research_evaluator_node (评估 research_cycles[N])
         ├─ dvf_feedback = pm.generate_dvf_feedback(brief, research_cycles[N].output)
         ├─ dvf_summary 生成
         ├─ research_eval 生成
         └─ 决定是否再循环
```

---

## 问题 2：dvf_summary 是评测方式，不是独立的东西

### ✅ 你的见解完全正确！

当前架构的问题：

```python
# 现在的设计：DVF 作为独立字段
class ProjectState(TypedDict):
    research_eval: Dict[str, Any]    # 研究质量评分
    dvf_summary: List[str]            # DVF 评分摘要（独立）
    validated_insights: List[str]
    opportunities: List[str]
    ux_feedback: List[FeedbackBundle] # UX 反馈

# 问题：
# 1. dvf_summary 是格式化字符串，不是结构化数据
# 2. 它只在 research_evaluator 生成一次，后续不更新
# 3. ux_design 读取它，但它应该有自己的 DVF 评估
# 4. 状态字段数量过多
```

### 为什么要重构？

| 当前问题 | 建议方案 |
|---------|--------|
| DVF 评分分散在 dvf_summary (格式化字符串) 中 | 放入 `research_eval` 作为结构化数据 |
| ux_feedback 中没有 DVF 评分，只有定性反馈 | 为 ux_feedback 增加 DVF 评分 |
| 状态字段混乱：dvf_summary, validated_insights, opportunities 都来自同一个地方 | 统一管理：DVF 评分、洞察、机会都归入各自的 eval 对象 |

---

## 建议的重构方案

### 方案 A：将 DVF 集成到 research_eval

#### 当前结构（问题）
```python
# research_evaluator_node 返回
{
    "research_eval": {
        "passes_gate": True,
        "overall_score": 8.5,
        "next_action": "proceed_to_ux",
        # ← 缺少 DVF 评分
    },
    "dvf_summary": [          # ← 独立、无结构
        "Desirability (Score 9/10): ...",
        "Viability (Score 8/10): ...",
        ...
    ],
    "validated_insights": [...],   # ← 冗余
    "opportunities": [...],        # ← 冗余
}
```

#### 建议的结构
```python
# research_evaluator_node 返回
{
    "research_eval": {
        # 质量评分
        "passes_gate": True,
        "overall_score": 8.5,
        "next_action": "proceed_to_ux",
        
        # 🆕 DVF 评分（集成）
        "dvf": {
            "desirability": {
                "score": 9,
                "evidence": "Strong user demand signals from market research..."
            },
            "viability": {
                "score": 8,
                "evidence": "Sustainable business model with clear revenue streams..."
            },
            "feasibility": {
                "score": 8,
                "evidence": "Tech stack is proven, team has relevant experience..."
            },
            "overall_assessment": "Strong project with balanced DVF scores"
        },
        
        # 🆕 洞察与机会（结构化）
        "validated_insights": [
            {
                "statement": "Users prioritize real-time collaboration",
                "confidence": "high",
                "evidence": "85% of interviews mentioned this need"
            },
            ...
        ],
        "opportunities": [
            {
                "title": "AI-powered suggestions",
                "desirability": 8,
                "viability": 7,
                "feasibility": 6,
                "rationale": "..."
            },
            ...
        ],
    }
}

# 状态变化
{
    "research_eval": research_eval,  # ← 一个对象包含所有
    # validated_insights 移除（在 research_eval 内）
    # opportunities 移除（在 research_eval 内）
    # dvf_summary 移除（在 research_eval.dvf 内）
}
```

---

### 方案 B：为 ux_feedback 也添加 DVF 评估

#### 当前的 ux_feedback（缺少 DVF）
```python
ux_feedback = [
    FeedbackBundle(
        source_agent="pm",
        comments=[...],  # 定性反馈
        cross_team_feedback={...}
    ),
]
# ← 只有定性反馈，没有定量的 DVF 评分
```

#### 建议的 ux_feedback（添加 DVF）
```python
# 在 ux_feedback_node 中
dvf_feedback_ux = pm.generate_dvf_feedback_for_ux(
    brief=brief,
    research_output=research_output,
    ux_output=ux_output
)

ux_feedback = [
    FeedbackBundle(
        source_agent="pm",
        comments=[...],
        cross_team_feedback={...},
        # 🆕 DVF 评分
        dvf_scores={
            "desirability": 7,  # UX 是否符合用户需求
            "viability": 8,     # UX 是否支持商业模式
            "feasibility": 6,   # UX 实现的难度
        },
        dvf_rationale="..."
    ),
]
```

---

## 完整的重构方案（推荐）

### 1. 更新 StateSchema

```python
# src/schemas/state.py

class DVFScores(BaseModel):
    desirability: int  # 1-10
    viability: int     # 1-10
    feasibility: int   # 1-10
    overall_assessment: str
    evidence: Dict[str, str]  # 每个维度的证据

class ValidatedInsight(BaseModel):
    statement: str
    confidence: str  # "high", "medium", "low"
    evidence: str
    dvf_dimension: str  # 主要关联到哪个 DVF 维度

class Opportunity(BaseModel):
    title: str
    description: str
    dvf_scores: DVFScores
    priority: int  # 1-5
    risks: List[str]

class ResearchEvaluation(BaseModel):
    passes_gate: bool
    overall_score: float
    next_action: str
    
    # DVF 评分（结构化）
    dvf: DVFScores
    
    # 洞察与机会
    validated_insights: List[ValidatedInsight]
    opportunities: List[Opportunity]
    
    # 其他
    risks_identified: List[str]
    assumptions_needing_validation: List[str]

class FeedbackBundle(BaseModel):
    source_agent: str
    comments: List[str]
    cross_team_feedback: Optional[Dict[str, List[str]]]
    
    # 🆕 DVF 评分
    dvf_scores: Optional[Dict[str, int]] = None  # {"desirability": 7, ...}
    dvf_rationale: Optional[str] = None

class ProjectState(TypedDict, total=False):
    brief: Optional[ProjectBrief]
    
    research_cycles: List[Dict[str, Any]]
    research_eval: Optional[ResearchEvaluation]  # ← 包含 DVF
    
    ux_v1: Optional[UXOutput]
    ux_feedback: List[FeedbackBundle]  # ← 现在包含 DVF
    ux_v2: Optional[UXOutput]
    
    dev_output: Optional[DevOutput]
    
    decisions_log: List[DecisionLog]
    # ❌ 移除：dvf_summary, validated_insights, opportunities
```

### 2. 重构 research_evaluator_node

```python
def research_evaluator_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_output = _get_latest_research_output(state)
    iteration = int(state.get("research_iteration", 1) or 1)

    # 1. 质量评分
    evaluation_scores = pm.evaluate_research_quality(
        brief=brief,
        research_output=research_output,
        iteration=iteration,
    )

    # 2. DVF 评分（结构化）
    dvf_feedback = pm.generate_dvf_feedback(brief, research_output)
    dvf_scores = DVFScores(
        desirability=dvf_feedback['desirability']['score'],
        viability=dvf_feedback['viability']['score'],
        feasibility=dvf_feedback['feasibility']['score'],
        overall_assessment=dvf_feedback['overall_assessment'],
        evidence={
            "desirability": dvf_feedback['desirability']['evidence'],
            "viability": dvf_feedback['viability']['evidence'],
            "feasibility": dvf_feedback['feasibility']['evidence'],
        }
    )

    # 3. 提取洞察（结构化）
    insights_raw = research_output.get("insights", [])
    validated_insights = [
        ValidatedInsight(
            statement=item.get("statement", ""),
            confidence=item.get("confidence", "medium"),
            evidence=item.get("evidence", ""),
            dvf_dimension=item.get("dvf_dimension", "desirability")
        )
        for item in insights_raw if isinstance(item, dict)
    ]

    # 4. 提取机会（结构化）
    opportunities_raw = research_output.get("opportunities", [])
    opportunities = [
        Opportunity(
            title=item.get("title", ""),
            description=item.get("description", ""),
            dvf_scores=DVFScores(
                desirability=item.get("dvf_scores", {}).get("desirability", 7),
                viability=item.get("dvf_scores", {}).get("viability", 6),
                feasibility=item.get("dvf_scores", {}).get("feasibility", 6),
                overall_assessment="",
                evidence={}
            ),
            priority=item.get("priority", 3),
            risks=item.get("risks", [])
        )
        for item in opportunities_raw if isinstance(item, dict)
    ]

    # 5. 构建完整的 ResearchEvaluation
    research_eval = ResearchEvaluation(
        passes_gate=evaluation_scores.get("passes_gate", False),
        overall_score=evaluation_scores.get("overall_score", 0),
        next_action=evaluation_scores.get("next_action", "iterate_research"),
        dvf=dvf_scores,
        validated_insights=validated_insights,
        opportunities=opportunities,
        risks_identified=evaluation_scores.get("risks", []),
        assumptions_needing_validation=evaluation_scores.get("assumptions", [])
    )

    # 6. 构建决策
    existing_decisions = state.get("decisions_log", [])
    decisions = list(existing_decisions)
    
    if research_eval.passes_gate:
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed to UX design",
                rationale=f"Research quality gate passed ({research_eval.overall_score}/10). DVF scores: D{research_eval.dvf.desirability}/V{research_eval.dvf.viability}/F{research_eval.dvf.feasibility}.",
            )
        )
    elif research_eval.next_action == "force_proceed_with_risk":
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed with risk",
                rationale=f"Reached max research rounds ({iteration}). DVF assessment: D{research_eval.dvf.desirability}/V{research_eval.dvf.viability}/F{research_eval.dvf.feasibility}.",
            )
        )

    payload = {
        "research_eval": research_eval.model_dump(),  # ✅ 一个对象包含所有
        "decisions_log": decisions,
        "current_phase": "research_evaluated",
    }

    if research_eval.next_action == "force_proceed_with_risk":
        payload["risk_flag"] = "research_quality_below_threshold"

    return _with_node_timing(state, "research_evaluator", payload, started_at)
```

### 3. 更新 ux_design_node

```python
def ux_design_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_eval = state.get("research_eval", {})
    research_output = _get_latest_research_output(state)
    
    # ✅ 从结构化数据中提取 DVF，而不是 dvf_summary
    dvf_context = {
        "scores": research_eval.get("dvf", {}),
        "insights": research_eval.get("validated_insights", []),
        "opportunities": research_eval.get("opportunities", []),
    }
    
    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        dvf_context=dvf_context,  # ✅ 传递结构化 DVF 数据
    )
    return _with_node_timing(
        state,
        "ux_design",
        {"ux_v1": ux, "current_phase": "ux_v1_done"},
        started_at,
    )
```

### 4. 更新 ux_feedback_node

```python
def ux_feedback_node(state: ProjectState) -> dict:
    """Generate structured feedback on UX design with DVF evaluation."""
    started_at = time.perf_counter()
    ux_v1 = state.get("ux_v1")
    brief = state.get("brief")
    research_eval = state.get("research_eval", {})
    
    ux_output = ux_v1.model_dump() if ux_v1 else {}
    
    feedback_dict = pm.generate_ux_feedback(
        brief=brief,
        research_eval=research_eval,  # ✅ 传递完整的研究评估
        ux_output=ux_output
    )
    
    # ✅ UX 反馈现在包含 DVF 评分
    feedback = [
        FeedbackBundle(
            source_agent="pm",
            comments=feedback_dict.get("actionable_revisions", []) + 
                    feedback_dict.get("feature_priority_feedback", []),
            cross_team_feedback={
                "research": feedback_dict.get("cross_team_feedback", {}).get("research_comments", []),
                "developer": feedback_dict.get("cross_team_feedback", {}).get("developer_comments", [])
            },
            # ✅ DVF 评分
            dvf_scores={
                "desirability": feedback_dict.get("dvf_scores", {}).get("desirability", 7),
                "viability": feedback_dict.get("dvf_scores", {}).get("viability", 7),
                "feasibility": feedback_dict.get("dvf_scores", {}).get("feasibility", 7),
            },
            dvf_rationale=feedback_dict.get("dvf_rationale", "")
        ),
    ]
    return _with_node_timing(
        state,
        "ux_feedback",
        {"ux_feedback": feedback, "current_phase": "ux_feedback_done"},
        started_at,
    )
```

---

## 重构对比图

### 当前设计（问题）
```
ProjectState:
├─ research_eval { passes_gate, overall_score, next_action }
├─ dvf_summary [ "Desirability...", "Viability...", ... ]  ❌ 格式化字符串
├─ validated_insights [ "Insight 1", ... ]                  ❌ 冗余
├─ opportunities [ "Opp 1", ... ]                           ❌ 冗余
└─ ux_feedback [ FeedbackBundle(...) ]                      ❌ 无 DVF 评分
```

### 建议的设计（优化）
```
ProjectState:
├─ research_eval {
│  ├─ passes_gate, overall_score, next_action
│  ├─ dvf { desirability, viability, feasibility, evidence }  ✅ 结构化
│  ├─ validated_insights [{ statement, confidence, evidence }] ✅ 结构化
│  └─ opportunities [{ title, dvf_scores, priority, risks }]   ✅ 结构化
├─ ux_feedback [
│  ├─ FeedbackBundle { comments, cross_team_feedback }
│  └─ dvf_scores { desirability, viability, feasibility }     ✅ 新增
│  └─ dvf_rationale "..."                                      ✅ 新增
└─ (移除 dvf_summary)
```

---

## 优势总结

| 方面 | 当前 | 重构后 |
|------|------|--------|
| **数据结构** | 混杂（格式化字符串 + 列表） | 统一（Pydantic 模型） |
| **DVF 评分位置** | research_eval（缺少）+ 独立 dvf_summary | research_eval 内 + ux_feedback 内 |
| **机器可读性** | 低（需要解析字符串） | 高（结构化数据） |
| **状态字段数** | 多（19 个） | 少（15 个） |
| **数据冗余** | 有（insights, opportunities 重复） | 无 |
| **向下游传递** | 格式化字符串 | 结构化对象 |
| **UX Agent 需要的数据** | 需要提取并重新组织 | 直接可用 |

---

## 实施建议

### 第 1 步：定义新的 Pydantic 模型
更新 `src/schemas/` 中的相关文件（brief.py, research.py, ux.py等）

### 第 2 步：更新 nodes.py
- 重构 `research_evaluator_node`
- 更新 `ux_design_node`、`ux_feedback_node`、`developer_node`

### 第 3 步：更新提示词
修改 PM Agent 的提示词，让其输出结构化的 DVF 评分而非格式化字符串

### 第 4 步：测试验证
确保所有 Agent 能正确消费新的数据结构

---

## 总结：你的见解很敏锐！

你指出的核心问题：
- ✅ DVF 是**评测方式**，不是独立数据
- ✅ 不应该作为单独的状态字段
- ✅ 应该集成到 evaluation 对象内
- ✅ ux_feedback 也需要 DVF 评分

这样的设计会让系统更清晰、更易维护、更易扩展。
