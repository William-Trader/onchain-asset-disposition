#!/usr/bin/env python3
"""Test exact output boundaries and reconstruct pool fees at historical block state."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, getcontext

from census import ROOT, cache, endpoint, log_key, need, number, read, rpc, signed, words, write_csv

getcontext().prec = 78
Q96 = 1 << 96
ONE = 10**18
SWAP_TOPIC = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
LIQUIDITY = '0x1a686502'
SPACING = '0xd0c93a7c'
SLOT0 = '0x3850c7bd'
BITMAP = '0x5339c296'
TICKS = '0xf30dba93'
GAS_FIELDS = ('from','to','gas','gasPrice','value')
BS_UNDERBOUGHT = b'UniswapV3Feature/UNDERBOUGHT'


def fixtures(summary):
    return json.loads(summary.read_text(encoding='utf-8'))['strict_paths']


def thresholds(out_wei, original):
    levels = {out_wei: 'exact', original: 'original', 0: 'zero'}
    for offset in (1, 2, 10, 100, 1_000, 10**6, 10**9, 10**12):
        levels[out_wei-offset] = '-wei-' + str(offset)
        levels[out_wei+offset] = '+wei-' + str(offset)
    for bps in (1, 5, 10, 25, 50, 100, 250, 500):
        offset = out_wei * bps // 10_000
        levels.setdefault(out_wei-offset,'-bps-' + str(bps))
        levels.setdefault(out_wei+offset,'+bps-' + str(bps))
    return sorted(levels.items())


def params(tx, minimum, historical_block):
    data = tx['input']
    start = 10 + 2 * 64
    modified = data[:start] + f'{minimum:064x}' + data[start + 64:]
    entry = {name: tx[name] for name in GAS_FIELDS}
    entry['data'] = modified
    return [entry, hex(historical_block)]


def decode_replay(payload, expected_request):
    request, response = payload['request'], payload['response']
    need(request['method'] == 'eth_call' and request['params'] == expected_request, 'not the same historic state/call')
    if 'result' in response and isinstance(response['result'], str):
        return 'success', number(response['result'])
    raw_error = response.get('error', {}).get('data')
    need(isinstance(raw_error, str) and raw_error.startswith('0x08c379a0'), 'not a verified protocol revert')
    contents = bytes.fromhex(raw_error[10:])
    offset = int.from_bytes(contents[:32], 'big')
    size = int.from_bytes(contents[offset:offset+32], 'big')
    detail = contents[offset+32:offset+32+size]
    need(detail == BS_UNDERBOUGHT, f'invalid revert reason: {detail!r}')
    return 'revert', detail.decode()


# Multipliers from the fixed version of Uniswap v3-core TickMath.sol.
TICK_MULTIPLIERS = tuple(int(x, 16) for x in (
    'fffcb933bd6fad37aa2d162d1a594001', 'fff97272373d413259a46990580e213a',
    'fff2e50f5f656932ef12357cf3c7fdcc', 'ffe5caca7e10e4e61c3624eaa0941cd0',
    'ffcb9843d60f6159c9db58835c926644', 'ff973b41fa98c081472e6896dfb254c0',
    'ff2ea16466c96a3843ec78b326b52861', 'fe5dee046a99a2a811c461f1969c3053',
    'fcbe86c7900a88aedcffc83b479aa3a4', 'f987a7253ac413176f2b074cf7815e54',
    'f3392b0822b70005940c7a398e4b70f3', 'e7159475a2c29b7443b29c7fa6e889d9',
    'd097f3bdfd2022b8845ad8f792aa5825', 'a9f746462d870fdf8a65dc1f90e061e5',
    '70d869a156d2a1b890bb3df62baf32f7', '31be135f97d08fd981231505542fcfa6',
    '9aa508b5b7a84e1c677de54f3e99bc9', '5d6af8dedb81196699c329225ee604',
    '2216e584f5fa1ea926041bedfe98', '48a170391f7dc42444e8fa2'))


def ceildiv(n, d):
    return (n + d - 1) // d


def sqrt_at_tick(tick):
    exponent = abs(tick)
    need(exponent <= 887272, 'tick exceeds the v3 domain')
    ratio = 1 << 128
    for bit, amount in enumerate(TICK_MULTIPLIERS):
        if exponent & (1 << bit):
            ratio = (ratio * amount) >> 128
    if tick > 0:
        ratio = ((1 << 256) - 1) // ratio
    return ceildiv(ratio, 1 << 32)


def crossings(state, start_tick, end_tick, spacing):
    left, right = end_tick//spacing, start_tick//spacing
    need(left//256 == right//256 and end_tick % spacing != 0,
         'this reconstruction requires the observed path to stay in one tick-bitmap word')
    bitmap = number(state['bitmap0'])
    return sorted((i*spacing for i in range(left+1, right+1) if bitmap & (1 << (i%256))), reverse=True)


def route_fee(history, receipt, state):
    # All three direct 0x sales were exact-input token0 -> token1 swaps within one bitmap word.
    p = history['pool']
    legs = [e for e in receipt['logs'] if e['address'].lower() == p and e['topics'][0] == SWAP_TOPIC]
    need(len(legs) == 1, 'fee reconstruction needs one Swap')
    log = legs[0]
    a0, a1, end_sqrt, end_L, end_tick = words(log['data'])
    sold, gross, fee = history['input_raw'], history['native_eth_wei'], history['pool_fee']
    need(signed(a0) == sold and -signed(a1) == gross, 'event delta mismatch')
    pslot = words(state['slot0'])
    start_sqrt, start_tick = pslot[0], signed(pslot[1])
    end_tick = signed(end_tick)
    spacing = number(state['spacing'])
    liquidity = number(state['liquidity'])
    need(start_tick >= end_tick and start_sqrt > end_sqrt and liquidity > 0, 'unsupported direction/state')
    block_logs = state['all_pool_logs']
    need(len(block_logs) == 1 and block_logs[0]['blockHash'] == receipt['blockHash']
         and block_logs[0]['transactionHash'] == history['hash']
         and block_logs[0]['logIndex'] == log['logIndex'], 'pre-block price or liquidity may have changed')
    crossed = crossings(state,start_tick,end_tick,spacing)
    need(set(state['ticks']) == {str(tick) for tick in crossed}, 'incomplete initialized tick data')
    fee_total, paid_total, remaining = 0, 0, sold
    steps = []
    sqrt = start_sqrt
    for tick in crossed + [None]:
        target = sqrt_at_tick(tick) if tick is not None else end_sqrt
        need(sqrt >= target and target > 0 and liquidity > 0, 'invalid price-moving step')
        used = ceildiv(ceildiv((liquidity << 96)*(sqrt-target),sqrt),target)
        out = liquidity*(sqrt-target)//Q96
        less_fee = remaining*(1_000_000-fee)//1_000_000
        need(less_fee >= used, 'full input cannot fund step')
        if tick is None:
            q = liquidity << 96
            predicted = ceildiv(q*sqrt, q + less_fee*sqrt)
            need(predicted == end_sqrt, 'historical terminal sqrtPriceX96 mismatch')
            fee_step = remaining - used
        else:
            fee_step = ceildiv(used*fee,1_000_000-fee)
        need(fee_step >= 0 and used+fee_step <= remaining, 'step charges exceed remaining')
        steps.append({'ending_tick':tick,'liquidity':liquidity,'start_sqrt':sqrt,'end_sqrt':target,
                      'net_input_raw':used,'output_raw':out,'fee_input_raw':fee_step})
        paid_total += out
        fee_total += fee_step
        remaining -= used + fee_step
        sqrt = target
        if tick is not None:
            tick_state = words(state['ticks'][str(tick)])
            need(tick_state[0] > 0 and tick_state[-1] == 1, 'crossed tick was not initialized')
            liquidity -= signed(tick_state[1])
    need(remaining == 0 and paid_total == gross and liquidity == end_L, 'replay sums do not match receipt')
    return start_sqrt, end_sqrt, number(state['liquidity']), start_tick, end_tick, spacing, fee_total, steps


def reconstruct(state, history, receipt):
    s0, s1, liquidity, t0, t1, spacing, exact_pool_fee, steps = route_fee(history, receipt, state)
    sold = history['input_raw']
    gross = history['native_eth_wei']
    nominal_fee = history['pool_fee']
    baseline_ETH = Decimal(sold)*Decimal(s0**2)/Decimal(Q96**2)
    gas = history['gas_wei']
    market_loss = baseline_ETH - gross
    all_in = (market_loss + gas) * 10_000 / baseline_ETH
    fee_rate_bps = Decimal(nominal_fee) / 100
    fee_bps = Decimal(exact_pool_fee) * 10_000 / sold
    execution_bps = market_loss * 10_000 / baseline_ETH
    # Same denominator for fee-price-gas decomposition. The output-normalized Gas ratio is separate.
    pool_component_bps = fee_bps
    price_component_bps = execution_bps - pool_component_bps
    gas_component_bps = Decimal(gas)*10_000 / baseline_ETH
    need(abs(all_in-pool_component_bps-price_component_bps-gas_component_bps) < Decimal('1e-65'),
         'cost shares do not add up')
    return {'hash':history['hash'],'utc':history['utc'],'pretick':t0,'posttick':t1,'tick_spacing':spacing,
            'liquidity_raw':liquidity,'prior_sqrt_price_x96':s0,'post_sqrt_price_x96':s1,
            'swap_steps':len(steps),'pool_fee_nominal_bps':str(fee_rate_bps),'pool_fee_input_wei':exact_pool_fee,
            'gas_wei':gas, 'net_eth_wei':gross-gas,'gas_bps_gross':str(Decimal(gas)*10_000/gross),
            'pool_fee_component_bps':str(pool_component_bps),'other_execution_component_bps':str(price_component_bps),
            'total_execution_bps':str(execution_bps),'gas_component_bps':str(gas_component_bps),
            'all_in_bps':str(all_in), 'steps':steps}


def state_record(h, label):
    pool = h['pool']
    block = h['block']
    archive = endpoint(label)
    p = hex(block-1)
    methods = {'slot0':SLOT0,'liquidity':LIQUIDITY,'spacing':SPACING}
    state = {k:rpc(archive,'eth_call',[{'to':pool,'data':sel},p]) for k,sel in methods.items()}
    tick = signed(words(state['slot0'])[1])
    spacing = number(state['spacing'])
    word = (tick//spacing//256) % (1 << 256)
    state['bitmap0'] = rpc(archive,'eth_call',[{'to':pool,'data':BITMAP+f'{word:064x}'},p])
    state['all_pool_logs'] = rpc(archive,'eth_getLogs',[{'address':pool,'fromBlock':hex(block),'toBlock':hex(block)}])
    swap = next(x for x in state['all_pool_logs'] if x['topics'][0]==SWAP_TOPIC and x['transactionHash']==h['hash'])
    end_tick = signed(words(swap['data'])[4])
    state['ticks'] = {str(i):rpc(archive,'eth_call',[{'to':pool,'data':TICKS+f'{i%(1<<256):064x}'},p])
                      for i in crossings(state,tick,end_tick,spacing)}
    return state


def collect(census_raw, raw, items, workers):
    raw.mkdir(parents=True,exist_ok=True)
    requests = []
    for h in items:
        key = h['hash']
        bundle = read(census_raw,'tx_'+key)
        tx = bundle['transaction']
        for provider in ('a','t'):
            cache(raw,f'cost_state_{key}_{provider}',lambda:state_record(h,provider))
        for level, label in thresholds(h['native_eth_wei'],h['minimum_wei']):
            q = params(tx,level,h['block']-1)
            for provider in ('a','t'):
                requests.append((key,str(level),label,provider,q))

    def emit(task):
        h,level,label,provider,q = task
        k = f'call_{h}_{level}_{provider}'
        response = cache(raw,k,lambda:rpc(endpoint(provider),'eth_call',q,allow_error=True))
        decode_replay(response,q)
    with ThreadPoolExecutor(max_workers=workers) as p:
        for i,_ in enumerate(p.map(emit,requests),1):
            if i%40==0 or i==len(requests):
                print(f'historical calls {i}/{len(requests)}',flush=True)


def audit(census_raw, raw, items, output):
    output.mkdir(parents=True,exist_ok=True)
    grid,costs,bounds = [],[],[]
    for h in items:
        key = h['hash']
        gross = h['native_eth_wei']
        txdata = read(census_raw,'tx_'+key)
        state = read(raw,f'cost_state_{key}_t')
        cross_state = read(raw,f'cost_state_{key}_a')
        need(all(state[name]==cross_state[name] for name in ('slot0','liquidity','spacing','bitmap0','ticks'))
             and list(map(log_key,state['all_pool_logs']))==list(map(log_key,cross_state['all_pool_logs'])),
             'historic cost state differs across nodes')
        costs.append(reconstruct(state,h,txdata['receipt']))
        levels = thresholds(gross,h['minimum_wei'])
        last_success = None
        first_revert = None
        for minimum,label in levels:
            expected = params(txdata['transaction'],minimum,h['block']-1)
            pair = []
            for provider in ('a','t'):
                snap = read(raw,f'call_{key}_{minimum}_{provider}')
                pair.append(decode_replay(snap,expected))
            need(pair[0]==pair[1], 'historical nodes disagree')
            status, result = pair[0]
            need((minimum <= gross and status=='success' and result==gross)
                 or (minimum>gross and status=='revert'), 'unexpected cutoff')
            if status=='success':
                last_success=minimum
            elif first_revert is None:
                first_revert=minimum
            grid.append({'hash':key,'historic_block':h['block']-1,'threshold_label':label,
                         'minimum_wei':minimum,'delta_from_payout_wei':minimum-gross,
                         'tenderly':status,'drpc':status,'output_or_reason':result})
        need(last_success==gross and first_revert==gross+1,'cutoff not one wei')
        bounds.append({'hash':key,'utc':h['utc'],'native_eth_wei':gross,'levels':len(levels),
                       'highest_tested_success_wei':last_success,'lowest_tested_revert_wei':first_revert})
    data={'transactions':len(items),'paired_parameter_points':len(grid),'node_calls':len(grid)*2,
          'cutoffs':bounds,'costs':costs}
    (output/'threshold_summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    write_csv(output,'threshold_grid',grid)
    write_csv(output,'cost_decomposition',[{k:v for k,v in row.items() if k!='steps'} for row in costs])
    write_csv(output,'swap_fee_steps',[{'hash':row['hash'],'step':i,**step} for row in costs for i,step in enumerate(row['steps'],1)])
    print(json.dumps({'transactions':len(items),'parameter_points':len(grid),'calls':len(grid)*2,
                      'exact_fees':[r['pool_fee_input_wei'] for r in costs]},indent=2),flush=True)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--census-raw',type=type(ROOT),default=ROOT/'raw'/'census')
    args.add_argument('--raw',type=type(ROOT),default=ROOT/'raw'/'thresholds')
    args.add_argument('--out',type=type(ROOT),default=ROOT/'derived')
    args.add_argument('--summary',type=type(ROOT))
    args.add_argument('--collect',action='store_true')
    args.add_argument('--workers',type=int,default=5)
    a=args.parse_args()
    selected=fixtures(a.summary or a.out/'census_summary.json')
    if a.collect:
        collect(a.census_raw,a.raw,selected,a.workers)
    audit(a.census_raw,a.raw,selected,a.out)


if __name__=='__main__':
    main()
