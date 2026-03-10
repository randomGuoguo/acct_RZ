# acct_RZ

面向 Ydata 历史违约事件的离线特征与查询项目。

当前项目状态与交接说明：

`docs/plans/2026-03-10-ydata-query-lookup-status.md`

## 测试命令

运行全量测试：

`conda run -n dl_new python -m pytest -q`

## 离线批处理

默认生成离线结果：

`conda run -n dl_new python run_pipeline.py`

指定输入输出路径：

`conda run -n dl_new python run_pipeline.py --input data/demo/y.csv --output data/result`

核心实现文件：

`src/acct_rz/pipeline.py`

核心函数：

`run_demo_pipeline`

## 查询模式

Python 入口：

`lookup_all_steps`

模块位置：

`src/acct_rz/query_lookup.py`

查询输入必需字段：

- `app_dt`
- `PID` 或 `ID` 至少一个非空
- `key_type` 可选，取值为 `pid`、`id`、`pid_id`

查询模式示例：

`conda run -n dl_new python run_pipeline.py --mode query --input data/demo/y.csv --query-input data/demo/query.csv --output data/result`

## 输出约定

所有 step 输出都保留以下列：

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

所有最终输出中的日期列统一序列化为 `YYYYMMDD` 形式的 `i64`。

如需查看最新可运行状态、回归结果与后续接续说明，请优先阅读：

`docs/plans/2026-03-10-ydata-query-lookup-status.md`
