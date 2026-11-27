"""Frozen three-venue post14 pool-inflow and direct-wallet screen."""
import argparse, csv, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from protocol import ENDPOINTS, TRANSFER, calldata, dump, fetch, read, word

START, END = 12885655, 12974517
CUTOFF = 12879308  # Last block before July 23 UTC; excludes event-day inflows from old holdings.

def rows(path):
    with (ROOT / path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def seed():
    tokens = {r['address'] for r in rows('additions/derived/restricted_addresses.csv')}
    result = defaultdict(list)
    for r in rows('additions/derived/listed_swaps.csv'):
        if START <= int(r['block']) <= END:
            for i in range(2):
                token = r[f'token{i}']
                amount = int(r[f'net_token{i}_into_pool'])
                if token in tokens and amount > 0:
                    result[r['tx']].append((r, token, amount))
    return result

def rpc(provider, name, method, params, collect):
    path = HERE / 'raw' / (name + '_' + provider + '.json.gz')
    if not path.exists() and collect:
        response = fetch(ENDPOINTS[provider], method, params)
        if 'result' not in response or response['result'] is None:
            raise ValueError((name, response.get('error')))
        dump(path, dict(method=method, params=params, response=response))
    saved = read(path)
    assert (saved['method'], saved['params']) == (method, params)
    return saved['response']['result']

def transfer(log, token):
    t = log['topics']
    if log['address'].lower() == token and len(t)==3 and t[0]==TRANSFER and len(log['data'])==66:
        return '0x'+t[1][-40:].lower(), '0x'+t[2][-40:].lower(), int(log['data'], 16)

def match(item, collect):
    transaction, legs = item
    receipt = rpc('d', 'receipt_'+transaction, 'eth_getTransactionReceipt', [transaction], collect)
    assert receipt['status']=='0x1' and receipt['transactionHash'].lower()==transaction
    wallet = receipt['from'].lower(); matches=[]
    for e,token,amount in legs:
        assert receipt['blockHash'].lower()==e['block_hash']
        swap = next(l for l in receipt['logs'] if int(l['logIndex'],16)==int(e['log_index']))
        assert swap['address'].lower()==e['pool']
        log_index = int(e['log_index'])
        same_tx = [(int(l['logIndex'],16), transfer(l,token)) for l in receipt['logs']]
        sent = [i for i,t in same_tx if t==(wallet,e['pool'],amount) and i<log_index]
        if len(sent) != 1:
            continue
        if sum(t[2] for i,t in same_tx if t and t[:2]==(wallet,e['pool']) and i<log_index) != amount:
            continue
        inbound = sum(t[2] for i,t in same_tx if t and t[1]==wallet and i<sent[0])
        matches.append(dict(wallet=wallet,token=token,amount=amount,block=int(e['block']),tx=transaction,
                            swap_log=log_index,transfer_log=sent[0],same_tx_inbound=inbound))
    return transaction,wallet,matches

def check_wallet(row, collect):
    wallet,token,block=row['wallet'],row['token'],row['block']
    suffix=token+'_'+wallet
    params=[dict(to=token,data=calldata('70a08231',wallet)),hex(CUTOFF)]
    balances=[int(rpc(p,'old_'+suffix,'eth_call',params,collect),16) for p in 'td']
    assert balances[0]==balances[1]
    filt=dict(address=token,fromBlock=hex(CUTOFF+1),toBlock=hex(block),topics=[TRANSFER,None,'0x'+word(wallet)])
    logs=rpc('t','incoming_'+suffix,'eth_getLogs',[filt],collect)
    cross=rpc('a','incoming_'+suffix,'eth_getLogs',[filt],collect)
    key=lambda l:(l['blockHash'].lower(),l['transactionHash'].lower(),int(l['logIndex'],16),l['data'],tuple(l['topics']))
    assert {key(l) for l in logs}=={key(l) for l in cross}
    inc=[l for l in logs if int(l['blockNumber'],16)<block or int(l['logIndex'],16)<row['transfer_log']]
    total=sum(transfer(l,token)[2] for l in inc)
    # Upper bound on post-cutoff units available in the wallet. Matching logs
    # do not identify individual ERC-20 units or the final output recipient.
    forced_old=max(0,row['amount']-total)
    pre_old=balances[0]
    return {**row,'cutoff_balance':pre_old,'post_cutoff_inbound_before_payment':total,
            'forced_old_minimum':forced_old,'status':('indeterminate_log_balance' if forced_old>pre_old
             else 'all_old_under_transfer_accounting' if forced_old==row['amount'] else
             'mixed_minimum_old' if forced_old else 'no_positive_lower_bound')}

def write(out,name,items):
    with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(items[0])); w.writeheader();w.writerows(items)

def main(out, collect):
    out.mkdir(parents=True,exist_ok=True)
    candidates=seed()
    with ThreadPoolExecutor(5 if collect else 3) as ex:
        receipts=list(ex.map(lambda item:match(item,collect),candidates.items()))
        qualified={}
        for _,_,parts in receipts:
            for x in parts:
                key=(x['wallet'],x['token'])
                if key not in qualified:
                    qualified[key]=x
        print('Matched',len(receipts),len(qualified),flush=True)
        items=list(ex.map(lambda item:check_wallet(item,collect),qualified.values()))
    write(out,'wallet_inflow_candidates.csv',[dict(tx=h,transaction_sender=w,direct_inflow_legs=len(m)) for h,w,m in receipts])
    write(out,'wallet_inventory_probe.csv',items)
    print('Wallets',len({w for _,w,_ in receipts}),len({r['wallet'] for r in items}),dict(Counter(r['status'] for r in items)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect',action='store_true')
    p.add_argument('--out',type=Path,default=HERE/'derived')
    a=p.parse_args();main(a.out,a.collect)
