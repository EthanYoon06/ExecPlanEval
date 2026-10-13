# ExecPlanEval Research Protocol

## 1. Working title

**ExecPlanEval: Execution-Grounded Evaluation of Multiple Valid Plans for Tool-Using Language Agents**

中文：**ExecPlanEval：面向工具调用型语言智能体的多有效计划执行感知评价方法**

## 2. Research gap

TaskBench和WorFBench主要将候选计划与单一参考计划进行节点、边、子序列或
子图匹配。然而，同一目标可能存在多个工具选择或执行顺序不同、但均合法且
可执行的计划。结构相似度因此不一定能准确预测实际任务成功率。

## 3. Research questions

- **RQ1:** 单参考节点/边F1与实际执行成功率的相关性有多强？
- **RQ2:** 单参考指标会以多高比例误判有效替代计划？
- **RQ3:** 加入语义目标覆盖、前置条件检查和执行结果后，评价与人工判断的
  一致性是否提高？
- **RQ4:** 评价方法能否跨数据集、任务复杂度和模型规模泛化？

## 4. Testable hypotheses

- **H1:** 节点F1和边F1与执行成功率仅呈弱到中等相关。
- **H2:** 对独立步骤进行合法换序会显著降低边F1，但不会降低执行成功率。
- **H3:** ExecPlanEval与人工有效性评分及执行成功率的相关性高于结构基线。
- **H4:** 随着DAG分支数和计划长度增加，单参考指标的误判率上升。

这些是假设，不是论文结论；必须通过实验检验。

## 5. Plan representation

每个计划表示为DAG：

```json
{
  "nodes": [
    {
      "id": "n1",
      "tool": "search_weather",
      "arguments": {"city": "Beijing"},
      "goal": "obtain weather forecast"
    }
  ],
  "edges": [
    {"source": "n1", "target": "n2", "type": "data_dependency"}
  ]
}
```

依赖类型至少区分：

- 数据依赖：前一步输出是后一步输入；
- 时间依赖：业务规则要求先后顺序；
- 无依赖：允许交换或并行。

## 6. Dataset design

### Phase A: pilot

- 50个任务；
- 每个任务1个参考计划；
- 每个参考计划构造4类候选：
  1. 合法独立节点换序；
  2. 等价工具替换；
  3. 无害冗余步骤；
  4. 真实错误（缺节点、错工具、破坏依赖或参数错误）。

预计得到约250个候选计划，用于验证评价管线和标注规范。

### Phase B: full study

- TaskBench、WorFBench与一个可执行工具环境；
- 300--1000个任务；
- 按计划长度、分支宽度和工具领域分层抽样；
- 训练、验证、测试按任务划分，防止同一任务的变体泄漏。

## 7. Baselines

- Node F1；
- Edge F1；
- Graph edit similarity；
- Subgraph/subsequence matching；
- LLM-as-a-Judge（隐藏执行结果）；
- Execution success only；
- Proposed ExecPlanEval。

## 8. Proposed evaluation

候选计划的评价由四部分组成：

- **Goal coverage (G):** 子目标是否完整覆盖用户需求；
- **Dependency validity (D):** 数据与时间依赖是否满足；
- **Executability (X):** 工具存在、参数有效、前置条件满足；
- **Outcome success (O):** 执行后最终状态是否满足目标。

初始形式：

```text
ExecPlanEval = w_g G + w_d D + w_x X + w_o O - penalties
```

权重不得凭主观选择。使用验证集拟合，或报告各分量并用预注册的等权版本作为
主结果。惩罚项仅针对可验证的流程违规、不可恢复错误和不合理成本。

当前pilot实现采用等权版本，并额外报告不包含最终结果的预执行评分：

```text
PreExec = (DependencyValidity + Executability) / 2
ExecPlanEval = (GoalCoverage + DependencyValidity + Executability + Outcome) / 4
```

pilot结果仅用于验证代码与构念，不能替代真实Agent计划上的主实验。

## 9. Human annotation

每个计划由至少2名标注者独立判断：

- 有效 / 部分有效 / 无效；
- 是否可执行；
- 是否满足最终目标；
- 错误类型。

报告Cohen's kappa或Krippendorff's alpha。分歧由第三人裁决。正式研究需按
实际条件执行，不能虚构多人标注。

## 10. Metrics and statistics

- Spearman rho与Kendall tau：指标排序和人工/执行排序的相关性；
- AUROC、AUPRC、F1：识别有效计划；
- False-negative rate：有效替代计划被判错的比例；
- Bootstrap 95%置信区间；
- 配对bootstrap或置换检验比较评价器；
- 按长度、宽度、领域和模型分层分析。

## 11. Models

- 调试：Qwen3-8B；
- 主要开源模型：Qwen3-14B；
- 强开源基线：Qwen3-30B-A3B 4-bit；
- 一个已有API模型作为闭源对照。

所有模型使用固定版本和解码设置；主实验低温度，稳健性实验使用多个随机种子。

## 12. Ablations

- 移除目标覆盖；
- 移除依赖验证；
- 移除真实执行；
- 不区分数据依赖与时间依赖；
- 单参考与多参考；
- 等权评分与验证集学习权重。

## 13. Minimum evidence required before writing conclusions

- pilot管线全部可运行；
- 至少100个任务的完整主实验；
- 至少两种模型；
- 人工标注协议与一致性结果；
- 主结果、消融、错误分析和成本分析；
- 原始轨迹、配置和统计脚本可追溯。
