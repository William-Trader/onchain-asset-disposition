#!/usr/bin/env python3
"""Build four editable classroom slides with 15-minute speaker notes."""
import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

FONT = 'Noto Sans CJK SC'
BG, INK, MUTED = 'F7F9F9','182830','4B5F66'
TEAL, PALE, WHITE = '20505C','E6F0F0','FFFFFF'
RED, BLUSH, RULE = '843F29','F5EAE4','D4DDDF'
TITLE = '数字资产交易服务受限下的用户资产处置能力'


def rgb(value):
    return RGBColor.from_string(value)


def rect(slide, x, y, w, h, fill, outline=None, rounded=False):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = rgb(fill)
    if outline:
        box.line.color.rgb = rgb(outline)
        box.line.width = Pt(1)
    else:
        box.line.fill.background()
    if rounded:
        box.adjustments[0] = .1
    return box


def text(slide, x, y, w, h, value, size, color=INK, bold=False, align=PP_ALIGN.LEFT):
    frame = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left=frame.margin_right=Pt(0)
    frame.margin_top=frame.margin_bottom=Pt(0)
    frame.vertical_anchor=MSO_ANCHOR.MIDDLE
    for i,line in enumerate(value.split('\n')):
        p = frame.paragraphs[0] if i==0 else frame.add_paragraph()
        p.alignment=align
        p.space_before=p.space_after=Pt(0)
        p.line_spacing=1.15
        run=p.add_run()
        run.text=line
        run.font.name=FONT
        run.font.size=Pt(size)
        run.font.bold=bold
        run.font.color.rgb=rgb(color)
        rpr=run._r.get_or_add_rPr()
        ea=OxmlElement('a:ea')
        ea.set('typeface',FONT)
        rpr.append(ea)
    return frame


def base(deck,title,sub,source,i):
    slide=deck.slides.add_slide(deck.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb=rgb(BG)
    rect(slide,.63,.56,.07,.44,TEAL)
    text(slide,.81,.52,11.71,.55,title,28,INK,True)
    text(slide,.81,1.19,11.71,.34,sub,14,MUTED)
    rect(slide,.64,6.86,12.04,.013,RULE)
    text(slide,.66,6.99,11.44,.25,source,8.8,MUTED)
    text(slide,12.15,6.97,.51,.27,str(i),11,MUTED,align=PP_ALIGN.RIGHT)
    return slide


def card(s,x,y,w,h,face,title,subtitle,blocked=False):
    fill=BLUSH if blocked else face
    color=RED if blocked else TEAL
    rect(s,x,y,w,h,fill,rounded=True)
    text(s,x+.20,y+.17,w-.40,.47,title,18,color,True,PP_ALIGN.CENTER)
    text(s,x+.20,y+.72,w-.40,h-.82,subtitle,12.5,INK,align=PP_ALIGN.CENTER)


def note(s,message):
    s.notes_slide.notes_text_frame.text=message


def make(output):
    deck=Presentation()
    deck.slide_width,deck.slide_height=Inches(13.333),Inches(7.5)
    deck.core_properties.title=TITLE+' 课堂展示'
    deck.core_properties.author='周家乐'
    s=base(deck,'交易继续，原账户 BTC 仍无法提取','2014 年 2 月 7 日，Mt.Gox 暂停 BTC 提现 · 周家乐',
           '来源  Winklevoss Bitcoin Trust，2014 年 Form S-1 修订稿；Mt.Gox，2014 年 2 月 28 日公告',1)
    starts=[.81,4.88,8.96]
    card(s,starts[0],2.35,3.56,1.65,PALE,'原账户 BTC','平台账本记录用户权益')
    card(s,starts[1],2.35,3.56,1.65,PALE,'场内成交','内部余额仍可更新')
    card(s,starts[2],2.35,3.56,1.65,PALE,'链上提现暂停','外部出币依赖托管方签名',True)
    for x,mark,c in [(4.39,'→',TEAL),(8.46,'×',RED)]:
        text(s,x,2.83,.45,.55,mark,25,c,True,PP_ALIGN.CENTER)
    text(s,.85,4.72,11.4,.65,'用户更换交易场所，也无法提走原账户的 BTC。',21,INK,True)
    note(s,'3 分钟。用一个简单问题开场：如果市场还允许下单，账户里原来的 BTC 能提走吗？说明场内记账、平台签名和个人控制地址的不同。SEC 资料是发行人向 SEC 提交的文件。2 月 28 日公告和后来民事再生用于说明后续程序。过渡：把必要权限拆开，才能比较两个不同案例。')

    s=base(deck,'129 个名单地址，只有 sETH 出现成交','以太坊主网 · 固定名单 · 前后各 14 个完整 UTC 日',
           '来源  Uniswap 界面提交 4078390；Vercel 部署 397083627；主网 Factory 和 Swap 日志',2)
    rect(s,.78,1.84,6.14,3.68,WHITE,RULE,True)
    text(s,1.04,2.05,5.7,.34,'官方网页限制的时间证据（UTC）',15,TEAL,True)
    for i,(stamp,v) in enumerate([('7 月 23 日 22:05:14','限制名单代码提交'),
                                  ('7 月 23 日 22:05:20','创建 Production 部署记录'),
                                  ('7 月 23 日 22:18:20','官方声明已开始限制'),
                                  ('7 月 24 日 06:48:34','首笔后窗链上闭环')]):
        y=2.53+i*.63
        text(s,1.05,y,2.7,.40,stamp,12.3,MUTED)
        text(s,3.77,y,2.84,.40,v,12.4,INK,True)
        if i!=3:rect(s,1.04,y+.50,5.56,.010,RULE)
    rect(s,7.20,1.84,5.34,3.68,PALE,rounded=True)
    for i,(num,v) in enumerate([('129','名单地址逐一筛查'),('6','名单资产匹配到 7 个池'),('1','观察窗内有成交的名单资产')]):
        y=2.13+i*.96
        text(s,7.48,y,1.45,.63,num,31,TEAL,True)
        text(s,8.86,y,3.35,.65,v,14.4,INK)
    text(s,.85,5.78,11.75,.48,'历史存档索引早于首笔交易，但没有可验证的生产脚本来确定官方域名生效秒点。',13.5,MUTED)
    note(s,'4 分钟。先读时间轴：Git 提交、创建部署记录、官方声明各自能证明什么。历史首页存档索引为次日 06:36:00，无法核验脚本。再解释样本选择：从 3739 条主网 v3 建池日志去找名单中的任一端，共 6 个代币、7 个池。前后各 14 天只有 sETH 成交。研究报告的两个后窗闭环都在后 7 天，窗口翻倍结果相同。')

    s=base(deck,'同一钱包付出原 sETH，收到原生 ETH','两笔真实交易均经 0x 与同一个 Uniswap v3 池',
           '来源  主网样本 A 0xcf44…8c53、样本 B 0x23f7…f89e；Tenderly 与 dRPC 回执及调用轨迹',3)
    for j,(lab,day,amount,received,gas) in enumerate([
        ('样本 A','7 月 24 日','0.5626','0.565085179','0.687%'),
        ('样本 B','7 月 27 日','0.4154','0.416331959','1.097%')]):
        x=.81+6.02*j
        rect(s,x,1.90,5.68,2.14,PALE,rounded=True)
        text(s,x+.24,2.09,2.55,.35,f'{lab} · {day}',14.5,TEAL,True)
        text(s,x+.24,2.62,5.15,.48,amount+' sETH → '+received+' ETH',19.5,INK,True)
        text(s,x+.25,3.24,5.14,.36,'网络费占该笔实收 '+gas,12,MUTED)
    rect(s,.82,4.40,11.70,.68,WHITE,RULE,True)
    text(s,1.08,4.54,11.19,.36,'资金流  原钱包付 sETH → v3 池给出 WETH → 0x 解包 → ETH 付回原地址',
         15.3,TEAL,True,PP_ALIGN.CENTER)
    text(s,.85,5.48,11.62,.62,'两节点归档复核  门槛等于实际到账时成功，提高 1 wei 即回滚。',15.5,INK)
    note(s,'5 分钟。用 A 样本解释成功回执、ERC-20 转账、Swap 与原生收款为什么要一起核对。B 用独立地址重复了同样的证据。比较 Gas 百分比，不把这两笔的费用当成普通用户平均成本。实验在原历史状态中只改变最低到账门槛。三笔含前窗对照，105 个设定、210 次双节点调用，没有广播。')

    s=base(deck,'资产处置取决于必要权限和替代路径','数字资产交易服务受限下的用户资产处置能力 · 周家乐',
           '完整论文与复现包  历史名单、双源日志、调用轨迹、归档实验输入输出及程序',4)
    for idx,(title,detail) in enumerate([('可调用','先定位受限环节及谁有执行权'),
                                        ('可完成','核验原资产扣款和最终收款'),
                                        ('成本可承担','分别衡量池费、价格偏离和 Gas')]):
        card(s,.81+idx*3.96,1.91,3.72,1.7,PALE,title,detail)
    rect(s,.83,4.04,11.66,1.76,WHITE,RULE,True)
    text(s,1.07,4.17,11.15,.50,'Mt.Gox 的平台出币权无法由原账户用户替代。',16.5,INK,True)
    text(s,1.07,4.68,11.15,.50,'sETH 样本证明公告后已有另一条路径完成原资产处置。',16.5,TEAL,True)
    text(s,.89,6.13,11.6,.29,'已成交日志缺少所有用户尝试的分母，无法据此估计总体成功率。',12.7,MUTED)
    note(s,'3 分钟。回到开场问题。Mt.Gox 说明托管签名不可由用户替代；sETH 的两笔交换说明替代路径曾经实际闭环。强调这是非对称的机制比较。链上数据看不到失败的前端尝试，不能计算总体成功率，也不知道用户具体选择的网页。用最后一句收尾：先问原资产的指定操作是否能完成，再讨论用户是否真正拥有可行的退出选择。')
    deck.save(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    make(parser.parse_args().output)
