# PLECS-MCP 开发计划（生产级）

> 目标：把 PLECS 的**全场仿真能力**（电气 / 控制 / 热 / 磁 + 仿真脚本与分析）封装成一个可靠的本地 MCP 服务器，让 Agent 用自然语言完成"搭电路 → 配参数 → 跑仿真 → 读结果 → 调优"的全链路。
>
> 状态基线：已用最小验证证明"Agent 从零生成 `.plecs` → 真实 PLECS 加载 → 仿真 → Vo=11.9985V（理论 12V）"全链路成立。本计划据此扩展到生产质量。
> 参考：`/mcp-builder` 技能（四阶段流程、工具命名/Schema/注解/错误信息规范、评测）。

---

## 1. 范围与目标

### 1.1 能力目标（按域）
- **电气**：DC/DC（buck/boost/buck-boost/SEPIC…）、桥臂/全桥、单/三相逆变与整流、RLC、源/表计。
- **控制环路**：求和、增益、PI/PID、限幅、PWM 比较器/载波、采样、传函/状态机，构建闭环。
- **仿真脚本（Simulation Scripts）**：多工况批量、扫参、用脚本驱动模块与求解设置。
- **分析（Analysis）**：稳态分析（Steady-State）、交流小信号/阻抗（AC Sweep）、损耗与效率、结温。
- **热仿真**：损耗标定的半导体、散热器、热网络、热探头与结温读取。
- **磁仿真**：磁域元件（磁阻/绕组/磁芯），磁-电耦合。

### 1.2 非目标（明确边界，避免过度承诺）
- 不做"任意复杂原理图的像素级自动布线"——电气连通性靠**符号化连接**（元件名+端子号）保证正确，可视布局尽力而为，复杂图可交回 GUI 精修。
- 不绕过 PLECS：所有仿真经官方 XML-RPC / pyplecs；搭图经**生成 `.plecs` 文件**（XML-RPC 不支持画图，这是已知限制）。
- 不执行任何破坏性操作（删模型文件、改 PLECS 全局配置）而不经确认。

### 1.3 成功判据（产品级 Definition of Done）
- 每个里程碑：在**完整路径**上跑通（真实 PLECS 加载+仿真），用**≥2 个信号/指标**判定，关键量与解析期望在容差内一致。
- 评测集（≥10 个真实任务）通过率达标；错误信息可操作；`claude mcp add` 一键挂载；文档+示例齐全；通过代码评审清单与安全评审。

---

## 2. 技术选型（ADR 摘要）

| 决策 | 选择 | 理由 / 推翻条件 |
|---|---|---|
| 语言 | **Python 3.10+** | 整个 PLECS 生态（pyplecs、xmlrpc、已验证 PoC、numpy 分析）都是 Python；与现有本地 MCP 一致。mcp-builder 默认 TS，但此处 Python 原生更优。若未来要做远程多租户 HTTP 服务，再评估 TS 重写。 |
| MCP SDK / 传输 | 官方 `mcp` SDK，**stdio 本地** | 必须运行在用户 Windows 机器上、直连 `localhost:1080`；本地 stdio 最简、最稳、最安全。 |
| 仿真后端 | **pyplecs**（`PlecsServer` + 批量并行）+ 直连 `xmlrpc.client` 兜底 | pyplecs 的 XML-RPC 层已验证正确、成熟、有测试；批量并行 ~4-5x 提速；缓存复用。 |
| 搭图引擎 | 自研 **Spec→.plecs 序列化器** + 组件知识库 | XML-RPC 无法画图；`.plecs` 是可生成的文本格式（已验证）。 |
| 数据分析 | numpy / scipy | 稳态、纹波、THD、超调、上升/调节时间、RMS、效率、FFT。 |
| 绘图 | matplotlib（落盘 PNG，返回路径） | 控制上下文体积，便于人看波形。 |
| Schema/校验 | pydantic v2 | 输入/输出 Schema、约束、清晰描述。 |
| 工程化 | ruff + pytest + 结构化日志（structlog） | 与 pyplecs 同栈，便于协作。 |

---

## 3. 架构

```
plecs_mcp/
  server.py            # MCP 入口：注册工具、stdio run、初始化选项
  config.py            # host/port/timeout、PLECS 路径、缓存目录（env + 文件）
  rpc/
    client.py          # XML-RPC 封装（连接、重试、错误归一化）
    pyplecs_backend.py # pyplecs 适配（单次/批量/缓存）
  authoring/
    spec.py            # 电路 Spec 数据模型（pydantic）：components/connections/init/solver
    serializer.py      # Spec -> .plecs 文本（golden-file 测试覆盖）
    kb/                # 组件知识库（YAML）：Type、端子映射、参数名/单位/默认、域
    validate.py        # 生成后加载校验，归一化 PLECS 报错
  results/
    store.py           # 结果句柄存储（避免把大数组塞进上下文）
    analysis.py        # 波形指标（numpy/scipy）
    plot.py            # matplotlib 出图
  tools/               # 各 MCP 工具（每工具一文件，薄封装）
  errors.py            # 错误分类 + 可操作建议
tests/                 # 单元（离线）+ 集成（需 Windows+PLECS）+ 评测
docs/                  # 安装、工具参考、示例、组件库说明
golden_models/         # 已验证拓扑（既当模板，又当回归基线）
eval/                  # mcp-builder 第四阶段评测集（XML）
```

**关键设计：结果句柄**。仿真结果（时间+多信号，可能数万点）存服务端，工具默认只返回**摘要/标量指标**；原始波形仅按需、降采样返回或落盘出图。这是产品级上下文管理的核心。

**关键设计：Spec 为单一事实源**。搭图/改图都先改 Spec（结构化 JSON），`commit` 时序列化为 `.plecs` 并加载校验。保证可重放、可测试、可回滚。

---

## 4. 工具目录（遵循 mcp-builder：`plecs_` 前缀、动作化命名、注解、可操作错误）

> 注解：`readOnlyHint / destructiveHint / idempotentHint / openWorldHint`。下表 RO=只读、Idem=幂等。

### 4.1 连接与模型生命周期
| 工具 | 作用 | 注解 |
|---|---|---|
| `plecs_status` | 探测 PLECS 是否在线（host:port）、版本 | RO, Idem |
| `plecs_load_model` | 加载 `.plecs` | 非破坏 |
| `plecs_close_model` | 关闭模型 | Idem |

### 4.2 搭图（差异化能力）
| 工具 | 作用 | 注解 |
|---|---|---|
| `plecs_list_component_types` | 列出知识库支持的元件（按域过滤） | RO |
| `plecs_describe_component` | 返回某元件的端子映射、参数名/单位/默认 | RO |
| `plecs_build_model` | **工作流工具**：传入电路 Spec → 生成 `.plecs` → 加载 → 返回校验结果 | 非破坏 |
| `plecs_edit_model` | 在 Spec 上增删元件/连线/改参 → 重新提交 | 非破坏 |
| `plecs_validate_model` | 加载并返回连通性/参数错误（归一化、含修复建议） | RO |

### 4.3 参数
| 工具 | 作用 | 注解 |
|---|---|---|
| `plecs_get_params` | 读 ModelVars/组件参数及范围 | RO |
| `plecs_set_param` / `plecs_set_params_batch` | 改参数（`plecs.set`） | Idem |

### 4.4 仿真与脚本/分析
| 工具 | 作用 | 注解 |
|---|---|---|
| `plecs_simulate` | 单次仿真，返回结果句柄+摘要 | 非破坏 |
| `plecs_simulate_batch` | 批量并行（pyplecs），扫参 | 非破坏 |
| `plecs_run_script` | 运行 Simulation Script / 脚本化多工况（含 SolverOpts、模块驱动） | 非破坏 |
| `plecs_analyze` | 稳态分析 / AC 扫频(阻抗·bode) / 损耗 | 非破坏 |

### 4.5 结果与可视化
| 工具 | 作用 | 注解 |
|---|---|---|
| `plecs_analyze_waveform` | 对句柄结果算指标：steady_state, ripple_pp, thd, overshoot, settling_time, rise_time, rms, mean, efficiency, Tj 等 | RO |
| `plecs_get_waveform` | 按信号名返回降采样序列 | RO |
| `plecs_plot_waveform` | 出 PNG，返回路径 | RO |

> 每个工具：pydantic 输入/输出 Schema、字段示例、错误返回"原因+下一步建议"（如"端子 3 越界：Mosfet 仅 1/2/3，3 为栅极信号端"）。

---

## 5. 组件知识库（搭图可靠性的根基）

- **结构**：每个元件一条 YAML：`plecs_type`、`terminals`（index→角色/域）、`params`（名/单位/默认/范围）、`domain`(electrical|control|thermal|magnetic)、`notes`。
- **来源**：① pyplecs 样例模型（buck/boost/buckboost/nibb/fb）；② plecs-expert 技能参考库；③ **对真实 PLECS 做单元件 round-trip 验证**（生成→加载→读回端子/参数）固化为事实。
- **校验**：KB 完整性单测 + 每个 Type 的 round-trip 集成测试；跨 PLECS 版本各自校验，差异显式报错而非静默。
- **黄金模型库**：每类拓扑沉淀一个已验证 `.plecs`，既做生成模板，又做回归基线。

---

## 6. 验证与测试策略（按 CLAUDE.md：完整路径、多信号、可复现）

1. **单元（离线，可 CI）**：Spec→.plecs 序列化器 golden-file 测试；KB 完整性；指标算法（用合成波形验证 THD/超调/调节时间）。
2. **集成（Windows+PLECS，手动/本地钩子）**：每个黄金模型**加载零报错 + 仿真 + 指标对解析期望**（如 buck `Vo≈D·Vi`，boost `Vo≈Vi/(1-D)`，纹波量级、效率）在容差内。
3. **从零搭建回归**：对每类拓扑执行"生成→加载→仿真→断言"，防止 KB/序列化器回归。
4. **评测集（mcp-builder 第四阶段）**：≥10 个真实任务（含搭图、扫参、闭环整定、AC 分析、热/损耗），答案可字符串校验、稳定。
5. **CI 约定**：参考 pyplecs——离线测试入 pre-push 钩子；PLECS 相关测试在 Windows 手动跑，结果归档。

---

## 7. 里程碑路线图（增量交付，每步含通过/失败判据）

| 里程碑 | 内容 | 通过判据 |
|---|---|---|
| **M0 地基** | 仓库脚手架、config、`plecs_status`、结果句柄、打包、`claude mcp add` | 握手成功 + `plecs_status` 对实时 PLECS 返回在线/版本 |
| **M1 跑/读已有模型** | load/set/simulate(单+批)/波形指标/出图 | 驱动 `simple_buck` 样例，Vo/纹波/效率指标正确 |
| **M2 搭图引擎** | Spec+序列化器+KB(电气)+build/validate+电气黄金库 | 从零 buck/boost/buck-boost 加载+仿真在容差内（buck 已验证） |
| **M3 控制环路** | 控制域 KB（求和/增益/PI/PID/PWM 比较器/载波/限幅/采样）+闭环黄金库 | 闭环 buck 稳态跟踪 Vref，超调/调节时间达标 |
| **M4 脚本与分析** | `plecs_run_script` 多工况、稳态分析、AC 扫频/阻抗、脚本扫参 | buck 控制-输出 bode 符合预期；稳态分析收敛 |
| **M5 热与磁（全场）** | 热 KB（损耗数据/散热器/热探头/结温）+磁 KB；损耗/效率/Tj 指标 | 热 buck 报合理损耗与 Tj；磁元件模型可仿真 |
| **M6 加固与评测** | 完整评测、文档、错误信息审计、性能/上下文调优、安全评审 | 评测通过率达标 + 评审清单全绿 |

> 现状已实质性降低 M2 核心风险（符号化连接假设已验证）。建议 M0→M1→M2 优先，尽快让你能用自然语言指挥。

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| `.plecs` 为逆向格式、无官方规范 | golden-file round-trip + 版本探测/锁定 + 加载校验；变化即显式报错 |
| 端子/参数 KB 随 PLECS 版本漂移 | 每版本 round-trip 校验；不命中给清晰建议 |
| XML-RPC 返回结构多变 | 先探测真实返回再写解析（已有教训），防御式解析 |
| 复杂电路自动布线难 | 连通性靠符号化保证电气正确；布局尽力而为，复杂图交回 GUI |
| 大波形撑爆上下文 | 结果句柄 + 服务端指标 + 降采样/出图 |
| 安全（任意路径/破坏操作） | 路径白名单、只读/破坏注解、破坏性操作需确认；仅 localhost |

---

## 9. 近期执行（待你确认即开工）

- **第 1 步（M0+M1）**：搭好服务器骨架与连接/仿真/分析工具，挂上 `claude mcp add`，用 `simple_buck` 样例端到端验证。产出：可用 MCP + 通过的 M1 集成测试。
- **第 2 步（M2）**：把已验证的 buck 搭图能力产品化为 `plecs_build_model` + KB + 黄金库。
- 之后按 M3→M6 推进至控制环路、仿真脚本/分析、热与磁全场能力。

交付物：可 `pip install` 的 `plecs-mcp` 包、`claude mcp add` 配置、工具参考文档、组件库、黄金模型库、评测集与测试报告。
```
