# TASK

## 0. 目标

- 基于模拟的 Ydata 数据，加工出违约历史相关特征，提炼数据价值。
- 当前阶段聚焦特征/产品层，不包含评分映射、模型训练、接口服务和对外交付系统。

## 1. 背景

- 业务场景是围绕信贷申请记录与违约标签，沉淀可复用的数据产品，为传统评分业务提供信息增益。
- 当前希望围绕每个用户主键构建违约历史特征，支持黑名单命中、历史回溯、分口径统计和窗口计数。
- 主键统计口径包含三种：
  - `PID + ID`
  - `ID`
  - `PID`

## 2. 开发环境

- 运行环境：`dl_new`
- 当前验证命令：
  - `conda run -n dl_new python -m pytest -q`
  - `conda run -n dl_new python run_pipeline.py`

## 3. 数据说明

- 输入样例：[`data/demo/y.csv`](D:\wise\acct_RZ\data\demo\y.csv)
- 当前默认输出目录：[`data/result`](D:\wise\acct_RZ\data\result)

## 4. 业务规则

- 只有 `target == 1` 视为违约事件。
- 其他标签如 `0`、`-2`、未来的 `0.5`、`-1` 等，默认都不是违约事件。
- 违约事件生效日规则：
  - `event_dt = app_dt + mob`
  - 若 `mob` 缺失，则先按 `6` 个月处理
- 黑名单命中、历史回溯和滚动窗口统计都以 `event_dt` 为准，而不是原始 `app_dt`。

## 5. 业务阶段状态

| 阶段 | 目标 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| step1 | 简单黑名单产品 | 已完成 | 已支持按 `PID+ID / ID / PID` 三种口径判断截至申请日是否命中过违约，并输出首次命中日期 |
| step2 | 可回溯黑名单产品 | 已完成 | 已支持按每个 `app_dt` 回看历史违约命中、累计命中次数和最近命中日期 |
| step3 | 分口径黑名单产品 | 已完成 | 已支持按 `Org_class_new` 输出长表形式的分机构大类黑名单命中结果 |
| step4 | 分口径违约记录产品 | 已完成 | 已支持近 `3/6/12` 月违约次数、部分机构大类计数、`fpd/dpd` 计数等窗口特征 |
| step5 | 评分映射/信用评分产出 | 待实现 | 当前未设计，也未实现 |
| step6 | 对外服务/查询接口 | 待实现 | 当前未设计，也未实现 |

## 6. 工程实现状态

| 模块 | 内容 | 状态 | 说明 |
| --- | --- | --- | --- |
| 原始数据标准化 | `app_dt` 解析、`mob` 回填、`is_default`、`event_dt` 生成 | 已完成 | 见 [`normalize.py`](D:\wise\acct_RZ\src\acct_rz\normalize.py) |
| 主键展开 | `pid_id / id / pid` 三种口径统一展开 | 已完成 | 见 [`keys.py`](D:\wise\acct_RZ\src\acct_rz\keys.py) |
| 违约事件事实层 | 默认事件过滤与事件长表构建 | 已完成 | 见 [`events.py`](D:\wise\acct_RZ\src\acct_rz\events.py) |
| 黑名单特征 | `step1 + step2` 截至日命中与回溯 | 已完成 | 见 [`features_blacklist.py`](D:\wise\acct_RZ\src\acct_rz\features_blacklist.py) |
| 分机构黑名单特征 | `step3` 分 `Org_class_new` 结果 | 已完成 | 见 [`features_org_blacklist.py`](D:\wise\acct_RZ\src\acct_rz\features_org_blacklist.py) |
| 窗口统计特征 | `step4` 滚动窗口计数 | 已完成 | 见 [`features_windows.py`](D:\wise\acct_RZ\src\acct_rz\features_windows.py) |
| 离线管道入口 | 读取 CSV 并生成 4 张结果表 | 已完成 | 见 [`pipeline.py`](D:\wise\acct_RZ\src\acct_rz\pipeline.py) |
| 可复用启动脚本 | 根目录一键运行脚本 | 已完成 | 见 [`run_pipeline.py`](D:\wise\acct_RZ\run_pipeline.py) |
| 自动化测试 | 单元测试与烟测 | 已完成 | 见 [`tests`](D:\wise\acct_RZ\tests)，当前 `10` 个测试通过 |
| 设计文档 | 设计稿与实现计划 | 已完成 | 见 [`docs/plans`](D:\wise\acct_RZ\docs\plans) |
| Git 版本管理 | 本地提交并推送远程 | 已完成 | 已推送到远程 `main` |

## 7. 待实现任务

| 任务 | 状态 | 优先级 | 说明 |
| --- | --- | --- | --- |
| 评分映射方案设计 | 待实现 | 高 | 将黑名单/窗口特征转成信用评分或评分卡规则 |
| 评分层实现 | 待实现 | 高 | 基于特征层结果输出最终评分字段 |
| 对外查询接口设计 | 待实现 | 中 | 明确离线产物如何被下游查询或批量消费 |
| 在线/准实时方案 | 待实现 | 中 | 当前仅支持离线批处理，尚未支持准实时查询 |
| 特征扩展 | 待实现 | 中 | 可继续扩展更多机构维度、渠道维度、去重计数等特征 |
| 数据质量统计 | 待实现 | 中 | 当前规则已做轻量清洗，但未系统输出异常记录统计报表 |
| `.gitignore` 整理 | 待实现 | 低 | 当前本地仍有 `__pycache__` 和异常缓存目录未被忽略 |
| CLI/包入口增强 | 待实现 | 低 | 当前脚本已可运行，但尚未做更完整的参数校验与日志输出 |

## 8. 当前运行方式

### 运行测试

```powershell
conda run -n dl_new python -m pytest -q
```

### 生成结果到默认目录

```powershell
conda run -n dl_new python run_pipeline.py
```

### 指定输入输出路径

```powershell
conda run -n dl_new python run_pipeline.py --input data/demo/y.csv --output data/result
```

## 9. Query lookup update

- Historical source stays `data/demo/y.csv`; it is only used to build default-event history.
- Arbitrary external query rows can now provide `app_dt` plus `PID`, `ID`, or both.
- Offline batch output and query lookup share the same lookup logic.
- All outputs retain `PID` and `ID` split columns alongside `key_type` and `key_value`.
- Query CLI example:

```powershell
conda run -n dl_new python run_pipeline.py --mode query --input data/demo/y.csv --query-input data/demo/query.csv --output data/result
```

## 10. 当前交接状态

- 查询 lookup 重构已完成。
- 离线批处理与查询模式共用同一套 lookup 逻辑。
- 最终输出中的日期列统一为 `YYYYMMDD` 形式的 `i64`。
- 数值型查询日期如 `20251006` 已可正确解析。
- 最近一次全量回归结果：`conda run -n dl_new python -m pytest -q` -> `22 passed`。
- 后续新会话优先参考：
  - `docs/plans/2026-03-10-ydata-query-lookup-status.md`

## 11. 当前统一状态表

### 11.1 项目当前阶段

| 项目 | 当前状态 | 说明 |
| --- | --- | --- |
| 历史事件标准化 | 已完成 | 由 `normalize.py` 负责 `app_dt` 解析、`mob` 补齐、`is_default` 与 `event_dt` 生成 |
| 键展开与查询快照 | 已完成 | 同时支持历史批量快照与外部单键查询快照 |
| step1 黑名单 | 已完成 | 支持 `PID` / `ID` / `PID+ID` 查询 |
| step2 回溯明细 | 已完成 | 返回命中状态、首末次命中日期、累计命中次数 |
| step3 机构维度黑名单 | 已完成 | 默认输出长表 |
| step4 时间窗计数 | 已完成 | 支持 3/6/12 月窗口计数及部分机构、表现类型拆分 |
| 离线批处理 | 已完成 | 与查询模式共用 lookup 逻辑 |
| 查询模式 CLI | 已完成 | `run_pipeline.py --mode query` |
| 输出日期列 `i64` 化 | 已完成 | 最终输出中的所有日期列统一为 `YYYYMMDD` 形式的 `i64` |
| 数值型查询日期解析 | 已完成 | 例如 `20251006` 不再被错误解析为远未来日期 |

### 11.2 当前统一入口

| 类型 | 入口 | 说明 |
| --- | --- | --- |
| 离线批处理 CLI | `conda run -n dl_new python run_pipeline.py` | 从 `data/demo/y.csv` 生成 step1~4 parquet |
| 查询模式 CLI | `conda run -n dl_new python run_pipeline.py --mode query --input data/demo/y.csv --query-input data/demo/query.csv --output data/result` | 使用历史事件 + 外部查询输入生成 step1~4 parquet |
| Python 查询入口 | `acct_rz.query_lookup.lookup_all_steps` | 返回 `step1`、`step2`、`step3`、`step4` 四个 DataFrame |
| 状态交接文档 | `docs/plans/2026-03-10-ydata-query-lookup-status.md` | 记录当前可运行状态与后续接续说明 |

### 11.3 当前输出约定

| 项目 | 约定 |
| --- | --- |
| 共同键列 | `app_dt`、`key_type`、`key_value`、`PID`、`ID` |
| 日期列类型 | 最终输出统一为 `i64` |
| 日期列格式 | `YYYYMMDD` |
| `step3` 形态 | 默认长表 |
| 历史数据源 | `y.csv` 仅作为历史违约事件来源 |
| 外部查询限制 | 查询键不要求事先存在于历史申请中 |

### 11.4 当前验证结果

| 检查项 | 当前结果 |
| --- | --- |
| 全量测试命令 | `conda run -n dl_new python -m pytest -q` |
| 最近回归结果 | `22 passed` |
| 查询样例文件 | `data/demo/query.csv` |
| 默认输出目录 | `data/result` |

### 11.5 后续待办

| 任务 | 状态 | 说明 |
| --- | --- | --- |
| 评分映射设计 | 待开始 | 目前只完成特征层与查询层 |
| 对外服务接口设计 | 待开始 | 当前仅支持离线与本地查询模式 |
| CLI 参数校验增强 | 可继续 | 现有可运行，但错误提示仍可更细化 |
| `.gitignore` 清理 | 可继续 | 仓库内仍有缓存目录与临时文件管理空间 |
