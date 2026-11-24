# 数字资产交易服务受限下的用户资产处置能力
## 基于 Mt.Gox 与 Uniswap v3 的案例比较和链上复核

@author 周家乐

@lead 摘要｜交易服务受限后，用户能否处置原有资产，取决于指定操作所需的权限以及替代路径。本文以 Mt.Gox 暂停 BTC 提现和 Uniswap Labs 公告限制网页访问为机制对照。首先，追溯 2021 年 7 月限制名单、生产部署记录及网页存档索引，定位代码提交、部署任务创建和官方声明的时间，保留官方域名实际生效时点的识别边界。其次，按 129 个名单地址筛查以太坊主网 3,739 条 Uniswap v3 建池记录，获得涉及 6 个名单资产的 7 个池。剔除公告日后的前后各 14 个完整 UTC 日内，仅 sETH 池出现成交，共 16 条交换日志、15 笔去重交易。公告后两笔交易经 0x 卖出 sETH 并把原生 ETH 付回原发送地址，前后各 7 日与各 14 日口径得出相同的公告后闭环集合。对含公告前对照在内的三笔交易进行 105 组参数设定、210 次双节点归档调用，最低到账额从实际可得值提高 1 wei 即由成功变为回滚。逐价格步复算池费，并把池费、其余成交价格偏离和网络费按同一基准分解。结果支持特定条件下替代交易的可完成性。已成交日志不覆盖未广播或失败尝试，结论限于样本资产、执行路径及历史状态。

@key 关键词｜数字资产；资产处置能力；托管依赖；网页访问限制；链上复现

@en Users’ Ability to Dispose of Digital Assets under Trading-Service Restrictions
@enauthor Jiale Zhou

@lead Abstract｜This study compares Mt.Gox’s BTC withdrawal suspension with Uniswap Labs’ restriction on token access through its web interface. We reconstruct the announcement, the repository commit, the creation of a production deployment record and the timing of a web archive index. The available evidence leaves the exact activation time on the official domain unidentified. We screen 3,739 Ethereum Uniswap v3 pool creation records for all 129 addresses in the pinned list. Seven pools match six listed assets. Across the two fourteen-day windows, sETH is the only listed asset with observed swaps. The 16 swap logs correspond to 15 unique transactions. Two post-announcement sales through 0x transfer sETH out of the original sending accounts and return native ETH to those accounts. Both sales remain in the seven- and fourteen-day post-announcement samples. For three historically executed sales, 210 archival calls at 105 parameter settings show a one-wei boundary between successful execution and reversion at the minimum-output threshold. We reconstruct the pool fee at each price step and separately account for execution deviation and gas. The results establish realized alternative execution under the observed conditions. They do not identify population-level completion rates or the causal cost of the web restriction.

@key Keywords｜digital assets; asset disposability; custody dependence; web interface restriction; on-chain replication

# 1 研究问题

2014 年 2 月 7 日，Mt.Gox 暂停 BTC 提现，场内交易一度继续［1］。2021 年 7 月 23 日，Uniswap Labs 宣布限制其官方网页对部分代币的访问［2］。两项事件触及不同的操作。在第一种情形中，用户欲把原托管账户中的 BTC 提至自控地址；在第二种情形中，用户欲用原钱包里的指定代币换得可支配资产。本文考察用户能否在原服务受限后完成该操作，以及执行依赖何种权限。

Hägele 将托管、市场流动性和交易功能纳入交易场所比较［3］。Schär 区分结算、资产、协议和应用入口［4］。Hirschman 对退出的讨论则提示了替代选项的价值取决于退出者能实际带走什么［5］。据此，本文将比较落在原有资产的可执行操作上。Mt.Gox 用来识别托管出币依赖，Uniswap 用来核验界面限制公告后是否存在同资产的真实结算。两案的法域、技术、时间与经营状态不对称，比较的单位是必要权限与替代路径。

本文推进三项验证。第一，将政策声明、构建部署记录和生产域名实际生效分开识别。第二，先穷举固定历史名单与主网 v3 池的交集，再对成交回执和资产终点逐级核验。第三，在历史状态上用参数网格检验交易的精确可执行边界，并分解实际成交成本。

# 2 观察单位与证据规则

处置能力的观察单位为「原资产、指定操作、时点、受限服务」。账户内权益必须能对应至原托管账户。链上原资产以链 ID 和合约地址识别。以卖出 sETH 为例，单有代币获准转移或池事件只回答局部问题，完成处置要求可验证的原钱包扣款、成交和可支配对价到账。

@caption 表 1　处置能力的三层证据
| 层级 | 待检验问题 | 所需证据 |
|---|---|---|
| A 可调用 | 哪个环节受限，其他执行者能否进入协议？ | 历史政策、固定代码、部署记录和池创建事件。 |
| B 可完成 | 原资产的指定操作是否真正执行？ | 回执、受限合约的转账、池交换和最终收款必须匹配。 |
| C 成本可承担 | 用户能否以可接受的成本完成？ | 逐笔量化链上成本。估计用户层结果还需尝试分母、授权和行为资料。 |

链上证据采用三个累进判别。Swap 及其回执用于认定池内活动。若池在同一交易内的两个代币净转移等于 Swap 事件净额，则记录为池级对账一致。严格闭环在此基础上要求识别第三方执行合约、钱包付款以及最终原生资产收款。池级对账的统计单位是日志，严格闭环的统计单位是去重后的交易哈希。用户尝试、成功上链交易和池内交易腿分别计量。

# 3 Mt.Gox 的提现权限

2014 年 2 月 7 日 BTC 提现暂停时，Mt.Gox 客户仍可在场内成交一段时间［1］。发行人向 SEC 提交的材料记载了操作的时间差，Mt.Gox 随后的公司公告则记录网站关闭、资产缺口调查和法院保全［6］。场内成交改变内部账户记录。外部提现要求持有托管地址控制权的一方发起链上转出，客户无法用自己的钱包签名完成该步骤。在其他市场新买入 BTC 也不会释放原账户权益。

2014 年 2 月 28 日公司公告宣布提出民事再生申请［6］。此后经历破产程序。东京地方法院于 2018 年 6 月 22 日裁定启动新的民事再生程序，公告于 2018 年 10 月 26 日更新［7］。经法院许可，管财人于 2026 年 10 月 16 日将相关偿付期限延至 2027 年 10 月 31 日。公告同时指出，对于已完成手续且付款无障碍的相关债权人，若干类偿付大体完成［8］。在这一过程中原资产获取依赖债权确认和程序安排。该案识别的是日常提现中的控制依赖，无法提供 Uniswap 案例的同质反事实。

@figure mechanism.png
@caption 图 1　同资产原定操作中的限制位置
@note Mt.Gox 限制发生于平台链上出币。Uniswap Labs 公告所指限制发生于官方网页入口，图中的 0x 路径为本研究复核的链上执行路径。资料来源为公开公告、代码与交易回执。

# 4 网页限制与部署证据

## 4.1 公告、名单与生产部署记录

Uniswap Labs 于 2021 年 7 月 23 日公布网页限制。公告链接指向界面仓库的禁用名单［2］。当天 22:05:14 UTC 的固定提交将 129 个主网代币地址列入本地名单，sETH 合约为 0x5e74C9036fb86BD7eCdcb084a0673EFc32eA31cb，精度为 18。父提交旧本地名单有 3 个地址，未列入 sETH。代码在主机名为 app.uniswap.org 时使用该本地名单。JSON 内部时间字段沿用旧值，研究以 Git 提交时间界定代码版本［9］。

同一提交在 22:05:15 合并，Vercel 机器人于 22:05:20 为其在 GitHub 建立编号 397083627 的部署记录，环境名称标作 Production［10-11］。该条目的 production_environment 字段为 false，公开状态接口仅返回 2022 年 11 月 30 日的 inactive 记录，且环境 URL 为空。GitHub 可分别记录部署创建与状态［12］。PR 所显示的 branch preview 属预览环境，不能确认官方域名所服务的构建。官方账号于 22:18:20 UTC 发布消息，声明已开始在 app.uniswap.org 限制若干代币［13］。

## 4.2 网页存档与推论上限

Internet Archive 的可用性接口返回官方域名首页于 7 月 24 日 06:36:00 的索引，早于第一笔样本 12 分 34 秒［14］。本次取证的历史页面回放未返回可核验的 HTML 或对应脚本。Arquivo.pt 的查询在所查日期只返回公告前两条首页记录［15］。因此，能确立的是首笔样本之前已合并名单、创建生产部署任务，并由官方对外声明已开始限制。官方域名实际切换秒点、地区覆盖和账户遭拒的时点仍无法从这些证据识别。

@caption 表 2　限制事件与链上成交的时间证据（UTC）
| 时间 | 可核验记录 | 证据边界 |
|---|---|---|
| 7 月 23 日 22:05:14–15 | 固定名单提交与 PR 合并 | 可定位 sETH 地址及主机名规则。 |
| 7 月 23 日 22:05:20 | Vercel 创建 Production 部署记录 | 现存状态未提供官方域名成功激活时间。 |
| 7 月 23 日 22:18:20 | 官方账号声明限制已开始 | 属运营方当时公开陈述。 |
| 7 月 24 日 06:36:00 | 官方域名首页历史存档索引 | 未取得可验证版本的历史脚本。 |
| 7 月 24 日 06:48:34 | 首笔后窗 sETH 闭环卖出 | 距官方声明 8 小时 30 分 14 秒。 |

本文将后窗定义在公告日之后，而不把统计窗口解释为精确的生产部署断点。即使生产域名生效时间未能复原，后窗交易仍直接回答一项较窄的问题，即官方声明和名单合并后，同合约代币是否经独立路径实际完成交换。

# 5 全名单筛查与交易核验

## 5.1 样本覆盖与选择规则

样本从名单中所有 129 个主网地址开始。用官方主网 Factory 地址和 PoolCreated 事件扫描区块 12,369,621 至 12,974,517，无论名单代币是 token0 或 token1 均纳入［16-17］。以部署相邻区块代码验证起点。Tenderly 与 Alchemy 返回的 3,739 条建池日志在区块哈希、交易哈希、日志序号、主题及数据上逐项一致。匹配 7 个池和 6 个名单资产，分别为 sETH、sEUR、sXAG、MMSFT、MQQQ 和 MTSLA。另 123 个名单地址截至窗末未匹配主网 v3 建池记录。池计数以 Factory 事件定义，包括未产生交换的池。

事件日 7 月 23 日整日剔除。前后 7 日为 7 月 16—22 日和 7 月 24—30 日，扩展窗为 7 月 9—22 日和 7 月 24 日—8 月 6 日，均以 UTC 零时为边界。六个日期与区块端点由相邻时间戳及父区块哈希复核。14 日窗口的半开区间分别为 [12,789,855, 12,879,309) 与 [12,885,655, 12,974,518)。扩展窗内的 8 月 6 日提交保留原 129 个地址，仅新增一个名为 DYDX 的合约。将该地址加入敏感性检验，截止窗末未匹配池，故两种名单口径的成交结果一致［18］。

四个不重叠周段的全部匹配池 Swap 由两家节点核对。对每个成功交易，核验区块归属、完整回执及日志。第三个提供方 dRPC 提供独立回执和严格闭环的调用轨迹［19］。按交易哈希去重，同时保留同一交易中的多条日志。所有 16 条 Swap 都来自 sETH/WETH 的 0.05% 池。其余 6 个池在所取窗口内无 Swap。sETH 原先为探索性选取，本次对全名单的事后筛查说明它也是该固定范围内唯一活跃的名单资产。这个发现解释样本来源，并未把 sETH 变成整个市场的随机样本。

@caption 表 3　多窗口样本、对账与严格闭环
| 观察窗（UTC） | 活跃名单资产 | Swap 日志 | 去重成交 | 池级对账一致日志 | 严格 0x 卖出 |
|---|---|---|---|---|---|
| 前 7 日 | 1 | 6 | 6 | 6 | 1 |
| 后 7 日 | 1 | 6 | 5 | 4 | 2 |
| 前 14 日 | 1 | 10 | 10 | 10 | 1 |
| 后 14 日 | 1 | 6 | 5 | 4 | 2 |
@note 7 日窗是 14 日窗的子集，不能相加。后窗一笔交易包含同池两条 Swap，并有流动性和其他资金操作，池净额不能按 Swap 单独对账。该交易仍计入可观察成交。

## 5.2 第三方执行与最终收款

严格样本使用 0x 主网交易代理 Exchange Proxy 的 sellTokenForEthToUniswapV3 函数［20-21］。每笔须满足外部账户发送、原生 ETH 顶层 value 为零、同一 v3 池单腿成交、名单代币从发送账户扣款、WETH 由池付给 0x、0x 解包并把相同数额的 ETH 付给原地址。逐项核对 ABI、日志、轨迹和区块哈希。15 笔交易中，3 笔满足严格定义，另 12 笔为其他调用类型。后者属于口径外的成功交易。严格口径所用 0x 地址为 0xdef1c0ded9bec7f1a1670819833240f027b25eff，v3 池为 0xbb6642dda99c7fb1ecf310baa3477fa7ba3e7c82。

@caption 表 4　严格闭环的三笔交易
| 样本与 UTC 时间 | 区块 | 支付 sETH | 收到原生 ETH | Gas 费用（ETH） |
|---|---|---|---|---|
| 前窗　7 月 22 日 18:51:14 | 12,877,887 | 0.7612 | 0.763874225282298256 | 0.009132940 |
| A　7 月 24 日 06:48:34 | 12,887,491 | 0.5626 | 0.565085179393003844 | 0.003880870 |
| B　7 月 27 日 08:14:56 | 12,907,023 | 0.4154 | 0.416331959477254147 | 0.004567626 |

@mono 前窗｜0x52830f2aff23b7004163c3b4199ffcda38ab4cab4b7839012099cd07a1f56ea9
@mono A｜0xcf44a8e2da894ec47f52c86929fa1be3ff66724318fa19b22bc0fffc5c1c8c53
@mono B｜0x23f79ede0ae6d1aa8605d762ceafe8daccb507e8dd9e8da4bb2b96bcc299f89e

样本 A、B 的原发送地址分别为 0x2ead…f790 和 0x269e…b991。每个地址支付其已有 sETH，回执的 WETH 转账、sETH 扣款、Swap、WETH 解包日志索引分别为 A 的 207—210、B 的 175—178。原生 ETH 最终付款均出现在调用轨迹 [0, 2]，收款方等于顶层交易发送地址［22-24］。前窗一笔满足相同标准，说明该路由在公告前已存在。后窗从 7 日扩至 14 日没有增加成交或严格闭环，两个样本始终保留。链上方法能识别 0x 合约及资产流，无法识别实际网页、是否先遇到拒绝或用户为什么选用该入口。

# 6 成本分解与历史参数实验

## 6.1 逐价格步复算池费

三个样本各自所在区块内，该池只有一条日志，即该笔 Swap。本研究用两个归档节点在前一区块末读取 slot0、流动性、tick 间距、位图与穿越的已初始化 tick，以固定 v3 核心代码的整数舍入规则复算［16］。每一步分别核对流动性、净输入、输出与池费。三笔交易分别经历 3、4、3 个价格步，累加结果与 Swap 输出、终止价格和最终流动性一致。样本 A、B 的实际池费分别为 0.000281300000000002 和 0.000207700000000001 sETH，约为输入的 5 个基点。它们相对于名义费率的微小尾差来自逐步整数舍入。

令 I 为卖出量，P₀ 为交易前池内边际价格，令 X = I × P₀ 为同量资产的基准对价。以 P₀ 折算池收取的输入代币费 F，以收到的 ETH 数额为 Q，以本笔 Gas 开支为 G。成交偏离为 (X − Q)／X，分为 F × P₀／X 与 (X − Q − F × P₀)／X。后项反映沿池价格曲线交易及离散舍入造成的剩余偏离。总可观测成本为 (X − Q + G)／X，新增项是 G／X。本文统一以 X 分解成本，同时单列 G／Q 供理解实际现金负担。池费已包含在成交偏离中，不能与未拆分的成交偏离再次加总。

@figure costs.png
@caption 图 2　以池内边际价格为统一基准的成本分解
@note 单位为基点。总条长是成交偏离加本笔 Gas。池费从成交偏离中拆出，外部授权、学习及等待成本没有纳入。

@caption 表 5　公告后两笔交易的可观测成本
| 样本 | 池费（bps） | 其余成交偏离（bps） | Gas（bps，以 X 为分母） | 合计（bps） | Gas／实收 |
|---|---|---|---|---|---|
| A | 5.00 | 42.90 | 68.35 | 116.25 | 0.687% |
| B | 5.00 | 35.05 | 109.27 | 149.32 | 1.097% |
@note 样本 A、B Gas 用量分别为 277,205 和 253,757，单价为 14 和 18 Gwei。显示值经舍入。池内基准不是下单时的前端报价。授权若发生在其他交易，相关费用不在表内。

## 6.2 最低到账条件的 1 wei 分界

对表 4 三笔交易在各自前一区块末进行配对只读实验。固定发送方、目的合约、交易路径、输入量、Gas 和 ETH value，仅替换最低到账数额。每笔 35 个去重设定，包含原门槛、零、实际到账 Q、Q 的正负 1 至 10¹² wei 的若干绝对偏移，以及正负 1 至 500 个基点的相对偏移。两家归档节点对同一输入分别执行，合计 105 个参数点、210 次 eth_call。所有配对结果一致。每笔在门槛等于 Q 时成功并仍返回 Q，在门槛等于 Q + 1 wei 时即返回 UniswapV3Feature/UNDERBOUGHT。

@caption 表 6　三笔交易的最低到账分界
| 样本 | 最高实测成功门槛（wei） | 最低实测回滚门槛（wei） | 双节点结果 |
|---|---|---|---|
| 前窗 | 763874225282298256 | 763874225282298257 | 一致 |
| A | 565085179393003844 | 565085179393003845 | 一致 |
| B | 416331959477254147 | 416331959477254148 | 一致 |
@note 实验单位是历史交易。105 个参数点属于对三笔交易的重复干预。调用无签名和广播，模拟回滚不计入链上失败次数。

这一结果区分 A 层可调用与 B 层可完成。即使交易路径、资金与历史流动性固定，用户设置的门槛也足以改变合约执行结果。实验直接识别的是给定状态和参数下的执行约束。它无法恢复用户报价、迁移过程或因官方网页限制而增加的摩擦。

# 7 讨论与结论

Mt.Gox 的账户内成交没有移除平台出币的必要权限。Uniswap Labs 公告限制自营网页入口后，sETH 在观察范围内仍有两笔通过 0x 和 v3 池完成原钱包扣款与原生 ETH 结算的交易。**用户能否处置原有资产，取决于指定操作的必要权限及其可替代路径。** 这个结论由同资产、同路径和对价到账的直接证据支持，与对交易组织的笼统安全排序无关。

三个识别边界决定如何使用研究结果。首先，生产部署记录和历史存档索引无法定位官方网页规则的实际激活时刻，也无法证明交易者实际遭遇网页拒绝。其次，完整名单筛查保证的是明确链、协议版本及窗口内的覆盖，真实成交集中于 sETH，无法外推到其他代币、无活跃流动性的池或其他限制类型。最后，Swap 日志以执行成功为条件，缺少未广播、回滚或放弃的用户尝试。样本内成本不能估计普通用户的完成概率或限制所致的增量成本。

@availability 数据与代码｜补充材料提供全部 Factory 日志和匹配池 Swap、双源回执、调用轨迹、历史状态、105 组配对输入输出、生产取证记录、运行环境及预期结果。无需 RPC 可离线复算，在线入口可重取链上结果。公开节点受历史状态能力和限流约束，所有结果使用已冻结的原始快照验证。

# 参考文献

[1] WINKLEVOSS BITCOIN TRUST. Amendment No. 3 to Form S-1［EB/OL］. (2014-05-08)［2026-11-23］. https://www.sec.gov/Archives/edgar/data/1579346/000119312514190365/d721187ds1a.htm.

[2] UNISWAP LABS. Token access on app.uniswap.org［EB/OL］. (2021-07-23)［2026-11-23］. https://blog.uniswap.org/token-access-app.

[3] HÄGELE S. Centralized exchanges vs. decentralized exchanges in cryptocurrency markets: A systematic literature review［J］. Electronic Markets, 2024, 34: 33. https://doi.org/10.1007/s12525-024-00714-2.

[4] SCHÄR F. Decentralized finance: On blockchain- and smart contract-based financial markets［J］. Federal Reserve Bank of St. Louis Review, 2021, 103(2): 153-174. https://doi.org/10.20955/r.103.153-74.

[5] HIRSCHMAN A O. Exit, voice, and loyalty: Responses to decline in firms, organizations, and states［M］. Cambridge, MA: Harvard University Press, 1970.

[6] MTGOX CO., LTD. Announcement regarding an application for commencement of a procedure of civil rehabilitation［EB/OL］. (2014-02-28)［2026-11-23］. https://www.mtgox.com/img/pdf/20140228-announcement_eng.pdf.

[7] KOBAYASHI N. Announcement of commencement of civil rehabilitation proceedings［EB/OL］. 首发 2018-06-22，更新 2018-10-26［2026-11-23］. https://www.mtgox.com/img/pdf/20180622_announcement_en.pdf.

[8] KOBAYASHI N. Notice concerning change of repayments deadline［EB/OL］. (2026-10-16)［2026-11-23］. https://www.mtgox.com/img/pdf/20261016_b3a13e0f-55f6-4653-913b-be80762390e8_announcement_en.pdf.

[9] UNISWAP. Update unsupported and broken lists: commit 4078390［CP/OL］. (2021-07-23)［2026-11-23］. https://github.com/Uniswap/interface/commit/4078390a4890445d1ff0ed5196fd4cb56a44de87.

[10] UNISWAP. Fix: update unsupported and broken lists: pull request 2100［EB/OL］. (2021-07-23)［2026-11-23］. https://github.com/Uniswap/interface/pull/2100.

[11] GITHUB. Uniswap/interface deployment 397083627 and public statuses［DS/OL］. (2021-07-23)［2026-11-23］. https://api.github.com/repos/Uniswap/interface/deployments/397083627/statuses.

[12] GITHUB. REST API endpoints for deployment statuses［EB/OL］. ［2026-11-23］. https://docs.github.com/en/rest/deployments/statuses.

[13] UNISWAP. Announcement on restricting token access at app.uniswap.org［EB/OL］. (2021-07-23)［2026-11-23］. https://x.com/Uniswap/status/1418697012095164420.

[14] INTERNET ARCHIVE. Wayback Machine availability record for app.uniswap.org［DS/OL］. (2021-07-24)［2026-11-23］. https://archive.org/wayback/available?url=https%3A%2F%2Fapp.uniswap.org%2F&timestamp=20210724064834.

[15] ARQUIVO.PT. Archived URL history for app.uniswap.org［DS/OL］. ［2026-11-23］. https://arquivo.pt/textsearch?versionHistory=https%3A%2F%2Fapp.uniswap.org%2F&from=20210722000000&to=20210807000000&maxItems=10.

[16] UNISWAP. Uniswap v3 core: commit e3589b1［CP/OL］. ［2026-11-23］. https://github.com/Uniswap/v3-core/tree/e3589b192d0be27e100cd0daaf6c97204fdb1899.

[17] UNISWAP DEVELOPERS. Ethereum deployments［EB/OL］. ［2026-11-23］. https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments.

[18] UNISWAP. Interface list revision: commit b416603［CP/OL］. (2021-08-06)［2026-11-23］. https://github.com/Uniswap/interface/commit/b416603ff483679eedb795141cb9c376ee9b5086.

[19] ETHEREUM. JSON-RPC API［EB/OL］. ［2026-11-23］. https://ethereum.org/developers/docs/apis/json-rpc/.

[20] 0x PROTOCOL. Addresses［EB/OL］. ［2026-11-23］. https://docs.0xprotocol.org/en/development/basics/addresses.html.

[21] 0x PROJECT. IUniswapV3Feature.sol: commit b46eead［CP/OL］. ［2026-11-23］. https://github.com/0xProject/protocol/blob/b46eeadc64485288add5940a210e1a7d0bcb5481/contracts/zero-ex/contracts/src/features/interfaces/IUniswapV3Feature.sol.

[22] ETHEREUM MAINNET. sETH sale through 0x at block 12877887［DS/OL］. (2021-07-22)［2026-11-23］. https://etherscan.io/tx/0x52830f2aff23b7004163c3b4199ffcda38ab4cab4b7839012099cd07a1f56ea9.

[23] ETHEREUM MAINNET. sETH sale through 0x at block 12887491［DS/OL］. (2021-07-24)［2026-11-23］. https://etherscan.io/tx/0xcf44a8e2da894ec47f52c86929fa1be3ff66724318fa19b22bc0fffc5c1c8c53.

[24] ETHEREUM MAINNET. sETH sale through 0x at block 12907023［DS/OL］. (2021-07-27)［2026-11-23］. https://etherscan.io/tx/0x23f79ede0ae6d1aa8605d762ceafe8daccb507e8dd9e8da4bb2b96bcc299f89e.
