# 数字资产交易服务受限下的用户资产处置能力
## Mt.Gox 与 Uniswap v3 的条件式机制检验 · William Chou

从压缩包顶层打开论文或技术附录。两者均提供可编辑 Word 和已排版 PDF。本目录包含研究源文件。主文、附录和复算数据均为同一修订版本。

### 复现正文的数值

解压本研究包并在本文件所在目录运行。Python 3.10 或以上即可；本次验证环境为 CPython 3.12.14，核心计算全部使用标准库。

```sh
python verify.py
```

该命令逐文件核验 SHA-256，重算历史建池普查、每条 Swap、门槛、tick 成本及前端证据，再重算本次新增的持仓、市场价差、路径净得、全额报价与费用预算。三组输出分别与 `evidence/derived/`、`derived/` 和 `additions/derived/` 逐字节比较。其中第三组覆盖名单全窗、两个钱包回滚、市场敏感性、管财人偿付条款与进度及治理回执。最后使用独立的原始字段读取及 SQLite 检查主要结果。运行会创建临时输出目录，不写入冻结的原始数据。请保留 Python 默认断言，不要加 -O。最后一行应为 `Offline reproduction passed; historical and new output directories match byte for byte.`。这里的独立检查指不同计算程序，没有第二位审稿人参与。

若需观察某一步的输出，运行以下命令。
```sh
python analyze.py --out results
python decision.py --out results
python decision.py --out results --cap 100
python audit.py
```

| 所在位置 | 内容 | 期望核对结果 |
| --- | --- | --- |
| evidence/derived/census_summary.json | 129 个主网名单地址和整段建池、成交普查 | 3,739 条 Factory 日志，6 个名单资产、7 个池，双 14 日只有 sETH 发出 Swap。16 条日志、15 笔去重，后窗 2 笔严格闭环。 |
| evidence/derived/threshold_grid.csv、swap_fee_steps.csv | 三笔历史路径的整数门槛与逐步池费 | 105 个配对门槛，210 次调用；相邻成功与回滚边界相差 1 wei。 |
| derived/holdings.csv、transfers.csv | 公告前余额、卖出前余额、双向历史日志、第一笔正额入账 | A 公告前余额为 0。B 公告前余额 415404002756450395，卖出 415400000000000000，单位均为 sETH 的最小单位。 |
| derived/gox_market.csv、summary.json | 33 个 UTC 日期、3 家市场、两个参照价差；Bitstamp 官方日线区间核对 | 各 14 日相对 Bitstamp 的日价差中位数 +17.29% 与 −39.63%。 |
| derived/counterfactuals.csv、conditions.csv | 三个历史钱包 × 五个钱包执行情景，逐条记录授权、用气、毛额和净额 | 原路径 3/3 重放与真实金额及 Gas 相等。无新增授权的 6 个替代情景回滚；加入授权的 6 个完成。失败情景毛额和净额列为空。 |
| derived/trade_quotes.csv、daily_quotes.csv | 交易前同量报价和每日固定规模比较、v3 输入消耗、等额价格缺口 | 28 日 × 4 个卖量 = 112 个价格比较单元。112 个正报价，84 个 v3 全额，28 个部分。部分输入单元价格缺口留空。 |
| derived/decision.csv | 各种费用预算下可通过的路径及最高历史模拟净到账 | 100 bp 且许可新授权时，A 有 3 条，B 有 1 条，净得最高者均为 Curve。此示例的分母是毛到账，费用含本次必要的新授权。 |
| text/ | 论文、技术附录与图表的文字和生成源 | 正文含 9 张表、3 幅图，附录列出全部 19 条评审意见及证据边界。 |

### 本轮数据、分母与复核

下列路径均相对于本目录。离线重算只用 Python 标准库。运行 `python additions/recalculate.py --out results_expanded` 可单独生成本轮结果。

| 文件 | 计量单位及用途 |
| --- | --- |
| additions/panel/list_2021.json、additions/derived/restricted_addresses.csv | 固定提交的链 ID 1 名单及完整地址，原始 JSON 和便于筛选的 129 行 CSV。 |
| additions/panel/bound_*.json.gz、additions/derived/window_totals.csv | 8 个 UTC 边界分别保存前后相邻区块头。输出每个窗口含首尾区块，均为闭区间。工厂与 Swap 日志由 Tenderly 和 Alchemy 核对；边界用 dRPC 区块头。 |
| additions/derived/address_by_window.csv | 129 × 8 × 2 行。no_pool 为截至该窗口末未建池；pool_zero 为已建池但窗内零成交；positive 为有 Swap。zero_logs=no_pool+pool_zero。池较晚建成时，仅从创建块开始计活动。 |
| additions/derived/listed_pools.csv、listed_swaps.csv | 全 61 天三场所 70 个名单池、2,773 个事件、2,718 笔交易。CSV 保存交易哈希、日志序号、区块哈希和代币净输入，正数为流入池。工厂扫描同时匹配名单资产两侧，剔除非名单的辅助检索地址。 |
| additions/raw/account_*.json、acct_receipt_*、failed_trace_*、*_nonce_* | 两个地址各自的区块浏览器原始返回、176 份回执（88 笔各由两家查询）、两笔回滚轨迹及四处边界 nonce。派生 wallet_counts.csv 与 wallet_mined_txs.csv 仅覆盖该地址的已上链外发。 |
| additions/raw/forum_topic.json、forum_evidence.json、web_index.json | 原帖完整 JSON、逐帖 UTC、摘录、请求 URL 和存档请求成败。网页索引不是资源已部署的凭证。 |
| additions/raw/plan_en.pdf、trustee_*.pdf、*.txt | 管财人文件和排版保留文本。payment_bounds.csv 给累计下界；schedule_rates.csv 给计划条款下的五档日元算例。没有个人实际到账底册。 |
| additions/raw/*_price.csv.gz、*_volume.csv.gz、fx_usd_eur.csv | Bitcoinity 价格、以 BTC 计的每日成交量、ECB 每欧元美元数。另三家美元价格在 raw/。market_by_day.csv 和 market_sensitivity.csv 可重新计算所有窗口、分母、权重和 FX 配对。 |
| additions/raw/gov_receipt_*、owner_logs_*、fee_logs_*、gov_owner_* | 完整治理执行回执、变更事件、空数组原始返回和历史 owner() 结果。 |
| additions/derived/ | 本轮数值输出；其中金额最小单位或超长整数宜以文本导入电子表格。SHA256SUMS.txt 覆盖全部随附研究文件。 |

三家服务名称代表访问端点。尚无自托管归档节点，多个端点可能共享数据来源。链上扩样的 25 个活跃资产只证明相应池有过交换。严格的“事前持有—事后实际卖出—原钱包收到 ETH”仍是 B 一例。完整 mempool、未广播和放弃行为不在冻结数据内。

### 在线重新采集本轮扩展

在本研究目录运行下列命令。按需将供应商接口改为具备历史能力的地址。在线服务可能追加数据、限流或修改返回元数据。若重新取样，应比较研究区间和字段，保留冻结版本。

```sh
mkdir -p fresh_review/panel fresh_review/raw
cp additions/panel/list_2021.json additions/panel/mirror_20210712.json fresh_review/panel/
python additions/panel_methods.py --collect --only-logs --raw fresh_review/panel
python additions/collect_web.py --out fresh_review/raw
python additions/extract_documents.py --raw fresh_review/raw
python additions/collect_chain.py --out fresh_review/raw
python additions/recalculate.py --raw fresh_review/raw --panel fresh_review/panel --out fresh_review/results
```

名单已固定为原始提交的历史快照，可直接和正文引用的 Git 版本对照。panel_methods.py 的日志端点可由 JOURNAL_RPC_A、JOURNAL_RPC_B 指定，端点 T 用于边界搜索；collect_chain.py 的端点取 TENDERLY_RPC、DRPC_RPC 和 ALCHEMY_RPC。collect_web.py 记录各下载的结果；缺必要原件时后续程序停止。提取管财人 PDF 的命令需要 Poppler 的 pdftotext，离线校验直接使用包内已经提取的文本。历史回放的 eth_call、trace_call、eth_simulateV1 完整参数均在下面的冻结路径中。

### 输入与在线重取

- `evidence/baseline/raw` 包含 2021 年历史名单、前一版本、主机名逻辑、池源码、账户交易与回执、真实付款轨迹及 Mt.Gox 程序文件。`evidence/raw/{census,deployment,thresholds}` 包含双源扫描、部署元数据、逐门槛请求及价格步状态，文件命名与 `evidence/sources.csv` 对应。
- `raw/*history*` 与 `raw/*balance*` 分别是自创世到卖出块、按地址过滤的 Transfer 查找和 balanceOf。样本截止块按 UTC 确定；sETH 相关状态量使用 18 位整数。原地址曾经收币与该次实际卖出来自公告前余额，分别编码。
- `raw/*sim*` 保存 eth_simulateV1 的完整输入与返回。用原 Gas 单价，不覆盖账户授权或余额。新增授权按同一合成块中的第一笔独立调用执行并单独收取 Gas。traceTransfers 合成原生资产移动日志；旧样本的真实链上轨迹独立存放。报价基准由历史区块具体指定，未回放其他候选真实交易，没有排队或等待成本。
- `raw/utc*` 保存每日首块和父块的核验字段。`raw/quotes*` 保存报价请求及返回。`raw/fills*` 保存 v3 Quoter 的 trace_call 调用树，核验回调实际输入和输出。Quoter 在内部回滚以传回报价是其正常机制，合成测试中的单笔用户交易回滚另行标注。`raw/*csv.gz` 为 Bitcoinity 的按交易所导出；`bitstamp_ohlc.json` 用于检查均价落于官方日内区间。价格资料是历史聚合数据，不具备逐客户归属。
- `raw/swap_page.tsx`、`tokens_hooks.ts`、`useIsSwapUnsupported.ts` 与上述名单钩子共同识别禁用按钮。Solidity、Vyper 和法院文件提供制度、实现与行为旁证。`sources.py` 列完整来源 URL，正文所引公开链接保存在 `text/paper.md` 和 `文献与数据来源.csv`。

在线复取使用空目录，不覆盖冻结数据。来源网址变化、公共 RPC 限流或历史能力被移除时，可直接离线复核。
```sh
python sources.py --raw fresh
python protocol.py --raw fresh
python routes.py --raw fresh
python grid.py --raw fresh
python fills.py --raw fresh
python analyze.py --raw fresh --out new_results
python decision.py --out new_results
```
提供方使用 Tenderly、Alchemy 及 dRPC，可设置 TENDERLY_RPC、ALCHEMY_RPC、DRPC_RPC 指向具备相应能力的主网归档服务。protocol.py 需 eth_getLogs、历史 eth_call 和区块头；routes.py 需支持含 traceTransfers 的 eth_simulateV1；fills.py 需 trace_call。grid.py 对首块猜测用 DefiLlama 的公开时间戳接口，随后用相邻实际区块头校验 UTC 边界；接口不可达时会使用近似高度再搜索。Bitcoinity 原始导出可能随时间追加新日期，在线复算比较派生研究窗口即可。重新获取旧 129 地址部分可运行以下命令。
```sh
python evidence/census.py --collect --raw fresh_base/census --out fresh_base/results
python evidence/thresholds.py --collect --census-raw fresh_base/census --raw fresh_base/thresholds --out fresh_base/results
python evidence/deployment.py --raw evidence/raw/deployment --census fresh_base/census --out fresh_base/results
```

### 图文重排

分析代码和下载文件均可在没有 Word 的机器上使用。重建论文和图另需 python-docx 1.2.0、Matplotlib 3.10.8、Pillow 13.0.0，以及 Noto Serif/Sans CJK SC 和 Liberation 字体；图脚本的 Linux 字体路径可按安装位置修改。
```sh
python text/plot.py
python text/build_docx.py --source text/paper.md --output paper.docx
python text/build_docx.py --source text/technical.md --output appendix.docx
soffice --headless --convert-to pdf paper.docx appendix.docx
```

稿件未指定新的目标期刊，排版采用 A4、连续页码、顺序编码引文和双语摘要。AI 辅助了数据采集、计算核验、图表和文字修订；署名人应在拟投稿时核对署名和目标期刊的披露条件。
