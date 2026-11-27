"""Rebuild phase diagnostics, event intervals and route-fee break-even values."""
import argparse, csv, gzip, json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from wallet_probe import HERE, ROOT, rows, write

D=Decimal
def price(path):
    with gzip.open(ROOT/path,'rt',encoding='utf-8-sig',newline='') as f:
        return {r['Time'][:10]:D(r['avg']) for r in csv.DictReader(f) if r['avg']}

def market(out):
    sources=dict(mtgox='raw/mtgox.csv.gz',stamp='raw/bitstamp.csv.gz',finex='raw/bitfinex.csv.gz',
                 btce='additions/raw/btce_USD_price.csv.gz',kraken='additions/raw/kraken_USD_price.csv.gz')
    src={k:price(f) for k,f in sources.items()}
    day=rows('additions/derived/market_by_day.csv')
    base={t['utc']:t for t in day}
    ranges=[('pre14','2014-01-24','2014-02-06'),('halt_day','2014-02-07','2014-02-07'),
            ('post_days_1_7','2014-02-08','2014-02-14'),('post_days_8_14','2014-02-15','2014-02-21'),
            ('post14','2014-02-08','2014-02-21'),('post_halt_pre_shutdown','2014-02-08','2014-02-23'),
            ('shutdown_day','2014-02-24','2014-02-24'),('after_shutdown_before_filing','2014-02-25','2014-02-27'),
            ('filing_day','2014-02-28','2014-02-28')]
    daily=[]
    for d in sorted(t for t in src['mtgox'] if ranges[0][1]<=t<=ranges[-1][2]):
        p=src['mtgox'][d];stamp=src['stamp'].get(d)
        ds=[src[k].get(d) for k in ('stamp','finex','btce','kraken')]
        ref=median(ds) if all(v and v>0 for v in ds) else None
        assert d in base or d>day[-1]['utc']
        daily.append(dict(utc=d,mtgox_price=p,bitstamp=stamp,four_venue_median=ref,
                          bitstamp_pct=100*(p/stamp-1) if p>0 and stamp else None,
                          basket_pct=100*(p/ref-1) if p>0 and ref else None))
    stats=[]
    for name,start,end in ranges:
        selected=[r for r in daily if start<=r['utc']<=end]
        vals=lambda k:[x[k] for x in selected if x[k] is not None]
        s=vals('bitstamp_pct');b=vals('basket_pct')
        stats.append(dict(period=name,start=start,end=end,raw_rows=len(selected),valid_stamp=len(s),valid_basket=len(b),
                          bitstamp_pct=median(s) if s else None,basket_pct=median(b) if b else None))
    write(out,'market_phase_days.csv',daily)
    write(out,'market_phases.csv',stats)

def fees(out):
    scenarios={(r['sample'],r['scenario']):r for r in rows('derived/counterfactuals.csv')}
    results=[]
    for w in ('B','A'):
        replay=scenarios[w,'replay'];real=int(replay['net_eth_wei'])
        for path in ('replay','router_approved','curve_approved'):
            row=scenarios[w,path]
            g,n,p=map(int,(row['gross_eth_wei'],row['net_eth_wei'],row['gas_price_wei']))
            approved=int(row['approval_gas'])
            expected=int(row['swap_gas'])*p+approved*p
            assert g-n==expected
            headroom=n-real
            results.append(dict(sample=w,path=path,minimum_fee_budget_bps=10000*D(expected)/g,
                    net_difference_vs_0x_wei=headroom,extra_fee_headroom_bps=10000*D(headroom)/g,
                    maximum_approval_gas_at_equal_net=(g-int(row['swap_gas'])*p-real)//p if path!='replay' else ''))
    write(out,'route_thresholds.csv',results)

def times(out):
    state=json.loads((ROOT/'evidence/derived/deployment_summary.json').read_text())
    ann=datetime.fromisoformat(state['official_announcement_utc'])
    sales=rows('evidence/derived/strict_native_0x.csv')[1:]
    write(out,'announcement_intervals.csv',[
        dict(sample=w,starting_timestamp=ann.isoformat(),sale_timestamp=r['utc'],
             elapsed_seconds=int((datetime.fromisoformat(r['utc'])-ann).total_seconds()))
        for w,r in zip('AB',sales,strict=True)])
    write(out,'wallet_screen_totals.csv',[dict(status=s,count=n) for s,n in sorted(Counter(
        r['status'] for r in rows('final_review/derived/wallet_inventory_probe.csv')).items())])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=HERE/'derived')
    out=p.parse_args().out;out.mkdir(exist_ok=True,parents=True)
    market(out);fees(out);times(out)
