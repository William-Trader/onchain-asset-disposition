#!/usr/bin/env python3
"""Create the control-path diagram and cost figure for print."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parent
CJK = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
INK, BLUE, RED = '#17252D', '#1E4E5C', '#843E2A'
PALE, BLUSH, LINE = '#EDF4F5', '#F7EEEB', '#C9D4D7'


def mechanism(output):
    image = Image.new('RGB',(1950,715),'white')
    d = ImageDraw.Draw(image)

    def text(x,y,t,size,color=INK,strong=False,anchor='la'):
        d.text((x,y),t,font=ImageFont.truetype(BOLD if strong else CJK,size,index=2),fill=color,anchor=anchor)

    def card(x,y,w,title,detail,blocked=False):
        c,fill = (RED,BLUSH) if blocked else (BLUE,PALE)
        d.rounded_rectangle((x,y,x+w,y+115),radius=14,fill=fill,outline=c,width=3)
        text(x+w/2,y+32,title,37,c,True,'mm')
        text(x+w/2,y+81,detail,28,INK,False,'mm')

    def arrow(a,b,y,color=BLUE):
        d.line((a,y,b-12,y),fill=color,width=4)
        d.polygon(((b,y),(b-18,y-10),(b-18,y+10)),fill=color)

    text(35,5,'Mt.Gox · 2014 年 2 月',45,strong=True)
    xs,w = [35,506,977,1448],436
    card(xs[0],85,w,'原账户 BTC','平台账本记录权益')
    card(xs[1],85,w,'场内成交','账户余额仍可更新')
    card(xs[2],85,w,'平台链上出币受限','用户无法替代托管签名',True)
    card(xs[3],85,w,'用户自控地址','原账户对应 BTC 未提取')
    for i in (0,1): arrow(xs[i]+w+5,xs[i+1]-6,140)
    center=(xs[2]+w+xs[3])//2
    d.line((center-10,130,center+10,150),fill=RED,width=5)
    d.line((center-10,150,center+10,130),fill=RED,width=5)
    text(36,224,'后续追偿由法院程序及管财人组织。',30)
    d.line((35,287,1885,287),fill=LINE,width=3)

    text(35,301,'Uniswap v3 · 2021 年 7 月',45,strong=True)
    d.rounded_rectangle((505,362,1365,421),radius=14,fill=BLUSH,outline=RED,width=3)
    text(935,393,'官方网页入口受限（运营方公告）',33,RED,True,'mm')
    d.line((290,468,290,393,486,393),fill=RED,width=4)
    arrow(465,494,393,RED)
    card(xs[0],476,w,'原钱包 sETH','钱包签名与原代币付款')
    card(xs[1],476,w,'0x Exchange Proxy','第三方顶层执行合约')
    card(xs[2],476,w,'Uniswap v3 池','sETH 换得 WETH')
    card(xs[3],476,w,'原钱包收到 ETH','0x 解包 WETH 后付款')
    for i in range(3): arrow(xs[i]+w+5,xs[i+1]-6,531)
    text(36,627,'两笔实际交易的回执和调用轨迹均记录了这条路径。',30)
    image.save(output,dpi=(300,300),optimize=True)


def plot_costs(output, rows):
    font = FontProperties(fname=CJK)
    fig,ax = plt.subplots(figsize=(9.8,2.85),dpi=300)
    names = [('池费','pool_fee_component_bps','#1E4E5C',''),
             ('其余成交偏离','other_execution_component_bps','#82ABB0','//'),
             ('本笔 Gas','gas_component_bps','#D19D83','..')]
    baseline = [0,0]
    for label,key,color,hatch in names:
        values = [float(r[key]) for r in rows]
        ax.barh([1,0],values,left=baseline,height=.57,label=label,color=color,
                edgecolor='#4D5960',hatch=hatch,linewidth=.5,zorder=3)
        baseline = [l+v for l,v in zip(baseline,values)]
    for y, num in zip([1,0],baseline):
        ax.text(num+2,y,f'{num:.2f}',ha='left',va='center',fontsize=12,color=INK)
    ax.set(yticks=[1,0],xlim=(0,165),ylim=(-.55,1.55))
    ax.set_yticklabels(['样本 A','样本 B'],fontproperties=font,fontsize=12)
    ax.set_xlabel('相对交易前边际对价的成本（基点）',fontproperties=font,fontsize=11)
    ax.tick_params(axis='both',length=0,labelsize=11)
    ax.xaxis.set_major_locator(MultipleLocator(25))
    for s in ['top','left','right']: ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#8C9CA3')
    ax.grid(axis='x',color='#d3dee0',zorder=0)
    ax.legend(loc='upper center',bbox_to_anchor=(.46,1.24),ncol=3,frameon=False,prop=font,fontsize=11)
    fig.subplots_adjust(left=.112,right=.987,top=.78,bottom=.24)
    fig.savefig(output,dpi=300)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--derived',type=Path,default=ROOT.parent/'derived')
    parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args()
    costs=json.loads((args.derived/'threshold_summary.json').read_text())['costs']
    mechanism(args.output/'mechanism.png')
    plot_costs(args.output/'costs.png',costs[1:])
