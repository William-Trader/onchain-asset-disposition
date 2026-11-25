# 数字资产交易服务受限下的用户资产处置能力
## 基于 Mt.Gox 与 Uniswap v3 的条件式机制检验

@author William Chou
@lead 摘要｜交易服务受限后，谁仍有权把原账户中的资产交到指定收款人手上？本文追踪托管提现和自托管卖出的必要步骤，并用历史链上状态检验替代路径。Mt.Gox 停提后，四场所参照下的场内价格转为折价。管财人公告给出分批收款人数下界，方案条款允许计算给定债权条件下的名义回收比例。以太坊主网固定名单含 129 个地址。公告后 14 天，Uniswap v3 上无池、有池零成交、有成交的地址分别为 123、5、1 个。在同一条链的 61 天、三个交易场所中，有成交的名单资产增至 25 个。公告后在 0x 路径核实的两笔卖出均完成 sETH 扣款和同钱包 ETH 到账，仅一笔可追溯至公告前余额。加入必要授权费后，历史模拟中改经 Curve 的净到账依次增加 0.001229 和 0.002412 ETH。结论限于指定时点、资产、数量与权限。个体网页拒绝、未广播尝试、托管客户实际回收分布均不可识别，场所与时段也限制外推。
@key 关键词｜数字资产；托管提现；界面限制；原有持仓；交易执行成本
@en Users’ Ability to Dispose of Digital Assets under Trading-Service Restrictions: A Conditional Mechanism Test Using Mt.Gox and Uniswap v3
@lead Abstract｜Who can deliver assets from an existing position to the intended recipient when a trading service is restricted? We trace custodial withdrawals and self-custodial sales, then replay alternative routes at historical states. After Mt.Gox suspended withdrawals, its price moved to a discount relative to a four-venue benchmark. Trustee notices bound cumulative recipient counts, and plan provisions determine nominal recovery for specified claims. Of 129 listed Ethereum addresses, 123 had no Uniswap v3 pool, 5 had pools without swaps, and 1 traded in the 14 days after the announcement. Over 61 days across three venues, 25 listed assets traded. Two subsequent 0x sales debited sETH and returned native ETH to the originating wallet. Only one drew on a pre-announcement balance. With required approvals priced in, simulated Curve execution increased net receipts by 0.001229 and 0.002412 ETH, respectively. The findings are conditional on the asset, size, state and permissions. Individual interface rejection, unbroadcast attempts and realized creditor-level recovery distributions remain unobserved. Coverage is venue- and period-specific.
@key Keywords｜digital assets; custodial withdrawals; interface restrictions; pre-existing holdings; execution costs

@break
# 1　研究问题与比较设计
2014 年 2 月，Mt.Gox 客户可以在平台内看到以 BTC 表示的余额，一度还能成交，但向外部地址提取 BTC 已被暂停［1–3］。2021 年 7 月，Uniswap Labs 宣布限制其自营网页对部分代币的访问，同时主张其他入口仍能使用协议［4］。两件事都涉及“退出”，却要求用户完成不同的最后一步。本文将题目中的“用户资产处置能力”限定为可核验的问题：在特定时点，哪一笔原账户权益或钱包余额，能够经过哪些必要步骤，把指定资产或交易对价交到指定收款人手上？
Hägele 的交易所综述提供制度分类［5］。本文据此先区分由谁保管密钥。Schär 的分层框架［6］把界面、路由与结算合约分开，因而分别核验被禁按钮、执行合约和最终收款。Feder 等关于市场受安全冲击的实证［7］提醒我们，同期场内价格还含有其他风险。Hirschman 的退出概念［8］在这里对应一项可观察的结果，即原头寸转化为可控制的外部收款。依照 George 与 Bennett 的结构化、聚焦比较［9］，两案均回答同一组问题：谁须批准，是否另有执行者，指定收款人究竟收到什么？
## 1.1　比较单位与反证条件
观察单位为“原资产权益、指定操作、时点、受到限制的服务”。在托管案中，目标是从原平台账户提出 BTC，并由客户指定的外部地址收取。在链上案中，目标是卖出指定数量的主网 sETH，并由原发送地址收到原生 ETH。识别公告前持仓另加时间条件：事件前余额足够，且事前和事后入账能够区分。在可替代代币账户中，这一条件追踪余额来源，不给每枚代币赋予唯一编号。
@caption 表 1　从权限到到账的三个判据
| 判据 | 要回答的问题 | 观察与反证 |
| --- | --- | --- |
| A 可调用 | 谁能否决指定操作？其授权能否替换？ | 否决点指某主体拒绝后，给定时点所有合格路径均无法完成该步骤。托管出币须由平台签署。官方网页按钮仅控制该入口。 |
| B 可完成 | 指定数量是否从原账户扣除，并由指定收款人取得目标资产？ | 对照真实回执、转账与原生资产付款轨迹。缺少任一环，降为池内活动；持仓来源另查事件前余额。 |
| C 成本可观测 | 已经完成或可配对模拟的路径，各有多少可计量代价？ | 分列市场价差、程序历时、交易净额与假设费用预算。预算由分析者显式给定，用户实际偏好未知。 |
权限另行编码。池的 setFeeProtocol 调整既定交换费的分配，属于规则管理权。判定逐笔交换否决权还须找到可拒绝该笔操作的调用条件。第 3.3 节以链上执行回执核验二者。
## 1.2　证据边界
第一，源码、部署任务与论坛记录不能识别样本钱包何时被网页拒绝。第二，可核对已上链回滚，未广播、被替换或放弃的尝试缺少完整分母。第三，托管案的市场价差、计划偿付与个人净到账衡量不同对象。第四，两个事件依机制差异选取，名单、链、场所与窗口均固定。下文检验在这些条件下路径能否完成，不估计限制对一般用户的平均因果效应。

@break
# 2　Mt.Gox：账户余额、市场折价与偿付程序
## 2.1　从停提到部分实付
2014 年 2 月 7 日的同期报道转录了 Mt.Gox 暂停 BTC 提现的公司声明［1］。美国法院后来梳理案卷时记载，客户 Greene 称自己 2 月 5 日已向客服反映提现等功能无法使用，并记载了 7 日的停提公告［2］（第 6 页）。5 月 8 日第三方信托发起人呈交 SEC 的注册文件补充记载场内交易一度继续［3］。个案陈述说明至少有具体客户报告提现困难，不能据此概括全部客户遭遇。
2 月 28 日，公司在向东京地方法院申请民事再生的公告中披露，账面负债超过资产，并报告其初步发现有大量比特币缺失，规模及原因仍在调查［10］。这足以说明更换网页不能弥补托管资产缺口；2 月 7 日究竟有多少 BTC 可供正常兑付，无法由月末披露倒推。2018 年 6 月 22 日法院启动新的民事再生程序，相关公告于 10 月 26 日更新［11］。2024 年 7 月 5 日，管财人确认已通过部分指定交易所向部分债权人偿付 BTC 与 BCH，距停提 3,801 日［12］。这是两个公开事件的间隔，个人等待时长与回收比例须另有账户资料。2026 年 10 月公告仍列出未完成手续及支付遇阻的债权人，获准将相关期限延至 2027 年 10 月 31 日［13］。
## 2.2　场内 BTC 是怎样定价的
取 Bitcoinity 同一 UTC 日的 BTC/USD 均价。图 1 保留 Bitstamp 与 Bitfinex 两条可辨认的参照序列。将 1 月 24 日至 2 月 25 日的 Bitstamp 均价逐日与该所官方高低价核对，33 日均在区间内［14–15］。主要稳健性基准取 Bitstamp、Bitfinex、BTC-e、Kraken 同日美元均价的中位数。日价差按 100 ×（Mt.Gox 均价／基准 − 1）计算。
@figure gox.png
@caption 图 1　Mt.Gox 场内 BTC 相对两家参照交易所的日均价格差
@note 横轴为 2014 年 UTC 日期。两条序列在多日接近重合。纵轴为百分比，负值表示 Mt.Gox 折价。资料取自 Bitcoinity 分交易所历史导出。
相对 Bitstamp 的前后各 14 日价差中位数分别为 +17.29% 和 −39.63%。事件日仍溢价 2.64%，后续两个七日段的中位数分别为 −16.90% 和 −55.21%。交易在场内有报价，与客户能否把 BTC 转至外部地址，是两项分别可观察的事实。

@break
## 2.3　价格差对窗口、权重与法币摩擦的敏感性
@caption 表 1A　相对四场所基准的日价差（%）
| 单侧窗长 | 事前中位数 | 事后中位数 | 事前量加权均值 | 事后量加权均值 |
| --- | --- | --- | --- | --- |
| 3 日 | +14.75 | −5.35 | +10.86 | −6.03 |
| 7 日 | +15.73 | −16.90 | +12.58 | −19.85 |
| 14 日 | +17.29 | −39.61 | +17.02 | −47.76 |
| 17 日 | +16.97 | −50.47 | +16.95 | −52.25 |
@note 事件日 2014-02-07 单列。各窗口内的日价差以 Mt.Gox 当日 BTC 成交量加权。单位为百分比。原始日均价和成交量取自 Bitcoinity［14］。
四个窗口均从溢价变为折价，但幅度随窗口变化很大。后 14 日按量加权的折价比日中位数更深。用欧洲央行参考汇率将 Mt.Gox 同日 BTC/EUR 换成美元，构造美元相对欧元的场内基差：100 ×［美元报价／（欧元报价 × 每欧元美元数）− 1］［16］。前后各 14 日各有 10 个汇率发布日，不填补周末。基差中位数由 +1.63% 变为 −2.02%。在相同日期，美元与折美元欧元报价相对四所基准的事后中位数分别为 −43.87% 和 −42.88%。折价在两种计价下均存在。该代理还受汇率取样时间及市场分割影响，不能据此分离银行出金费、兑付预期或流动性冲击。
## 2.4　从计划条款到可观察的偿付进度
管财人的再生计划英译本第 4.3.1.2.2.2、4.3.4.3 节及修订生效公告［17–18］允许复算一类明确情形。设 C 为仅持有核准加密资产债权者的日元计价基数，无其他优先或法币债权，选择提前一次性偿付，忽略其他调整。名义应偿额为 min(C, 200,000) ＋ 21% ×［C − min(C, 200,000)］。C 为 20 万、50 万、100 万、1,000 万日元时，比率依次为 100%、52.60%、36.80%、22.58%。按原 BTC 数量回收多少及个人实际实收多少，还取决于债权、币现分配和到账记录。
以首次公开停提日为统一起点，管财人确认经指定交易所偿付 BTC/BCH。2024 年 7 月 5 日为第 3,801 天，已有部分债权人获偿［12］。其后公告给出累计人数的整数下界：第 3,812、3,820、3,827、3,848、4,066 天依次至少 13,001、17,001、17,001、19,001、19,501 人［19–23］。若把收款日排序，第 13,001 个收款时点距停提至多 3,812 天。公告没有逐人申请日、入账额或该口径的最终总人数，故只能给出顺序统计量上界，不能计算个人实际等待中位数或总体回收率。
@break
# 3　Uniswap v3：从公告声明到同资产样本
## 3.1　哪一步确实受限
Labs 在 2021 年 7 月 23 日的公告中同时声明限制自营界面访问、协议和其他入口仍可使用［4］。这一陈述给出了可检验的预测。如果名单内资产仍能经过相同协议池交换，链上应能找到输入和输出都可验证的实例。反之，成功的非名单代币交易、单一池事件或孤立报价均不足以支持该预测。本文只检验 sETH 等固定样本所及的一部分。
固定提交 4078390a 的前一版本不含 sETH。该提交的代码先在 app.uniswap.org 域名加载本地名单，再检查所选输入或输出是否属于名单；命中时，Swap 页面渲染 disabled 的“Unsupported Asset”按钮［24］。据此可辨认该版本禁止从标准按钮提交这笔交换。对纯中间路由代币是否有相同处理，需另外检查路由构建逻辑。提交时间为 7 月 23 日 22:05:14 UTC，同一 SHA 的 Production 部署任务创建于 22:05:20，官方消息发表于 22:18:20［24–27］。7 月 24 日 06:36 的网页存档只有索引，未恢复当时实际加载的脚本。证据可定位公告、代码分支及部署请求，生产域名生效时刻和两个钱包是否访问过该网页仍未识别。 同期论坛在 7 月 24 日 18:47 UTC 记述了“unsupported token”提示，7 月 26 日有发帖者报告自行维护镜像［28］。首帖晚于样本 A 的卖出、早于样本 B。公开帖子与 A、B 钱包均无可验证关联。
## 3.2　从名单到成交的筛选
7 月 23 日为事件日并单列。锁定同一历史名单的 129 个以太坊主网合约地址，名称仅供展示。后续名单变更不回填，这个固定队列不表示每个地址在全窗始终受限。主窗、扩展窗分别取前后各 7、14 日。另取前后各 30 日，并纳入 Uniswap v2 和 SushiSwap v2。逐工厂扫描建池事件至窗口末，再扫描匹配池的 Swap。没有池、有池零日志、有日志按地址互斥归类。两个名单资产配对时，池级交易哈希在场所汇总中只计一次。主窗所在的 v3 工厂至 8 月 6 日累计 3,739 条建池日志，匹配 6 个名单资产、7 个池［29］。
@caption 表 2　Uniswap v3 固定名单的完整分母及 sETH 成交
| UTC 窗口（2021 年） | 无池／有池零成交／活跃 | 零日志地址 | 日志／交易 | 严格卖出 |
| --- | --- | --- | --- | --- |
| 07-16 至 07-22 | 123／5／1 | 128 | 6／6 | 1 |
| 07-24 至 07-30 | 123／5／1 | 128 | 6／5 | 2 |
| 07-09 至 07-22 | 123／5／1 | 128 | 10／10 | 1 |
| 07-24 至 08-06 | 123／5／1 | 128 | 6／5 | 2 |
@note 每行分母均为 129。零日志涵盖无池和有池无成交两类。各 14 日窗嵌套相应的 7 日窗，合计时仅取不重叠窗口。严格卖出的收付规则见第 4.1 节。
sETH 原由个案线索选中。按相同规则重新普查名单后，发现它恰是 14 日窗唯一有 v3 成交的资产。表 2 的“零”只对指定链、工厂和时段有效。

@break
## 3.3　扩大场所与观察期后，哪些“零”仍然成立
@caption 表 2A　129 个名单资产在扩展窗口的分类及成交
| 覆盖范围和时段 | 无池 | 有池零成交 | 活跃 | 日志／去重交易 |
| --- | --- | --- | --- | --- |
| v3　前 30 日 | 123 | 4 | 2 | 45／45 |
| v3　后 30 日 | 122 | 5 | 2 | 41／40 |
| v3　全 61 日 | 122 | 4 | 3 | 87／86 |
| 三场所　前 30 日 | 91 | 14 | 24 | 1,602／1,574 |
| 三场所　后 30 日 | 90 | 20 | 19 | 1,120／1,093 |
| 三场所　全 61 日 | 90 | 14 | 25 | 2,773／2,718 |
@note 三场所为同链的 Uniswap v2、Uniswap v3 和 SushiSwap v2。前窗为 06-23 至 07-22，后窗为 07-24 至 08-22；全窗含 07-23。窗口末之前创建的池才进入该窗口。两种覆盖各有八种窗口，实际区块号及逐地址分类随文提供。
全窗 v3 的 87 个交换事件分属 sETH（85）、sXAG（1）和 MTSLA（1）。池的有符号净额进一步表明，前窗 sXAG 流入池，后窗 MTSLA 则从池流出。后者是买入方向，不能补作原持有人卖出受限资产的证据。三场所的活跃名单资产增加到 25 个，说明“仅 sETH 有成交”依赖具体的协议与观察期。这里能确认池发生了交换。钱包原持仓、实际支付人和收款人仍须逐笔核对，场所扩展的 2,718 笔交易不直接进入钱包层样本。
规则管理权须用执行记录核对。v3 工厂在区块 12,369,662 发出 OwnerChanged 事件，成功回执的受让地址与事件日前读取的 owner() 相符［30］。池的 setFeeProtocol 由工厂所有者调用，调整池交易费中划给协议的份额［29］。截至后 14 日窗末，目标池自创建以来对应变更日志为零。所有者权利与官网禁用按钮都可以定位，但两者均未为该指定卖出提供逐笔拒绝开关。
# 4　钱包层面的真实收付与持仓归属
## 4.1　谁付出了代币，谁收到了 ETH
严格判据要求交易成功，0x Exchange Proxy 的目标函数接收 sETH 卖单，池内与钱包侧记录满足四项条件：发送者支付 sETH 入池，池向代理支付 WETH，代理解包 WETH，等额原生 ETH 回到同一发送地址［29，31–32］。主网 sETH 合约为 0x5e74…31cb，成交池为 0xbb66…7c82；完整地址、函数选择器及原始调用轨迹随文提供。交易前一区块两个发送地址均无合约代码，地址记录不能识别地址背后的自然人、所有权安排或使用的前端。
后窗 6 个池内交换腿中有 4 个卖出腿、2 个买入腿。卖出中的两个单腿分别属于样本 A、B。其余两个卖出腿同属 7 月 27 日 09:42:19 的成功交易，顶层目的为 0xdd69…8471，日志序号分别为 124 和 127；该交易包含其他池内活动，未通过严格收付判据。两个反向买入也保留在池级分母。前窗有另一笔满足相同规则的 0x 卖出，证明这条执行路径在公告前已经存在。
@break
## 4.2　“曾经持有”与“卖出原持仓”
@caption 表 3　两笔公告后卖出及公告前持仓核验
| 钱包 | 样本 A（0x2ead…f790） | 样本 B（0x269e…b991） |
| --- | --- | --- |
| 最早收到 sETH 的区块及 UTC 日期 | 12,566,248，2021-06-04 | 8,949,696，2019-11-17 |
| 7 月 23 日开始前余额（sETH） | 0 | 0.415404002756450395 |
| 7 月 24 日开始前余额（sETH） | 0 | 0.415404002756450395 |
| 卖出时点（UTC）及区块 | 07-24 06:48:34，12,887,491 | 07-27 08:14:56，12,907,023 |
| 卖出数量／原地址实收 | 0.562600 sETH／0.565085179393003844 ETH | 0.415400 sETH／0.416331959477254147 ETH |
| 事件日至卖出前新增 sETH | 0.562629779282404131 | 0 |
@note 两窗口边界余额取 UTC 零点前最后一个区块。首次正额入账是该固定代币合约的最早 Transfer 入账。交易浏览器仅供定位，数值取自归档 RPC［32］。
对两个地址分别自创世块至卖出所在块检索转入、转出 Transfer 日志，保留区块及日志序号，按方向累计，再以事件日两侧和卖出前后的四次 balanceOf 快照交叉验证。两个地址在四个截点的净转移累计均与余额一致。A 在公告前收过币，却已将当时余额转出；本次卖出的资金于区块 12,887,464 才入账，距卖出 27 个区块。B 的 0.415404002756450395 sETH 从事件日初到卖出前未增加，卖出后余 0.000004002756450395 sETH。因而两笔都证明路径成交，只有 B 满足“把公告前已有持仓换回 ETH”的更强命题。
若只查首次收到代币的日期，两地址都会被编码为原持有人。这会使最贴近标题的证据数量翻倍。反过来，即使 B 的余额来源成立，链上仍无法识别其是否遭遇前端拒绝，或是否因公告而选择 0x。
## 4.3　已上链回滚能补到哪里
对事后选出的 A、B，在双 14 日及事件日完整列举其发起的主网交易，再以四个边界的账户交易序号和两家服务商的回执复核。A 前／当／后分别上链 6／1／9 笔，B 为 12／0／60 笔，共 88 笔。后窗两笔真实回滚分别涉及流动性仓位管理及另一资产的交换，调用轨迹均不满足本研究的 sETH 卖出判据［33–34］。钱包由已知成交反向选入，未广播、未打包或放弃操作无法由连续序号恢复。这 88 笔只界定两个地址的已上链观测范围。

@break
# 5　价格、费用与替代执行实验
## 5.1　相对哪个价格，付出了什么代价
记卖出数量为 q，原钱包实收 ETH 为 Y，网络费为 G。取交易前一区块末的池内边际价 P₀＝(sqrtPriceX96／2⁹⁶)²，以 WETH/sETH 计。两个代币均为 18 位精度。对交易所在块检查该池全部日志，并按历史流动性和跨越的已初始化 tick 重算每一步输入、费用、输出、终止价格。若逐步合计输出和真实收款不同，差额应单列；若目标函数有额外抽取，也会在这一对账中留下差额。两笔重算与实收在最小货币单位上相等。
@caption 表 4　两笔卖出的成交分解与外部价格基准
| 项目 | 样本 A | 样本 B |
| --- | --- | --- |
| P₀（WETH/sETH） | 1.009252109 | 1.006273788 |
| 池曲线期望产出＝实际收款（ETH） | 0.565085179393003844 | 0.416331959477254147 |
| 池费折价／曲线价格影响（bp） | 5.00／42.90 | 5.00／35.05 |
| 对池内边际价的成交偏离（bp） | 47.90 | 40.05 |
| 本笔网络费 G（ETH） | 0.003880870 | 0.004567626 |
| 同一池内基准下的网络费／合计（bp） | 68.35／116.25 | 109.27／149.32 |
| 网络费占实际收款（bp） | 68.68 | 109.71 |
| 对同额 Curve 报价的毛到账缺口（bp） | 7.47 | 41.79 |
@note 1 bp＝0.01%。表中可相加的三项统一除以 qP₀。网络费占实收另以 Y 为分母；Curve 毛到账缺口以 Curve 同额报价为分母。不同分母的数值不得相加。起止 sqrtPriceX96、逐步舍入和残差详见技术附录。
池内偏离量为 10,000 × [1 − Y／(qP₀)]，扣除网络费后把 Y 换为 Y − G。A 的 47.90 bp 可以分解为 5.00 bp 池费与 42.90 bp 曲线价格影响；在该精度下，池支付至钱包实收的额外路由残差为零。B 的分解同理。两笔相对另一池 Curve 的报价缺口分别是 7.47 和 41.79 bp［35］。同一笔交易因比较对象不同会给出不同量级；历史池内边际价和外部池报价都不能替代持有人当时看到的询价，也不能确定唯一公平价格。
## 5.2　最低到账条件在哪里失效
在原交易前一区块末复现原输入、发送者和执行合约，仅改变最低到账整数。对前窗一笔和后窗两笔，各取 35 个门槛，含原值、实际产出、实际产出相邻 ±1 wei 以及多档基点偏移。两家服务商的 210 次 eth_call 对 105 个配对取值完全一致。三个样本的最大成功门槛均等于该笔实收，再高 1 wei 均以 UNDERBOUGHT 回滚，实现代码也要求最低额不得大于产出［31］。A、B 原门槛均比当时实际可得额低约 50 bp。这是相对固定历史状态的成交余量，不能还原用户界面中显示的滑点偏好。实际的网络费来自历史回执；只读门槛实验的失败没有链上支出。

@break
## 5.3　同一钱包换执行者，净到账如何变化
在三笔真实成交各自的父区块上，使用 eth_simulateV1 构造五个可分别复跑的历史情景。第一组重放 0x；第二、三组通过 Uniswap v3 SwapRouter 直连原池，并把 WETH 解包至同一钱包，分别保留原授权和先做一笔等量授权；第四、五组对 Curve sETH/ETH 池作相同处理。固定卖方、卖量、原最低到账和 Gas 单价，竞争路径从同一父状态分别开始。模拟不签名、不广播；合成的原生资产付款日志只用于追踪模拟收款，真实样本仍以链上回执和调用轨迹核验［31–32，35–37］。
历史 allowance 显示，三地址在对应时点对 0x 的额度充足，对另两条路径的额度均为零。无新增授权的六个替代情景全部回滚，先授权的六个情景均完成。0x 的三次重放均精确再现真实毛到账与 Gas 用量。两家服务商对状态、用气、回滚数据及收付方向一致；提供商数量不等于底层基础设施的独立性。
@caption 表 5　历史同额卖出及净到账对照
| 历史情景 | 授权 Gas | 交换 Gas | 毛到账（ETH） | 净到账（ETH） |
| --- | --- | --- | --- | --- |
| A · 原 0x 实际 | 0 | 277,205 | 0.565085179 | 0.561204309 |
| A · 新授权＋直连 v3 | 69,773 | 269,465 | 0.565085179 | 0.560335847 |
| A · 新授权＋Curve | 69,773 | 149,850 | 0.565507642 | 0.562432920 |
| B · 原 0x 实际 | 0 | 253,757 | 0.416331959 | 0.411764333 |
| B · 新授权＋直连 v3 | 66,973 | 246,016 | 0.416331959 | 0.410698157 |
| B · 新授权＋Curve | 66,973 | 149,850 | 0.418079065 | 0.414176251 |
@note 既有授权在本次交易无需新增。净到账＝毛到账 −（新增授权 Gas＋执行 Gas）× 原 Gas 单价。A、B 分别取 14、18 Gwei。过去已付的授权费未分摊；表内取 9 位小数，计算使用整数 wei。
直连同一池后，v3 曲线给出的金额不变，直连接口的执行 Gas 略少；但若从该钱包的真实授权状态出发，补授权使两笔净到账分别减少 0.000868462、0.001066176 ETH。Curve 在相同限额下给出更高的毛到账，且执行用气较低；计入新授权后，净到账分别比真实交易高 0.001228610815784793 和 0.002411917511634630 ETH。历史成交只能说明交易者采用了 0x。重现出更优的反事实金额，不能据此推断当时的人有相同报价、理解全部选项，或因界面政策承担了这一差额。
治理也是路径的条件。三笔交易前，0x 代理的 owner 和卖出函数对应实现均可在历史状态查得，后者与真实轨迹中的委托调用吻合。特性注册合约对替换和回退函数实现设有所有者权限［31］。经该代理并未消除对执行合约的依赖；链上数据也无法证明用户曾使用某个 0x 报价网页或中继。

@break
## 5.4　扩大卖量：报价成功是否意味着能卖完
固定 2021 年 7 月 9—22 日与 7 月 24 日—8 月 6 日各日 UTC 零点后的第一个区块，在同一状态下比较 0.1、0.5、1、5 sETH 四档卖量，方向始终是 sETH 换 ETH。28 日 × 4 档形成 112 个“日期—卖量”单元。每个单元分别读取 v3 的单池 Quoter 和 Curve 的 get_dy，并从另一服务商复核，共 448 次报价读取。v3 报价器只返回输出数额，故再追踪池的回调，解码实际要求支付的 sETH 及给出的 WETH。两家归档服务商的 224 条网格调用轨迹均按输入、输出逐项比对。Curve 代码按传入的指定数量 dx 计算报价；每日网格度量报价和池容量，钱包级执行及 Gas 只在前述逐笔配对实验中测量。
@caption 表 6　28 个日度状态下，同额可比的路径覆盖
| 指定卖量 | v3 有正报价（日） | v3 全额（日） | Curve 毛报价较高（日） | 差额中位数（bp） |
| --- | --- | --- | --- | --- |
| 0.1 sETH | 28 | 28 | 15 | 3.67 |
| 0.5 sETH | 28 | 28 | 22 | 20.51 |
| 1 sETH | 28 | 28 | 27 | 42.06 |
| 5 sETH | 28 | 0 | 不适用 | 不适用 |
@note 仅以全额可比日期为分母。差额为 10,000 ×（Curve 报价 − v3 报价）／Curve 报价，正值表示 Curve 毛报价较高。不同日期可能复用相同池状态。
@figure capacity.png
@caption 图 2　每次指定卖出 5 sETH 时，v3 池回调实际要求的输入
@note 横轴为 2021 年 UTC 日期，纵轴单位为 sETH。实线来自逐日历史 Quoter 调用的池回调，虚线为请求数量。7 月 23 日单列。数据见 daily_quotes.csv。
如图 2 所示，5 sETH 这一档在 28 个日期均得到正报价，但池回调实际只要求约 1.0821 至 2.9999 sETH，达不到全额处置条件。若直接将该输出与另一池卖完 5 sETH 的总收入作比，会把未卖出的余额算作价格损失。0.1 sETH 档的相对毛报价时优时劣；到 1 sETH 档，Curve 在 27 个可比日给出较高毛报价。该结果描述特定池、方向、规模与取样时点。池的活跃流动性在相邻日期可能没有变化，112 个单元不能视为 112 名独立用户，也不用于政策显著性检验。

@break
# 6　两案的机制边界与处置方案
@figure mechanism.png
@caption 图 3　托管提现与网页受限交易的必要步骤
@note 作者依据停提公告、前端源码与 sETH 原始交易轨迹绘制。上排标出托管出币的暂停点，下排标出被限制的网页入口和已核实的链上收付。此图为流程图。
图 3 给出的判断起点是原权益的控制人。Mt.Gox 客户不能以自己的密钥签署托管地址出币；另一处交易或新购 BTC 无法释放原账户权益。相反，在 sETH 案中钱包保有签署权，官方网页、广播服务、执行代理和流动性池分别承担不同任务。可替代执行者至少包括本案实测的链上代理和经新授权后可完成的标准路由，调用哪个界面、由哪个广播服务提交仍不可见。链上签署权本身也不能保证卖完指定数量，图 2 给出了反例。
## 6.1　将机制判断转化为可检验的方案
对托管服务，运营方可在提现状态页独立显示四类记录：已接收申请、已记账、已产生可核验的出币交易、外部地址已收款；同时公布受限资产、起止时点与积压口径。用户能保存申请回执和链上哈希，审计者可以检查“标为完成”的抽样记录是否确有外部收款。偿付能力不足时，状态披露的作用是保全证据、减少误判；实际支付仍取决于可用资产、托管签署与法定程序。仅公布储备地址余额也无法同时证明客户负债及出币能力。
对自托管钱包，执行前可先固定链、代币地址、目标卖量和最终收款资产；随后检查授权对象和额度，在同一历史状态或当前估计状态比较全额扣款、实际收款人、最低到账与新增网络费。只有满足用户给定的限制，才按净到账排序。表 7 将这一方法作为可复验的决策规则，完整计算见 decision.py。
@caption 表 7　交易费用预算和新增授权如何改变可选路径
| 费用预算 | 是否允许新授权 | A 可选数／净得最高者 | B 可选数／净得最高者 |
| --- | --- | --- | --- |
| 50 bp | 是 | 0／无 | 0／无 |
| 100 bp | 否 | 1／原 0x | 0／无 |
| 100 bp | 是 | 3／Curve | 1／Curve |
| 150 bp | 是 | 3／Curve | 3／Curve |
@note 预算定义为本次全部网络费占该候选路径毛收款的比例。每钱包比较三条路径，保留原最低到账额；未单列以失败调用产生的假设费用。数值展示规则的适用条件，不代表用户真实预算或普适费率上限。
共同的设计原则是给出可检查的最终状态。托管案的“完成”要求收款证据，自托管案则额外要求输入数量足额、包装资产已按目标解包、新授权成本已计入。后者的程序只比较纳入的历史路径；广播后的状态变化、交易排序和时间成本仍可能改变实际结果。

@break
# 7　结论与识别限制
当交易服务受限时，用户能否退出一笔原有头寸，首先取决于谁有权完成不可省略的步骤。Mt.Gox 暂停出币后，场内成交仍有价格，跨场所折价和多年后的部分偿付记录反映了两种不同的退出约束。对于仍拥有签署权的钱包，问题转为是否存在一条能够消耗指定输入、把目标资产交还给本人的路径，以及这条路径是否满足其费用预算。本案在公告后观察到两笔具有完整支付链的交换，其中一笔还能确认资金来自公告前余额。
本文对 Labs 公开声明的增量在于可被推翻的具体判断。A 的持仓历史推翻了“两个卖家都处置了事前持仓”的说法。直连实验显示，执行合约本身省下的 Gas 可以小于新增授权费。大额报价实验又给出一个明确的失败条件：报价为正时，指定数量仍可能卖不完。这三项发现分别界定“原有”“可替代”和“可完成”的证据门槛。它们把退出理论中的权限与代价落实到可观察的账户、步骤和金额［8］。
两类记录可对机制给出有方向的约束。托管侧，四场所定价与分批偿付都指向从账面权益到交付之间的等待，但只能界定市场折价、计划算例和累计支付人数的下界。链上侧，真实回滚能定位已上链操作的失败，不能恢复钱包在网页上的经历。所有归档比对均经托管 RPC 服务完成，多个品牌可能共用后端。本研究未运行独立自托管归档节点。
若要进一步研究用户体验，分母须从“收到任务的用户”开始记录。经知情同意，可在只读或本地模拟环境随机分派同额处置任务，预先登记资产、预算及截止时点，并记录看到限制、放弃、授权、模拟成功和实收验证各阶段的人数及耗时。届时才能分别估计技术可执行、费用可接受以及用户实际完成的比例。
@availability 数据与程序｜压缩包提供正文、技术附录、逐条评审回应及研究复现目录。以 python verify.py 可离线重建主要表格并逐字节核对输出。原始请求、回执、轨迹、名单、市场 CSV 和管财人文件均随附。历史重放没有签名或广播。

@break
# 参考文献
[1] COINDESK. Mt. Gox halts all Bitcoin withdrawals, price drop follows［EB/OL］. (2014-02-07)［2026-11-23］. https://www.coindesk.com/markets/2014/02/07/mt-gox-halts-all-bitcoin-withdrawals-price-drop-follows.
[2] UNITED STATES DISTRICT COURT, NORTHERN DISTRICT OF ILLINOIS. Greene et al. v. Karpeles. Memorandum opinion and order, No. 14 C 1437, Doc. 410［Z/OL］. (2019-03-12)［2026-11-23］. https://www.govinfo.gov/content/pkg/USCOURTS-ilnd-1_14-cv-01437/pdf/USCOURTS-ilnd-1_14-cv-01437-4.pdf.
[3] WINKLEVOSS BITCOIN TRUST. Amendment No. 3 to Form S-1［EB/OL］. (2014-05-08)［2026-11-23］. https://www.sec.gov/Archives/edgar/data/1579346/000119312514190365/d721187ds1a.htm.
[4] UNISWAP LABS. Token access on app.uniswap.org［EB/OL］. (2021-07-23)［2026-11-23］. https://blog.uniswap.org/token-access-app.
[5] HÄGELE S. Centralized exchanges vs. decentralized exchanges in cryptocurrency markets: A systematic literature review［J］. Electronic Markets, 2024, 34(1): 33. DOI: 10.1007/s12525-024-00714-2.
[6] SCHÄR F. Decentralized Finance: On Blockchain- and Smart Contract-Based Financial Markets［J］. Federal Reserve Bank of St. Louis Review, 2021, 103(2): 153-174. DOI: 10.20955/r.103.153-74.
[7] FEDER A, GANDAL N, HAMRICK J T, et al. The impact of DDoS and other security shocks on Bitcoin currency exchanges: evidence from Mt. Gox［J］. Journal of Cybersecurity, 2017, 3(2): 137-144. DOI: 10.1093/cybsec/tyx012.
[8] HIRSCHMAN A O. Exit, voice, and loyalty: Responses to decline in firms, organizations, and states［M］. Cambridge, MA: Harvard University Press, 1970.
[9] GEORGE A L, BENNETT A. Case Studies and Theory Development in the Social Sciences［M］. Cambridge, MA: MIT Press, 2005.
[10] MTGOX CO., LTD. Announcement regarding an application for commencement of a procedure of civil rehabilitation［EB/OL］. (2014-02-28)［2026-11-23］. https://www.mtgox.com/img/pdf/20140228-announcement_eng.pdf.
[11] KOBAYASHI N. Announcement of commencement of civil rehabilitation proceedings［EB/OL］. (2018-06-22，更新于 2018-10-26)［2026-11-23］. https://www.mtgox.com/img/pdf/20180622_announcement_en.pdf.
[12] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash［EB/OL］. (2024-07-05)［2026-11-23］. https://www.mtgox.com/img/pdf/20240705_01_announcement_en.pdf.
[13] KOBAYASHI N. Notice concerning change of repayments deadline［EB/OL］. (2026-10-16)［2026-11-23］. https://www.mtgox.com/img/pdf/20261016_b3a13e0f-55f6-4653-913b-be80762390e8_announcement_en.pdf.
[14] BITCOINITY. Bitcoin markets: daily prices and trading volumes by exchange［DB/OL］. ［2026-11-23］. https://data.bitcoinity.org/markets/price.
[15] BITSTAMP. Historical OHLC, BTC/USD, daily candles［DB/OL］. ［2026-11-23］. https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=45&end=1393372800.
[16] EUROPEAN CENTRAL BANK. Euro foreign exchange reference rates: USD per EUR, daily［DB/OL］. ［2026-11-25］. https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2014-01-01&endPeriod=2014-02-25&format=csvdata.
[17] KOBAYASHI N. Draft amended rehabilitation plan: English translation for reference purposes only［EB/OL］. (2022-09-29)［2026-11-25］. https://www.mtgox.com/d/04y7ivbnz5gw.pdf.
[18] KOBAYASHI N. Notice of amendment of rehabilitation plan becoming final and binding［EB/OL］. (2022-10-28)［2026-11-25］. https://www.mtgox.com/img/pdf/20221028_announcement_en.pdf.
[19] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash (2)［EB/OL］. (2024-07-16)［2026-11-25］. https://www.mtgox.com/img/pdf/20240716_c63b18e5-6a79-4f24-9c1c-3dbd74dc6f78_announcement_en.pdf.
[20] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash (3)［EB/OL］. (2024-07-24)［2026-11-25］. https://www.mtgox.com/img/pdf/20240724_aeedf9f1-7f27-40ec-ad70-26d2811167a5_announcement_en.pdf.
[21] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash (4)［EB/OL］. (2024-07-31)［2026-11-25］. https://www.mtgox.com/img/pdf/20240731_f6e19c0e-85b0-41f6-8102-2e8cafc9c498_announcement_en.pdf.
[22] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash (5)［EB/OL］. (2024-08-21)［2026-11-25］. https://www.mtgox.com/img/pdf/20240821_e8dbec0c-1fd8-42b5-b0d9-0b98ab42587c_announcement_en.pdf.
[23] KOBAYASHI N. Notice regarding repayment in Bitcoin and Bitcoin Cash through designated cryptocurrency exchange, etc. (6)［EB/OL］. (2025-03-27)［2026-11-25］. https://www.mtgox.com/img/pdf/20250327_50441ef4-dc28-473a-9fd2-495db2da4bbd_announcement_en.pdf.
[24] UNISWAP. Update unsupported and broken lists: commit 4078390［CP/OL］. (2021-07-23)［2026-11-23］. https://github.com/Uniswap/interface/commit/4078390a4890445d1ff0ed5196fd4cb56a44de87.
[25] GITHUB. Uniswap/interface deployment 397083627 and public statuses［DB/OL］. (2021-07-23)［2026-11-23］. https://api.github.com/repos/Uniswap/interface/deployments/397083627/statuses.
[26] UNISWAP. Announcement on restricting token access at app.uniswap.org［EB/OL］. (2021-07-23)［2026-11-23］. https://x.com/Uniswap/status/1418697012095164420.
[27] INTERNET ARCHIVE. Wayback Machine availability record for app.uniswap.org［DB/OL］. (2021-07-24)［2026-11-23］. https://archive.org/wayback/available?url=https%3A%2F%2Fapp.uniswap.org%2F&timestamp=20210724064834.
[28] JORROPO, CHRISSIEGENTHALER. Change the IPFS resolution of uniswap.eth from app.uniswap.org to uniswap-uncensored.eth: discussion, posts 1 and 3［EB/OL］. (2021-07-24)［2026-11-25］. https://gov.uniswap.org/t/13586.
[29] UNISWAP. Uniswap v3 core: commit e3589b1［CP/OL］. ［2026-11-23］. https://github.com/Uniswap/v3-core/tree/e3589b192d0be27e100cd0daaf6c97204fdb1899.
[30] ETHEREUM MAINNET. Uniswap v3 factory ownership transfer: transaction receipt, block 12369662［DB/OL］. ［2026-11-25］. https://etherscan.io/tx/0x05d1e9c2c48faf82547e00d527923f980576c5d337b6c666d0e91d07517c4b86.
[31] 0x PROJECT. ZeroEx proxy, UniswapV3Feature, SimpleFunctionRegistryFeature and OwnableFeature, commit b46eeadc64485288add5940a210e1a7d0bcb5481［CP/OL］. ［2026-11-23］. https://github.com/0xProject/protocol/tree/b46eeadc64485288add5940a210e1a7d0bcb5481/contracts/zero-ex/contracts/src.
[32] ETHEREUM MAINNET. sETH/WETH pool, Ethereum chain 1. Swap, receipts and payment traces, July 2021［DB/OL］. ［2026-11-23］. https://etherscan.io/address/0xbb6642dda99c7fb1ecf310baa3477fa7ba3e7c82.
[33] ETHEREUM MAINNET. Failed transaction receipt and trace, wallet A［DB/OL］. ［2026-11-25］. https://etherscan.io/tx/0xd118318743e650fe5cb828291b2680ae3c7f70e5bbd6486a64783c48efac53f2.
[34] ETHEREUM MAINNET. Failed transaction receipt and trace, wallet B［DB/OL］. ［2026-11-25］. https://etherscan.io/tx/0x5ed406aaef68eed286cc82fa17ec8d4fdcd6b685195891bdcdb374669deb1f19.
[35] CURVE. sETH pool, Ethereum mainnet. Verified source and contract ABI［CP/OL］. ［2026-11-23］. https://etherscan.io/address/0xc5424b857f758e906013f3555dad202e4bdb4567#code.
[36] UNISWAP. Uniswap v3 periphery: SwapRouter, Quoter, PeripheryPayments, v1.0.0［CP/OL］. ［2026-11-23］. https://github.com/Uniswap/v3-periphery/tree/v1.0.0/contracts.
[37] GO ETHEREUM. Ethereum RPC namespace: eth_simulateV1［EB/OL］. ［2026-11-23］. https://geth.ethereum.org/docs/interacting-with-geth/rpc/ns-eth.
