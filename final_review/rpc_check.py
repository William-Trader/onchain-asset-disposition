"""Recheck the two witness transactions with a reader's archive node."""
import argparse
from wallet_probe import CUTOFF, calldata, fetch, rows

def main(url):
    assert int(fetch(url,'eth_chainId',[])['result'],16)==1
    holdings={r['sample']:r for r in rows('derived/holdings.csv')}
    sales=rows('evidence/derived/strict_native_0x.csv')[1:]
    for sample,s in zip('AB',sales,strict=True):
        wallet,token=s['sender'],s['sold_token']
        params=[{'to':token,'data':calldata('70a08231',wallet)},hex(CUTOFF)]
        assert int(fetch(url,'eth_call',params)['result'],16)==int(holdings[sample]['pre_day'])
        receipt=fetch(url,'eth_getTransactionReceipt',[s['hash']])['result']
        assert receipt['status']=='0x1' and receipt['from'].lower()==wallet and int(receipt['gasUsed'],16)==int(s['gas_used'])
        tx=fetch(url,'eth_getTransactionByHash',[s['hash']])['result']
        msg={key:tx[key] for key in ('from','to','gas','gasPrice','value')}
        msg['data']=tx['input']
        result=fetch(url,'eth_call',[msg,hex(int(s['block'])-1)])
        assert int(result['result'],16)==int(s['native_eth_wei'])
        print(sample,s['hash'],'balance, receipt and historical eth_call match')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    main(parser.parse_args().url)
