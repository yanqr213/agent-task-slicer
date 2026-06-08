# agent-task-slicer

中文 | [English](#english)

`agent-task-slicer` 是一个零运行时外部依赖的 Python 开发者工具，用来把 PRD、issue、需求 Markdown、任务清单和代码路径清单切成适合 Codex、Claude Code、自研 Agent 执行的小型工作包。

它会为每个工作包生成：

- 目标和范围
- 输入文件或路径提示
- 验收标准
- 风险原因和 1-5 分风险评分
- 建议验证命令
- 依赖关系
- Markdown、JSON、Graphviz DOT 输出

项目定位不是“替你做项目管理”的 SaaS，而是一个可以放进仓库、CI、agent 编排脚本里的轻量切片器。

## 适用场景

- 把大型产品需求拆成多个 agent 可独立执行的任务。
- 从 GitHub issue、PRD、开发计划、checklist 中提取工作包。
- 在提交给 Codex/Claude Code 前生成更小、更清晰的任务上下文。
- 为多人 review 或 agent 并行执行生成 JSON。
- 为任务依赖生成 DOT 图，接入 Graphviz 或文档站。

## 安装

从源码安装：

```bash
python -m pip install -e .
```

运行测试：

```bash
python -m unittest
```

要求 Python 3.9+。运行时只使用 Python 标准库。

## CLI

读取 Markdown 并输出 Markdown：

```bash
agent-task-slicer examples/sample_prd.md
```

输出 JSON：

```bash
agent-task-slicer examples/sample_prd.md --format json
```

输出 Graphviz DOT：

```bash
agent-task-slicer examples/sample_prd.md --format dot -o outputs/tasks.dot
```

从 stdin 读取：

```bash
cat examples/sample_prd.md | agent-task-slicer - --format markdown
```

限制任务数量和 ID 前缀：

```bash
agent-task-slicer examples/sample_prd.md --max-tasks 10 --prefix AG
```

使用配置文件：

```bash
agent-task-slicer examples/sample_prd.md -c examples/config.json --format json
```

### 退出码

- `0`：成功。
- `2`：输入错误，例如文件不存在、空输入、非 UTF-8。
- `3`：配置或格式错误。
- `4`：启用 `--fail-on-empty` 且没有生成任务。
- `5`：输出文件写入失败。
- `70`：其他可恢复异常。

## Python API

```python
from agent_task_slicer import SlicerConfig, TaskSlicer
from agent_task_slicer.exporters import export_json

config = SlicerConfig(max_tasks=20, package_prefix="AG")
slicer = TaskSlicer(config)
result = slicer.slice_file("examples/sample_prd.md")

for task in result.tasks:
    print(task.id, task.title, task.risk_score)

json_text = export_json(result)
```

快捷函数：

```python
from agent_task_slicer import slice_text

result = slice_text("# 任务：实现 CLI\n- 支持 JSON 输出")
```

## 配置

配置文件使用 JSON，避免引入 YAML/TOML 运行时依赖。示例：

```json
{
  "max_tasks": 20,
  "package_prefix": "AG",
  "default_test_commands": ["python -m unittest"],
  "risk_keywords": {
    "auth": 3,
    "database": 3,
    "migration": 3,
    "payment": 3,
    "性能": 2,
    "权限": 3
  },
  "task_markers": ["任务", "需求", "实现", "支持", "Task", "Feature"],
  "path_roots": ["src", "tests", "docs", "examples", ".github"],
  "infer_dependencies": true,
  "include_low_confidence_tasks": true
}
```

配置会严格校验，未知字段、错误类型、越界数值都会返回配置错误。

## 输出格式

### Markdown

适合直接复制给 agent、issue、PR 评论或开发计划。每个任务包含目标、scope、输入文件、验收标准、风险、验证命令和依赖。

### JSON

适合编排系统消费。顶层结构：

```json
{
  "source": "examples/sample_prd.md",
  "warnings": [],
  "metadata": {"title": "Agent Inbox Automation PRD", "sections": 5},
  "tasks": [
    {
      "id": "T001",
      "title": "任务：读取 Markdown 和 issue",
      "goal": "...",
      "scope": [],
      "input_files": [],
      "acceptance_criteria": [{"text": "...", "source": "generated"}],
      "risks": [],
      "risk_score": 2,
      "suggested_commands": ["python -m unittest"],
      "dependencies": []
    }
  ]
}
```

### Graphviz DOT

适合生成依赖图：

```bash
agent-task-slicer examples/sample_prd.md --format dot -o outputs/tasks.dot
dot -Tsvg outputs/tasks.dot -o outputs/tasks.svg
```

## CI 和 Agent 集成

GitHub Actions 已包含在 `.github/workflows/ci.yml`，会在 Python 3.9 到 3.13 上执行：

```bash
python -m pip install -e .
python -m unittest
```

典型 agent 集成方式：

```bash
agent-task-slicer docs/prd.md --format json -o work/tasks.json
```

然后由你的编排器读取 `tasks.json`，按 `dependencies` 拓扑排序，把每个任务的 `goal`、`scope`、`input_files`、`acceptance_criteria` 发送给 Codex、Claude Code 或内部 agent。

## 识别逻辑

当前版本使用启发式规则：

- Markdown 标题和列表解析。
- 中英文动作词、任务标记识别。
- 代码路径和目录提示抽取。
- 显式依赖词识别，例如 `依赖：...`、`depends on ...`、`after ...`。
- 相同输入路径的后续任务自动依赖前序任务。
- 风险关键词、scope 大小、文件数量共同影响风险评分。
- 缺少验收标准时生成默认验收标准。

## 限制

- 不调用 LLM，不理解完整语义，只做可解释的静态启发式切片。
- 不会读取仓库代码内容，只根据输入文本中的路径和关键词推断。
- 依赖推断是保守近似，复杂项目仍建议人工 review。
- 配置文件只支持 JSON。
- DOT 输出只描述任务依赖，不包含完整项目甘特图或资源排期。

## 开发指南

本地开发：

```bash
python -m pip install -e .
python -m unittest
```

项目结构：

- `src/agent_task_slicer/parser.py`：Markdown/plain text 解析。
- `src/agent_task_slicer/heuristics.py`：任务识别、依赖推断、风险和验证命令。
- `src/agent_task_slicer/exporters.py`：Markdown/JSON/DOT 导出。
- `src/agent_task_slicer/cli.py`：命令行入口和退出码。
- `tests/`：纯 `unittest` 测试。
- `examples/`：样例 PRD 和配置。

推荐贡献方式：

1. 先为新规则补测试。
2. 保持运行时标准库优先。
3. 任何启发式新增都要可解释，并尽量避免隐藏外部状态。
4. README 和示例需要随 CLI/API 行为同步更新。

## 许可证

MIT。

## English

`agent-task-slicer` is a dependency-free Python developer tool that slices PRDs, GitHub issues, Markdown requirements, task lists, and code path lists into small work packages suitable for Codex, Claude Code, or custom coding agents.

Each package includes:

- Goal and scope
- Input file/path hints
- Acceptance criteria
- Risk reasons and a 1-5 risk score
- Suggested verification commands
- Dependencies
- Markdown, JSON, and Graphviz DOT output

This is not a hosted project management product. It is a lightweight repository tool that can run locally, in CI, or inside your agent orchestration pipeline.

## Use Cases

- Break large product requirements into agent-sized tasks.
- Extract work packages from issues, PRDs, checklists, and implementation plans.
- Generate clearer context before asking a coding agent to act.
- Feed JSON tasks into an internal orchestrator.
- Produce DOT dependency graphs for reviews and documentation.

## Installation

Install from source:

```bash
python -m pip install -e .
```

Run tests:

```bash
python -m unittest
```

Python 3.9+ is required. Runtime code uses only the Python standard library.

## CLI

Read Markdown and print Markdown output:

```bash
agent-task-slicer examples/sample_prd.md
```

Print JSON:

```bash
agent-task-slicer examples/sample_prd.md --format json
```

Print Graphviz DOT:

```bash
agent-task-slicer examples/sample_prd.md --format dot -o outputs/tasks.dot
```

Read from stdin:

```bash
cat examples/sample_prd.md | agent-task-slicer - --format markdown
```

Limit task count and change the package prefix:

```bash
agent-task-slicer examples/sample_prd.md --max-tasks 10 --prefix AG
```

Use a config file:

```bash
agent-task-slicer examples/sample_prd.md -c examples/config.json --format json
```

### Exit Codes

- `0`: success.
- `2`: input error, such as missing file, empty input, or non-UTF-8 file.
- `3`: configuration or format error.
- `4`: `--fail-on-empty` was enabled and no tasks were produced.
- `5`: output write error.
- `70`: other recoverable failure.

## Python API

```python
from agent_task_slicer import SlicerConfig, TaskSlicer
from agent_task_slicer.exporters import export_json

config = SlicerConfig(max_tasks=20, package_prefix="AG")
slicer = TaskSlicer(config)
result = slicer.slice_file("examples/sample_prd.md")

for task in result.tasks:
    print(task.id, task.title, task.risk_score)

json_text = export_json(result)
```

Shortcut:

```python
from agent_task_slicer import slice_text

result = slice_text("# Task: implement CLI\n- Support JSON output")
```

## Configuration

Configuration files are JSON to avoid a runtime YAML/TOML dependency:

```json
{
  "max_tasks": 20,
  "package_prefix": "AG",
  "default_test_commands": ["python -m unittest"],
  "risk_keywords": {
    "auth": 3,
    "database": 3,
    "migration": 3,
    "payment": 3
  },
  "task_markers": ["Task", "Feature", "Requirement"],
  "path_roots": ["src", "tests", "docs", "examples", ".github"],
  "infer_dependencies": true,
  "include_low_confidence_tasks": true
}
```

Config validation is strict. Unknown keys, wrong types, and out-of-range values fail fast.

## Output Formats

Markdown is intended for agents, issues, pull request comments, and planning docs.

JSON is intended for orchestration systems. It contains `source`, `warnings`, `metadata`, and a `tasks` array.

DOT is intended for dependency visualization:

```bash
agent-task-slicer examples/sample_prd.md --format dot -o outputs/tasks.dot
dot -Tsvg outputs/tasks.dot -o outputs/tasks.svg
```

## CI and Agent Integration

GitHub Actions are provided in `.github/workflows/ci.yml` and run on Python 3.9 through 3.13:

```bash
python -m pip install -e .
python -m unittest
```

Typical agent pipeline step:

```bash
agent-task-slicer docs/prd.md --format json -o work/tasks.json
```

Your orchestrator can then read `tasks.json`, topologically order tasks by `dependencies`, and send each package's `goal`, `scope`, `input_files`, and `acceptance_criteria` to Codex, Claude Code, or an internal agent.

## How It Works

The current version uses transparent heuristics:

- Markdown heading and list parsing.
- English and Chinese action words and task markers.
- Code path and directory hint extraction.
- Explicit dependency phrases such as `depends on`, `after`, and `依赖`.
- Later tasks sharing the same input path depend on earlier tasks.
- Risk keywords, scope size, and file count contribute to risk scoring.
- Default acceptance criteria are generated when the input does not provide any.

## Limitations

- It does not call an LLM and does not perform deep semantic reasoning.
- It does not inspect repository source code; it uses only the input text.
- Dependency inference is a conservative approximation and should be reviewed.
- Config files are JSON only.
- DOT output describes task dependencies, not a full project schedule.

## Development

```bash
python -m pip install -e .
python -m unittest
```

Main modules:

- `src/agent_task_slicer/parser.py`: Markdown/plain text parsing.
- `src/agent_task_slicer/heuristics.py`: task recognition, dependency inference, risk scoring, verification commands.
- `src/agent_task_slicer/exporters.py`: Markdown/JSON/DOT export.
- `src/agent_task_slicer/cli.py`: command line entry point and exit codes.
- `tests/`: `unittest` suite.
- `examples/`: sample PRD and config.

Contribution guidelines:

1. Add tests before changing heuristics.
2. Prefer the Python standard library for runtime code.
3. Keep heuristics explainable and deterministic.
4. Update README and examples when CLI/API behavior changes.

## License

MIT.

