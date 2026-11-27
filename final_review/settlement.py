"""Follow the 14 first observed direct payments with a positive old-balance bound."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from statistics import median
from wallet_probe import HERE, rpc, rows, seed, transfer, write, calldata, CUTOFF, TRANSFER, word

WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
WITHDRAWAL = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'
V2_SWAP = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
V2_FACTORY = '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f'

def value(log):
    return int(log['logIndex'], 16)

def receipt_fields(receipt):
    logs = tuple((l['address'].lower(), value(l), tuple(l['topics']), l['data']) for l in receipt['logs'])
    return (receipt['status'], receipt['blockHash'], receipt['from'].lower(), receipt['gasUsed'], receipt['effectiveGasPrice'], logs)

def successful_calls(trace):
    failed = {tuple(s['traceAddress']) for s in trace if s.get('error')}
    result = []
    for frame in trace:
        path = tuple(frame['traceAddress'])
        if frame.get('type') != 'call' or frame['action'].get('callType') != 'call':
            continue
        if any(path[:n] in failed for n in range(len(path)+1)):
            continue
        action = frame['action']
        amount = int(action.get('value', '0x0'), 16)
        if amount:
            result.append((path, action['from'].lower(), action['to'].lower(), amount))
    return result

def confirm_pair(pool, token_a, token_b, block, collect):
    a, b = sorted((token_a, token_b))
    args = [{'to': V2_FACTORY, 'data': calldata('e6a43905', a, b)}, hex(block)]
    key = f'pair_{block}_{pool}_{a}_{b}'
    observed = [rpc(p, key, 'eth_call', args, collect) for p in ('t', 'd')]
    return all('0x'+r[-40:].lower() == pool for r in observed)

def confirm_inventory(item, collect):
    wallet, token = item['wallet'], item['token']
    key = token+'_'+wallet
    block, payment = int(item['block']),int(item['transfer_log'])
    params = [dict(to=token,data=calldata('70a08231',wallet)),hex(block-1)]
    observed = [int(rpc(p,'settlement_balance_'+key,'eth_call',params,collect),16) for p in ('t','d')]
    search = dict(address=token,fromBlock=hex(CUTOFF+1),toBlock=hex(block))
    receiver = dict(search,topics=[TRANSFER,None,'0x'+word(wallet)])
    sender = dict(search,topics=[TRANSFER,'0x'+word(wallet)])
    incoming = rpc('t','incoming_'+key,'eth_getLogs',[receiver],False)
    debits = [rpc(p,'settlement_out_'+key,'eth_getLogs',[sender],collect) for p in ('t','a')]
    identity = lambda l:(l['blockHash'],l['transactionHash'],value(l),tuple(l['topics']),l['data'])
    assert set(map(identity,debits[0]))==set(map(identity,debits[1]))
    def amounts(entries, include):
        return sum(transfer(l,token)[2] for l in entries if include(l))
    earlier = lambda l: int(l['blockNumber'],16)<block
    pre_block = int(item['cutoff_balance']) + amounts(incoming,earlier)-amounts(debits[0],earlier)
    same_block_before = lambda l: int(l['blockNumber'],16)==block and value(l)<payment
    pre_pay = pre_block + amounts(incoming,same_block_before)-amounts(debits[0],same_block_before)
    assert pre_block == observed[0] == observed[1] and pre_pay >= int(item['amount'])
    return pre_block,pre_pay

def scan(item, candidates, symbols, collect):
    h, wallet, token = item['tx'], item['wallet'], item['token']
    receipt = rpc('d','receipt_'+h,'eth_getTransactionReceipt',[h],False)
    cross = rpc('t','arrival_'+h,'eth_getTransactionReceipt',[h],collect)
    assert receipt_fields(receipt) == receipt_fields(cross) and receipt['status']=='0x1'
    assert receipt['from'].lower() == wallet
    trace = rpc('d','settlement_'+h,'trace_transaction',[h],collect)
    assert trace[0]['blockHash'].lower() == receipt['blockHash'].lower() and not trace[0].get('error')
    assert trace[0]['transactionHash'].lower() == h and trace[0]['action']['from'].lower() == wallet
    pair_log, _, pa = next((e,t,a) for e,t,a in candidates[h] if e['log_index']==item['swap_log'] and t==token)
    logs = sorted(receipt['logs'], key=value)
    pre_block,pre_pay = confirm_inventory(item,collect)
    transfers = [(value(l), l['address'].lower(), t) for l in logs if (t:=transfer(l,l['address'].lower()))]
    side = 1 if token == pair_log['token0'] else 0
    output = pair_log[f'token{side}']
    expected = -int(pair_log[f'net_token{side}_into_pool'])
    pool = pair_log['pool']
    # V3 may pay the output before its callback collects the input.
    first_index = -1 if pair_log['venue']=='v3' else int(item['transfer_log'])
    swap_index = int(item['swap_log'])
    block = int(item['block'])
    assert pa == int(item['amount']) and expected>0
    hops = [pool]
    payment_logs = [int(item['transfer_log'])]
    call_path = ''
    final_token = ''
    final_amount = 0
    while len(hops) <= 3:
        payouts = [(idx,t[1]) for idx,a,t in transfers
                   if a==output and t[0]==pool and t[2]==expected and first_index<idx<swap_index]
        if len(payouts)!=1:
            break
        received_at, recipient = payouts[0]
        payment_logs.append(received_at)
        if recipient==wallet:
            net = sum(q*((dst==wallet)-(src==wallet)) for _,a,(src,dst,q) in transfers if a==output)
            if net == expected:
                final_token,final_amount=output,net
            break
        if output==WETH:
            withdrawals=[l for l in logs if value(l)>swap_index and l['address'].lower()==WETH
                         and l['topics'][0]==WITHDRAWAL and '0x'+l['topics'][1][-40:].lower()==recipient
                         and int(l['data'],16)==expected]
            calls = successful_calls(trace)
            debits = [(p,v) for p,f,t,v in calls if f==WETH and t==recipient and v==expected]
            native = [(p,v) for p,f,t,v in calls if f==recipient and t==wallet and v==expected]
            wallet_net=sum(n*((t==wallet)-(f==wallet)) for _,f,t,n in calls)
            if len(withdrawals)==len(debits)==len(native)==1 and debits[0][0]<native[0][0] and wallet_net==expected:
                payment_logs.append(value(withdrawals[0]))
                call_path='.'.join(map(str,native[0][0]))
                final_token,final_amount='ETH',expected
                break
        swaps=[l for l in logs if l['address'].lower()==recipient and l['topics'][0]==V2_SWAP and value(l)>swap_index]
        if len(swaps)!=1 or recipient in hops or len(hops)>=3:
            break
        nxt=swaps[0]
        transfers_out=[(i,b,t) for i,b,t in transfers if t[0]==recipient and swap_index<i<value(nxt)]
        if len(transfers_out)!=1:
            break
        _, target, (sender, receiver, payment) = transfers_out[0]
        if target==output:
            break
        data=bytes.fromhex(nxt['data'][2:])
        if len(data)!=128:
            break
        fields=[int.from_bytes(data[i:i+32],'big') for i in range(0,128,32)]
        actual=[expected,0,0,payment] if output<target else [0,expected,payment,0]
        if fields!=actual or not confirm_pair(recipient,output,target,block,collect):
            break
        hops.append(recipient)
        first_index,swap_index,pool,output,expected=received_at,value(nxt),recipient,target,payment
    fee = int(receipt['gasUsed'],16)*int(receipt['effectiveGasPrice'],16)
    return {**item,'symbol':symbols[token], 'venue':pair_log['venue'],'pool_hops':len(hops),
            'pools':';'.join(hops),'transfer_log_indices':';'.join(map(str,payment_logs)),
            'eth_recipient_trace':call_path,'output_asset':final_token,
            'output_amount_raw':final_amount,'network_fee_wei':fee,
            'balance_before_sale_block_raw':pre_block,'balance_before_payment_raw':pre_pay,
            'net_eth_after_network_fee_wei':final_amount-fee if final_token=='ETH' else '',
            'status_settlement':'closed' if final_token else 'unresolved'}

def main(out, input_csv, collect):
    candidates=seed()
    symbols={x['address']:x['symbol'] for x in rows('additions/derived/restricted_addresses.csv')}
    items=[x for x in rows(input_csv) if int(x['forced_old_minimum'])>0 and x['status']!='indeterminate_log_balance']
    assert len({(r['wallet'],r['token']) for r in items})==len(items)
    with ThreadPoolExecutor(max_workers=4 if collect else 2) as pool:
        results=list(pool.map(lambda item: scan(item,candidates,symbols,collect),items))
    closed=[x for x in results if x['status_settlement']=='closed']
    full=[x for x in closed if x['status']=='all_old_under_transfer_accounting']
    sizes=dict(candidates=len(items), closed=len(closed), all_old=len(full), part_old=len(closed)-len(full),
               unique_addresses=len({x['wallet'] for x in closed}), unique_assets=len({x['token'] for x in closed}),
               venues=dict(Counter(x['venue'] for x in closed)), routes=dict(Counter(x['pool_hops'] for x in closed)),
               outputs=dict(Counter(x['output_asset'] for x in closed)))
    eth=[r for r in closed if r['output_asset']=='ETH']
    sizes.update(native_eth=len(eth), wrapped_eth=sum(r['output_asset']==WETH for r in closed),
                 other_erc20=len(closed)-len(eth)-sum(r['output_asset']==WETH for r in closed),
                 native_fee_over_proceeds=sum(r['net_eth_after_network_fee_wei']<0 for r in eth),
                 single_hop=sum(r['pool_hops']==1 for r in closed),
                 two_hop=sum(r['pool_hops']==2 for r in closed),
                 three_hop=sum(r['pool_hops']==3 for r in closed))
    ratios=[Decimal(10000*r['network_fee_wei'])/r['output_amount_raw'] for r in eth]
    sizes['native_median_fee_bps']=format(median(ratios),'.2f')
    print(sizes)
    out.mkdir(parents=True,exist_ok=True)
    write(out,'settlement_rows.csv',results)
    write(out,'settlement_summary.csv',[{k:v for k,v in sizes.items() if not isinstance(v,dict)}])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=type(HERE),default=HERE/'derived')
    parser.add_argument('--input',type=type(HERE),default=HERE/'derived/wallet_inventory_probe.csv')
    parser.add_argument('--collect',action='store_true')
    args=parser.parse_args()
    main(args.out,args.input,args.collect)
