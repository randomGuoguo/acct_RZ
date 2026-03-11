# acct_RZ Architecture

## Product Boundary Update

The primary product boundary is now `blacklist_features.parquet`.

Current layering:
1. fact layer: `normalize.py`, `events.py`, `query_snapshot.py`
2. aggregation layer: `agg_lifetime.py`, `agg_windows.py`, `agg_breakdown.py`, `agg_recency.py`
3. label-family layer: `labels_history.py`, `labels_window.py`, `labels_orgtype.py`, `labels_perftype.py`, `labels_complexity.py`
4. product assembly layer: `product_blacklist_features.py`
5. compatibility layer: `features_blacklist.py`, `features_org_blacklist.py`, `features_windows.py`

Batch and query entrypoints now build the wide feature product first and keep `step1` through `step4` only for compatibility.

V1 intentionally does not expand `sample_flag` into the main wide table.

## 1. 文档目标

本文档面向后续接手本项目的开发者、维护者和协作式 AI，目标是用系统设计文档的方式说明当前项目的整体架构、核心数据流、业务规则、模块职责和维护重点。

本文档优先回答以下问题：

- 这个项目整体在做什么。
- `batch` 和 `query` 两种模式分别怎么运行。
- 原始 `y.csv` 如何被转换成统一中间层和最终输出。
- `src/acct_rz` 下各模块的职责边界是什么。
- 当前业务规则写在哪里，未来改规则应从哪里入手。
- 当前测试覆盖了什么，哪些地方仍有风险。

## 2. 项目定位

`acct_RZ` 是一个基于 `polars` 的离线特征与查询项目，围绕历史申请数据 `y.csv` 提供两类能力：

- `batch` 模式：将历史数据自身展开为全量查询快照，并输出 4 份 parquet 结果。
- `query` 模式：将历史数据作为事实源，对外部 `query.csv` 做按主键、按查询日的回查，并输出同结构结果。

当前系统的核心不是某个单独脚本，而是一条稳定的数据流水线：

`原始申请数据 -> 标准化申请层 -> 主键快照 / 违约事件事实层 -> 四类聚合输出`

## 3. 总体架构

### 3.1 架构分层

从代码职责上看，项目可以分成 5 层：

1. 输入与入口层
   - `run_pipeline.py`
   - 负责命令行参数、模式分流、文件读写

2. 标准化层
   - `src/acct_rz/normalize.py`
   - 负责原始申请数据清洗与违约事件日推导

3. 协议与事实层
   - `src/acct_rz/keys.py`
   - `src/acct_rz/query_snapshot.py`
   - `src/acct_rz/events.py`
   - 负责统一查询主键协议与共享事件事实表

4. 特征聚合层
   - `src/acct_rz/features_blacklist.py`
   - `src/acct_rz/features_org_blacklist.py`
   - `src/acct_rz/features_windows.py`
   - 负责 step1-step4 业务结果计算

5. 流程编排层
   - `src/acct_rz/pipeline.py`
   - `src/acct_rz/query_lookup.py`
   - 负责将共享中间层与各 step 串起来

### 3.2 架构核心判断

这个项目不是“4 个 step 直接读取原始 `y.csv` 分别算结果”，而是先构建两个共享中间层，再让各 step 复用：

- `query_snapshot`：定义“在什么日期，以什么 key，查谁”
- `event_fact`：定义“历史上发生过哪些可被命中的违约事件”

这两个中间层是整个项目最重要的稳定骨架。

它带来两个直接收益：

- `batch` 与 `query` 两种模式共用同一套特征计算内核。
- 规则变更能够集中收敛，而不是散落在多个 step 模块中。

### 3.3 总体流程图

```text
                        +--------------------+
                        |   run_pipeline.py  |
                        +--------------------+
                          |              |
                          | batch        | query
                          v              v
              +------------------+   +-------------------+
              | pipeline.py      |   | query_lookup.py   |
              +------------------+   +-------------------+
                          |              |
                          |              |
                          +------+-------+
                                 |
                                 v
                    +---------------------------+
                    | history_df / query_df     |
                    +---------------------------+
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
      +----------------------+        +----------------------+
      | query_snapshot       |        | event_fact           |
      | keys.py /            |        | events.py            |
      | query_snapshot.py    |        +----------------------+
      +----------------------+                   |
                |                                |
                +-----------+--------------------+
                            |
                            v
       +----------------+----------------+----------------+
       |                |                |                |
       v                v                v                v
   step1/step2       step3            step4         parquet outputs
 blacklist         org blacklist    windows
```

## 4. 运行模式

### 4.1 Batch 模式

入口函数是 `run_demo_pipeline(input_path, out_dir)`，位于 `src/acct_rz/pipeline.py`。

执行过程如下：

1. 从历史 `y.csv` 读取 `history_df`
2. 通过 `build_history_query_snapshot` 生成历史查询快照
3. 通过 `build_default_event_key_fact` 生成违约事件事实表
4. 依次计算 `step1`、`step2`、`step3`、`step4`
5. 将结果写出为 4 份 parquet 文件

这条链路的特点是：

- 查询对象不是外部输入，而是历史数据自身展开后的 key 快照
- 适合离线全量回溯、调试、校验或给下游产物提供基表

### 4.2 Query 模式

入口函数是 `lookup_all_steps(history_df, query_df, step3_format="long")`，位于 `src/acct_rz/query_lookup.py`。

执行过程如下：

1. 读取历史 `y.csv` 作为 `history_df`
2. 读取外部 `query.csv` 作为 `query_df`
3. 通过 `build_external_query_snapshot` 生成外部查询快照
4. 通过 `build_default_event_key_fact(history_df)` 生成共享违约事件事实表
5. 对查询快照执行 `step1`、`step2`、`step3`、`step4`
6. 将结果写出为 4 份 parquet 文件

这条链路的特点是：

- 允许外部指定查询日期与查询 key
- 本质上是“截至指定日期，对历史违约事件做回看”
- 与 batch 模式共用大部分计算逻辑

### 4.3 为什么两条模式能共用逻辑

因为对 step 模块来说，真正重要的输入不是“原始 CSV”，而是以下两个对象：

- 一个标准化后的 `query_snapshot`
- 一个标准化后的 `event_fact`

只要这两个对象结构一致，step 模块并不关心它们来自历史全量展开还是来自外部查询输入。

## 5. 核心数据模型

### 5.1 application_base

来源函数：`build_application_base(df)`，位于 `src/acct_rz/normalize.py`。

这是全项目唯一明确负责“原始申请标准化”的中间层。它至少完成以下工作：

- 将 `app_dt` 解析为 `pl.Date`
- 将 `PID`、`ID` 统一转为字符串
- 将 `mob` 补齐为 `mob_filled`
- 根据 `target` 生成 `is_default`
- 对违约记录推导 `event_dt`

关键业务规则：

- 仅 `target == 1` 认定为违约
- `mob` 为空、空字符串或非法时，回填为 `6`
- `event_dt = app_dt + mob_filled months`

这一层的作用是把原始申请表转成可复用的业务标准层。后续所有模块都应依赖这一层，而不是重复解释原始字段含义。

### 5.2 query_snapshot

这是“标准查询对象”的统一结构，核心字段如下：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

它有两种构造方式：

- `build_history_query_snapshot(df)`：从历史申请展开
- `build_external_query_snapshot(query_df)`：从外部查询文件构造

该层的语义是：

- `app_dt`：截至哪一天回看历史
- `key_type`：按哪种主键视角查询
- `key_value`：该主键视角对应的标准值

当前支持的主键类型有三种：

- `pid_id`
- `pid`
- `id`

对应规则：

- `pid_id`：需要 `PID` 和 `ID` 同时存在，`key_value = PID|ID`
- `pid`：只按 `PID` 查询，输出时 `ID` 置空
- `id`：只按 `ID` 查询，输出时 `PID` 置空

这层本质上定义了整个项目对“查询对象”的统一协议。

### 5.3 event_fact

来源函数：`build_default_event_key_fact(df)`，位于 `src/acct_rz/events.py`。

它的构造方式是：

1. 基于 `application_base`
2. 过滤出 `is_default == 1`
3. 按合法 key 类型展开成多视角事件记录

其核心字段包括：

- `PID`
- `ID`
- `key_type`
- `key_value`
- `event_dt`

在部分 step 中还会继续使用：

- `Org_class_new`
- `perf_type`

这张表的业务语义是：

- 谁在什么时间形成过违约事件
- 这些违约事件可以从哪些主键视角被命中

维护时应把这层视为共享事实源。step1-step4 不应再分别回到原始 `y.csv` 重复做违约解释。

### 5.4 step outputs

系统在 `query_snapshot + event_fact` 的基础上产生 4 类输出：

- `step1_blacklist`
- `step2_traceback`
- `step3_org_blacklist`
- `step4_window_counts`

它们共享统一的主键前缀字段，并在其上叠加各自的聚合结果。

## 6. 模块职责说明

### 6.1 `normalize.py`

核心函数：`build_application_base(df)`

职责：

- 原始输入标准化
- 违约规则落地
- `event_dt` 推导

维护重点：

- 违约口径调整应优先修改这里
- 原始日期、空值、类型兼容问题应集中在这里处理

### 6.2 `keys.py`

核心常量与函数：

- `BASE_KEY_COLUMNS`
- `VALID_KEY_TYPES`
- `expand_all_key_types`
- `build_selected_key_snapshot`
- `build_history_query_snapshot`

职责：

- 清洗 `PID`、`ID`
- 规范 `key_type`
- 构造 `key_value`
- 输出统一 key 快照结构

维护重点：

- 它是 batch/query 共用的协议层
- 新增 key 类型时，应先改这里，再检查所有下游 join 与测试

### 6.3 `query_snapshot.py`

核心函数：`build_external_query_snapshot(query_df)`

职责：

- 处理外部 `query.csv`
- 解析 `app_dt`
- 自动推断或校验 `key_type`
- 拒绝非法 query 行
- 输出标准查询快照

维护重点：

- 这是 query 模式的输入校验防线
- 外部输入格式扩展优先改这里，而不是改 `query_lookup.py`

### 6.4 `events.py`

核心函数：`build_default_event_key_fact(df)`

职责：

- 从标准申请层筛选违约事件
- 将违约事件按 key 类型展开

维护重点：

- 这是共享事实表，不应混入具体 step 的聚合逻辑

### 6.5 `lookup_base.py`

核心函数：

- `with_matched_event_dt`
- `resolve_query_snapshot_and_event_fact`
- `format_final_date_columns`

职责：

- 统一事件匹配时间语义
- 统一兼容两类入参模式
- 统一外部日期输出格式

维护重点：

- 这是跨 step 的公共规则层，任何修改都会影响多个输出

### 6.6 `features_blacklist.py`

核心函数：

- `_lookup_blacklist_features`
- `lookup_step1`
- `lookup_step2`

职责：

- 输出 step1 基础黑名单命中结果
- 输出 step2 traceback 增强结果

维护重点：

- step1 和 step2 共用一套聚合逻辑
- 黑名单口径变更时，应优先改共享聚合函数

### 6.7 `features_org_blacklist.py`

核心函数：`lookup_step3(...)`

职责：

- 将 blacklist 逻辑扩展到 `org_class` 维度
- 输出 long form 机构维度结果

维护重点：

- 当前只支持 `output_format="long"`
- 如果未来支持 wide 输出，建议新增转换层，而不是破坏现有 long 逻辑

### 6.8 `features_windows.py`

核心函数：`lookup_step4(...)`

职责：

- 计算近 3/6/12 月违约次数
- 计算按机构类别、违约类型拆分的部分窗口统计

维护重点：

- 时间窗口边界是最容易出错的区域
- 未命中主键时返回 0 值也是该模块的重要契约之一

### 6.9 `query_lookup.py`

核心函数：`lookup_all_steps(history_df, query_df, step3_format="long")`

职责：

- 作为 query 模式的编排层
- 生成 query snapshot 与 event fact
- 聚合四个 step 并返回字典结果

维护重点：

- 这是服务装配层，不应堆积底层业务细节

### 6.10 `pipeline.py`

核心函数：`run_demo_pipeline(input_path, out_dir)`

职责：

- 作为 batch 模式的编排层
- 构建历史 query snapshot
- 生成四类批量输出

维护重点：

- 当前偏轻量 orchestration 风格
- 若未来扩展批处理配置，优先在这里加参数和分支

## 7. 业务规则与查询语义

### 7.1 违约认定规则

当前规则集中在 `normalize.py`：

- 仅 `target == 1` 认定为违约
- 其余 `target` 一律视为非违约
- `mob` 缺失或非法时默认补为 `6`
- 违约生效时间取 `event_dt`，而不是原始 `app_dt`

这说明系统当前采用的是“申请之后若干月形成违约事件”的业务口径。

### 7.2 查询主键语义

系统支持三种 key 视角：

- `pid_id`
- `pid`
- `id`

同一条历史违约记录可能从多个视角被命中。这是当前系统的重要设计取舍，它让查询能力更灵活，但也意味着事件数与命中结果会随 key 视角变化。

### 7.3 时间匹配语义

所有 step 的命中都带时间约束，不是简单 key join。

统一规则是：

- 先按 `key_type + key_value` 匹配
- 再要求 `event_dt <= app_dt`

因此本系统是“截至查询日的历史回看”系统，不允许未来事件回流到过去的查询日。

### 7.4 Step1 与 Step2

`step1` 关注两个问题：

- 是否命中过违约
- 首次违约日期

`step2` 在此基础上继续提供：

- 最近违约日期
- 截至查询日累计命中次数

可以把它们理解为：

- `step1`：简化黑名单标签
- `step2`：带追溯信息的黑名单摘要

### 7.5 Step3

`step3` 将 blacklist 逻辑扩展到 `Org_class_new` 维度。

它回答的是：

- 在哪些机构类别上出现过违约
- 各机构类别的首次违约日期是什么

当前输出是 long form，因此更适合后续分析、透视和二次加工。

### 7.6 Step4

`step4` 用于衡量查询日前的违约活跃度，输出：

- 总体近 3/6/12 月违约次数
- 近 3/6 月的部分机构类别计数
- 近 3 月的部分 `perf_type` 计数

它强调的是“最近一段时间的风险强度”，而不是单纯“是否命中过”。

## 8. 输入输出契约

### 8.1 外部 Query 输入约束

`build_external_query_snapshot` 当前要求：

- 必须存在 `app_dt`
- `PID`、`ID` 至少要能构成一个合法 key
- `key_type` 可省略，省略时自动推断
- 若显式给出 `key_type`，必须属于受支持集合
- `app_dt` 支持 `YYYYMMDD`、`YYYY-MM-DD` 及可直接转日期的形式

不满足约束时直接抛出 `ValueError`，而不是静默跳过。

### 8.2 输出字段约束

四个 step 的最终输出都保留以下公共字段：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

其他字段由具体 step 决定。

### 8.3 日期序列化约束

`lookup_base.format_final_date_columns` 会将所有 `pl.Date` 列统一转换为：

- `YYYYMMDD`
- `Int64`

这使得外部 parquet 输出具备稳定、简单的消费接口。

## 9. 当前测试覆盖

当前 `tests/` 已覆盖以下关键层面：

- 包结构和 README
- 原始申请标准化
- key 展开与 key snapshot 协议
- 违约事件事实表
- step2、step3、step4 的核心聚合逻辑
- 外部 query snapshot 输入校验
- 统一查询入口
- batch pipeline 与 CLI 基础流程

从维护角度看，当前测试不是只有 smoke test，而是已经围绕关键中间协议和近期回归问题搭起了基本保护网。

## 10. 当前测试缺口与架构风险

目前仍有几个较明显的空白点：

- 缺少“`query.csv` 主键在 `y.csv` 中完全查不到”时的完整 query 链路集成测试
- `step1` 对未命中主键的返回契约没有专门测试
- `step2`、`step3` 对未命中场景的行为缺少单独断言
- 时间边界语义，例如“恰好位于窗口边界日”，缺少专门测试
- `step3` 只支持 `long` 输出，但尚无更系统的扩展说明

这些缺口不意味着当前实现错误，但意味着后续改动这些区域时，回归风险相对更高。

## 11. 当前架构优点

- 分层清晰，标准化、key 协议、事实表、聚合层、编排层职责较明确
- `batch` 与 `query` 共用同一套特征计算骨架，复用度高
- 对输入校验和日期输出格式有集中控制点
- 代码量不大，适合快速定位和定向改造
- 测试已覆盖数值日期解析、未命中 key 的部分场景和 CLI 基础行为

## 12. 当前架构限制

- `pipeline.py` 仍带有 demo 风格，参数能力有限
- `step3` 只支持 long 输出
- 业务规则仍主要写死在代码中，尚未配置化
- 各模块依赖 DataFrame 字段契约协作，没有显式 schema 类型层
- 项目当前更接近轻量分析管线，而不是严格分层的服务化系统

## 13. 维护建议

### 13.1 改业务规则时先找对位置

- 改违约认定规则，先看 `normalize.py`
- 改 key 语义，先看 `keys.py`
- 改 query 输入校验，先看 `query_snapshot.py`
- 改公共时间匹配或日期输出规则，先看 `lookup_base.py`

不要在某个 step 模块里直接打局部补丁来绕过上游中间层。

### 13.2 保持共享中间层稳定

未来若新增 step，建议继续复用：

- `query_snapshot`
- `event_fact`

这样可以维持 batch/query 两条链路的统一性。

### 13.3 新增 key 类型时的检查清单

若未来新增第 4 种 key 类型，至少需要同步审查：

- `keys.py`
- `query_snapshot.py`
- `events.py`
- 各 `features_*` 模块中的 join 逻辑
- 所有相关测试

### 13.4 补测试的优先顺序

如果继续增强项目稳健性，优先建议补以下场景：

1. query 模式下，外部主键完全查不到历史记录
2. step1/step2/step3 在未命中主键时的行为
3. 时间窗口边界日
4. step3 格式扩展的契约测试

## 14. 维护者快速心智模型

如果只用一句话概括当前项目：

这个项目先把历史申请数据翻译成“标准申请层”和“违约事件事实层”，再围绕统一的查询主键快照，在指定查询日上计算 4 类风险结果。

如果只记住两条维护原则：

- 先理解 `query_snapshot` 和 `event_fact`，再看四个 step
- 改规则优先改中间层，不要直接在输出层硬改

## 15. 代码入口索引

- CLI 入口：`run_pipeline.py`
- batch 编排：`src/acct_rz/pipeline.py`
- query 编排：`src/acct_rz/query_lookup.py`
- 标准化层：`src/acct_rz/normalize.py`
- key 协议层：`src/acct_rz/keys.py`
- query 输入层：`src/acct_rz/query_snapshot.py`
- 事件事实层：`src/acct_rz/events.py`
- 公共查询辅助：`src/acct_rz/lookup_base.py`
- step1/2：`src/acct_rz/features_blacklist.py`
- step3：`src/acct_rz/features_org_blacklist.py`
- step4：`src/acct_rz/features_windows.py`
