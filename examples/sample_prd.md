# Agent Inbox Automation PRD

## 背景

团队经常把大型需求一次性丢给 Codex 或 Claude Code，导致 agent 一次修改太多文件，很难 review。

## 任务：读取 Markdown 和 issue

- 实现 Markdown 标题、checklist、普通 bullet 的解析。
- 读取 `src/inbox/parser.py` 与 `tests/test_parser.py`。
- 验收：空输入应返回明确错误，非 UTF-8 文件应给出退出码。

## 任务：生成 agent 工作包

- 基于解析结果生成目标、范围、输入文件、验收标准。
- 依赖：读取 Markdown 和 issue。
- 风险：如果需求涉及 auth、database migration、payment，需要高风险提示。

## 任务：导出结果

- 支持 Markdown、JSON、Graphviz DOT。
- 更新 `src/inbox/exporters.py`、`tests/test_exporters.py`。
- 验收：DOT 中每个任务必须有节点，依赖必须有边。

## 集成

- 添加 GitHub Actions CI。
- 建议验证命令：python -m unittest

