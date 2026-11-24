# 数字资产交易服务受限下的用户资产处置能力
## William Chou · 投稿修订版复现资料

这份资料覆盖生产前端取证、129 个名单地址的主网 v3 全量筛查、前后各 7 日与 14 日比较、同钱包收付轨迹、最低到账归档对照及逐价格步费用复算。编码使用 UTF-8。CSV 带 UTF-8 BOM。使用电子表格时请将地址、哈希和 wei 整数列按文本导入。

## 1　离线复算

需要 Python 3.10 以上。链上复算程序仅用标准库，无需网络、API 密钥和私钥。

```sh
python reproduce_all.py --out verification
diff -r derived verification
```

GNU/Linux 上可在运行前执行 `sha256sum -c SHA256SUMS.txt`。归档的 `.json.gz` 可直接由 Python 读取，解压工具也能打开。原文件是相应 JSON-RPC 方法的 `result`，回放文件同时保存方法、参数和协议响应。日志以 UTC 为准，金额以 wei 或合约的最小计量单位为准。末位不可用二进制浮点复算。

### 期望结果

| 指标 | 核对值 |
|---|---:|
| 固定名单主网地址 | 129 |
| Factory 建池日志 | 3,739 |
| 匹配名单资产／池 | 6／7 |
| 前后各 14 日有 Swap 的名单资产 | 1（sETH） |
| 28 个观察日内的 Swap 日志／去重成交 | 16／15 |
| 前 7／前 14 日 Swap 日志 | 6／10 |
| 后 7／后 14 日 Swap 日志 | 6／6 |
| 后 7／后 14 日严格 0x 卖出 | 2／2（同两笔） |
| 收付闭环归档实验 | 3 个历史样本、105 个参数点、210 次节点调用 |
| 每笔成功与回滚阈值之差 | 1 wei |
| 样本 A 与 B 池费／合计可观测成本 | 0.000281300000000002／0.000207700000000001 sETH；116.25337／149.32312 bps |
| 生产部署记录时间 | 2021-07-23 22:05:20 UTC |
| 官方发布声明时间 | 2021-07-23 22:18:20 UTC |
| 生产域名实际生效时点 | 证据不足，见 `deployment_summary.json` |

## 2　在线独立重取

以当前目录作为解压后的复现包根目录。选择一个空的输出目录即可重新获取全部交易、回执和历史状态。

```sh
python census.py --collect --raw refreshed/census --out refreshed/derived
python thresholds.py --collect --census-raw refreshed/census   --raw refreshed/thresholds --out refreshed/derived
python deployment.py --raw raw/deployment --census refreshed/census --out refreshed/derived
diff -r derived refreshed/derived
```

默认以 Tenderly 与 Alchemy 对照 Factory 与 Swap，Tenderly 与 dRPC 对照回执，调用轨迹由 dRPC 提供。门槛实验及逐价格步复算状态由 Tenderly 与 dRPC 交叉核对。可设置：

- `RESEARCH_PRIMARY_RPC`：以太坊主网归档 RPC，提供 `eth_chainId`、`eth_getBlockByNumber`、`eth_getLogs`、`eth_getTransactionByHash`、`eth_getTransactionReceipt` 与历史 `eth_call`。
- `RESEARCH_SECONDARY_RPC`：第二个主网节点，提供早期主网日志和多地址筛选。
- `RESEARCH_TRACE_RPC`：主网归档 RPC，提供 `trace_transaction`、历史 `eth_call`、`eth_getCode`、回执和日志。

公开节点限流时可用 `--workers 2` 降低并发。程序遇到无效节点响应即停止，不将错误填充为零。遇到请求范围限制，自动分割区块再核验。历史调用须返回原始 ABI 回滚数据。离线方式独立于节点状态，只依赖资料包。若重新获取同源公共元数据，部署状态可能随时间变化，引用以包中冻结 JSON 为准。

## 3　原始数据与选择规则

- `baseline/raw/` 保存 2021 年固定名单、前一版本本地名单、主机名和规则源码、固定版本池代码、Mt.Gox 公告，以及上一版 7 日实验的原始快照。`baseline/reproduce.py` 是旧口径核验程序。
- `raw/census/` 保存两个节点的全部 3,739 条 Factory 日志、两家节点按周段和池地址查询的 Swap、UTC 边界与相邻区块、15 笔交易和双源回执、3 条调用轨迹及发送地址历史代码。
- `raw/deployment/` 保存 GitHub PR、部署记录和状态、官方消息结构化存档、2021-08-06 名单和网页存档索引。HTTP 失败日志记录本次检索所能达到的证据边界。
- `raw/thresholds/` 保存历史价格、tick 数据与池日志的双节点快照，以及每个数额在两家节点的完整调用输入和响应。
- `derived/` 保存池名单、各代币各窗口的覆盖表、每条 Swap、去重交易、严格收付闭环、逐价格步池费、门槛网格和结构化汇总。
- `sources.csv` 列出主要来源和包内文件入口。`manuscript/` 含论文、图和四页课堂展示的源文件。

链 ID 限定为 1。按 Factory 事件筛查任一代币端，不按符号配对。7 日窗嵌套于 14 日窗，两个方向不跨越 7 月 23 日事件日。两个节点输出按区块哈希、交易哈希、日志索引、合约、主题与 ABI 数据逐条核对。7 个池全部保留，包括无成交池。0x 只是严格规则的目标路由，其他调用即便实际成交也留在总体池日志和去重表内。前后 28 个观察日共有 15 笔去重成交，其中 3 笔符合严格规则。后窗一笔交易包含两个 Swap 加上其他池活动，净转账无法由 Swap 事件单独解释，故计入成交但未计入池净额一致的日志。

扩展窗内的 8 月 6 日提交新增一个地址，保留原 129 个地址。新增地址也在完整 Factory 日志中核查，仍无匹配池。该口径变化不影响窗口结果。

## 4　归档复算和成本定义

`thresholds.py` 保持发送者、路由、路径、输入量、Gas 及历史区块固定，只改变最低到账金额。每个历史样本取 35 个去重整数门槛。双节点基准成功值与历史到账 Q 完全一致，门槛为 Q + 1 wei 即触发确定的最小到账约束。没有签名和提交交易，模拟失败与真实成交样本分开。

用历史流动性和已初始化 tick 逐步复算 v3 的净输入、舍入后池费、输出、终止价格与流动性。成本分解用同一个基准，即输入量乘交易前池内边际价格。池费折算、其余成交偏离和本笔 Gas 的和是合计成本。Gas 占实收的百分比另列。授权费用、放弃成本和用户看到的前端报价未在此数据中观测。

## 5　生产证据识别

2021-07-23 22:05:14 UTC 的提交可定位规则。22:05:20 的 GitHub 记录证明 Vercel 机器人为同一 SHA 创建了环境名称为 Production 的部署任务。22:18:20 的官方消息为运营方当时的声明。Wayback 的 2021-07-24 06:36:00 索引早于第一次后窗成交 12 分 34 秒，实际页面脚本未被此次检验恢复。公开状态只显示后来 inactive 且无环境 URL。PR 成功部署的是 Preview，不能据此认定官方生产域名生效。统计窗口锚定公告日。

## 6　重新编排文件

正式论文未指定目标期刊模板，采用通用 A4 学术体例和 GB/T 7714—2025 顺序编码引文。作者为William Chou。展示 PPTX 的备注区提供 3、4、5、3 分钟讲述节奏。

```sh
python -m pip install -r requirements-layout.txt
python manuscript/draw_figures.py
python manuscript/build_docx.py --output rebuilt.docx
python manuscript/build_slides.py --output rebuilt_slides.pptx
soffice --headless --convert-to pdf rebuilt.docx rebuilt_slides.pptx
```

生成件使用 Noto CJK 和 Liberation 字体。图脚本默认 Linux Noto 字体路径。其他系统可修改字体路径，或直接使用资料包中的 PNG。
