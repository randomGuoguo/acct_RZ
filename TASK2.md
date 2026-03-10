# TASK2

## 0. 文档目的

本文件用于提供项目当前统一状态，供后续子项目、自动化流程和新会话直接读取。

使用原则：

- 只保留当前有效状态，不重复记录历史阶段性描述。
- 统一记录项目目标、入口、输出约定、模块状态、验证结果和后续待办。
- 如状态发生变化，应优先更新本文件，并同步更新相关交接文档。

## 1. 项目目标与范围

### 1.1 当前目标

基于 Ydata 历史申请与违约标签，构建可复用的违约历史特征与查询能力，支持：

- 离线批处理生成 `step1~step4` 特征结果
- 外部查询输入按 `PID`、`ID`、`PID+ID` 加 `app_dt` 查询 `step1~step4`
- 离线批处理与查询模式共用同一套 lookup 逻辑

### 1.2 当前范围

当前已覆盖：

- 历史事件标准化
- 键展开与查询快照构建
- step1 黑名单
- step2 回溯明细
- step3 机构维度黑名单
- step4 时间窗违约计数
- 离线 CLI
- 查询 CLI

当前未覆盖：

- 评分映射
- 模型训练
- 对外服务化接口

## 2. 当前统一状态总览

| 领域 | 当前状态 | 说明 |
| --- | --- | --- |
| 历史事件标准化 | 已完成 | `normalize.py` 负责 `app_dt` 解析、`mob` 补齐、`is_default` 与 `event_dt` 生成 |
| 历史事件事实表 | 已完成 | `events.py` 基于历史数据生成共享事件事实表 |
| 历史查询快照 | 已完成 | 支持从历史申请数据生成 batch lookup 快照 |
| 外部查询快照 | 已完成 | 支持外部 `PID` / `ID` / `PID+ID` 查询输入 |
| step1 | 已完成 | 返回是否命中历史违约及首个命中日期 |
| step2 | 已完成 | 返回命中状态、首末次命中日期、累计命中次数 |
| step3 | 已完成 | 默认输出长表，按 `Org_class_new` 返回机构维度命中结果 |
| step4 | 已完成 | 返回 3/6/12 月窗口计数及部分机构、表现类型拆分 |
| 批处理与查询共用 lookup | 已完成 | 批处理和 query mode 共用同一套 lookup 实现 |
| 输出保留拆分键列 | 已完成 | 输出保留 `PID`、`ID`、`key_type`、`key_value` |
| 最终日期列 `i64` 化 | 已完成 | 最终输出中的所有日期列统一为 `YYYYMMDD` 形式的 `i64` |
| 数值型查询日期解析 | 已完成 | 例如 `20251006` 可正确解析，不再被误转成远未来日期 |

## 3. 业务规则

| 规则项 | 当前规则 |
| --- | --- |
| 违约事件定义 | 仅 `target == 1` 视为违约事件 |
| 其他标签处理 | `0`、`-2`、`0.5`、`-1` 等均视为非违约事件 |
| 生效日期规则 | `event_dt = app_dt + mob_filled(月)` |
| `mob` 缺失处理 | 缺失时按 `6` 个月处理 |
| 匹配依据 | 黑名单、回溯和窗口统计均以 `event_dt` 为准，不以原始 `app_dt` 为准 |
| 历史数据源角色 | `y.csv` 仅作为历史违约事件来源 |
| 外部查询要求 | 查询键不要求事先存在于历史申请中 |
| 未命中历史时返回 | 仍保留查询行，计数字段为 `0`，日期字段为 `null` |
| step3 输出形态 | 默认长表 |

## 4. 当前统一入口

### 4.1 CLI 入口

| 类型 | 命令 | 说明 |
| --- | --- | --- |
| 全量测试 | `conda run -n dl_new python -m pytest -q` | 运行项目回归测试 |
| 离线批处理 | `conda run -n dl_new python run_pipeline.py` | 使用默认输入输出运行批处理 |
| 指定批处理输入输出 | `conda run -n dl_new python run_pipeline.py --input data/demo/y.csv --output data/result` | 指定历史输入与输出目录 |
| 查询模式 | `conda run -n dl_new python run_pipeline.py --mode query --input data/demo/y.csv --query-input data/demo/query.csv --output data/result` | 使用历史事件 + 外部查询输入生成 step1~4 输出 |

### 4.2 Python 入口

| 入口 | 位置 | 说明 |
| --- | --- | --- |
| `run_demo_pipeline` | `src/acct_rz/pipeline.py` | 批处理主入口 |
| `lookup_all_steps` | `src/acct_rz/query_lookup.py` | 查询模式主入口，返回 `step1~step4` 四个 DataFrame |
| `build_external_query_snapshot` | `src/acct_rz/query_snapshot.py` | 外部查询快照构建与校验入口 |

## 5. 输出约定

### 5.1 共同输出键列

所有 step 输出都保留：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

### 5.2 日期列约定

| 项目 | 约定 |
| --- | --- |
| 内部计算日期类型 | `Date` |
| 最终输出日期类型 | `i64` |
| 最终输出日期格式 | `YYYYMMDD` |
| 适用范围 | `app_dt` 以及所有最终结果中的日期列 |

示例：

- `app_dt = 20251006`
- `first_default_event_dt = 20240701`

### 5.3 各 step 输出说明

| Step | 输出粒度 | 主要字段 |
| --- | --- | --- |
| step1 | 每个查询键一行 | `black_hit_ever`、`first_default_event_dt` |
| step2 | 每个查询键一行 | `black_hit_ever`、`first_default_event_dt`、`latest_default_event_dt`、`hit_event_cnt_asof_dt` |
| step3 | 长表 | `org_class`、`black_hit_ever_by_org_class`、`first_default_event_dt_by_org_class` |
| step4 | 每个查询键一行 | `default_cnt_3m`、`default_cnt_6m`、`default_cnt_12m` 及若干拆分窗口字段 |

## 6. 实现模块状态

| 模块 | 文件 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| 标准化层 | `src/acct_rz/normalize.py` | 已完成 | 统一处理申请日期与事件日期 |
| 键处理层 | `src/acct_rz/keys.py` | 已完成 | 支持全量扩键与单键查询快照 |
| 事件层 | `src/acct_rz/events.py` | 已完成 | 生成共享违约事件事实表 |
| 查询快照层 | `src/acct_rz/query_snapshot.py` | 已完成 | 负责 query 输入解析与校验 |
| lookup 基础层 | `src/acct_rz/lookup_base.py` | 已完成 | 负责匹配辅助逻辑与最终日期列转换 |
| step1/step2 | `src/acct_rz/features_blacklist.py` | 已完成 | 黑名单与回溯 lookup |
| step3 | `src/acct_rz/features_org_blacklist.py` | 已完成 | 机构维度长表 lookup |
| step4 | `src/acct_rz/features_windows.py` | 已完成 | 窗口计数 lookup |
| 查询汇总入口 | `src/acct_rz/query_lookup.py` | 已完成 | 汇总返回四个 step 输出 |
| 批处理入口 | `src/acct_rz/pipeline.py` | 已完成 | 使用历史快照 + 共享事件表输出 batch 结果 |
| CLI | `run_pipeline.py` | 已完成 | 支持 `batch` 与 `query` 两种模式 |
| 测试 | `tests/` | 已完成 | 覆盖 query lookup、输出 schema 与关键 bug 修复 |

## 7. 当前验证结果

| 检查项 | 当前结果 |
| --- | --- |
| 运行环境 | `dl_new` |
| 最近全量测试命令 | `conda run -n dl_new python -m pytest -q` |
| 最近全量测试结果 | `22 passed` |
| 重点修复验证 | 数值型查询日期 `20251006` 已正确输出为 `20251006` |

## 8. 数据与目录

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 历史样例数据 | `data/demo/y.csv` | 历史申请与违约标签样例 |
| 查询样例数据 | `data/demo/query.csv` | 查询模式样例输入 |
| 默认输出目录 | `data/result` | step1~step4 parquet 默认输出位置 |
| 设计文档 | `docs/plans/2026-03-10-ydata-query-lookup-design.md` | 查询 lookup 设计说明 |
| 实现计划 | `docs/plans/2026-03-10-ydata-query-lookup.md` | 查询 lookup 实现计划 |
| 状态交接文档 | `docs/plans/2026-03-10-ydata-query-lookup-status.md` | 当前运行状态与交接补充 |

## 9. 后续待办

| 任务 | 状态 | 说明 |
| --- | --- | --- |
| 评分映射设计 | 待开始 | 当前仅完成特征层与查询层 |
| 对外服务接口设计 | 待开始 | 当前仅支持离线和本地查询模式 |
| CLI 参数校验增强 | 可继续 | 可补充更细的输入校验与错误提示 |
| 输出消费规范 | 可继续 | 可补充 parquet 字段说明与下游接入规范 |
| `.gitignore` 整理 | 可继续 | 仓库中仍有缓存目录和临时文件管理空间 |

## 10. 交接说明

后续新会话建议按以下顺序读取：

1. `TASK2.md`
2. `docs/plans/2026-03-10-ydata-query-lookup-status.md`
3. `README.md`

补充说明：

- `TASK.md` 保留为历史任务记录，不再作为当前统一状态入口。
- 如后续修改输出 schema、CLI 入口或测试结果，优先更新本文件。
