#!/usr/bin/env python3
"""2021 ETH mainnet Uniswap v3 census for all addresses in a pinned Labs list."""
import argparse
import csv
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'baseline'))
try:
    from reproduce import (MAIN, SECOND, TRACE, FACTORY, FACTORY_DEPLOYMENT_BLOCK, POOL_CREATED,
                           SWAP, TRANSFER, WITHDRAWAL, ZEROEX, SELECTOR, SETH, WETH,
                           addr, decimal_units, fetch, log_key, need, number, pool_index, receipt_match,
                           rpc, signed, utc, words)
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT.parent / 'replication'))
    from reproduce import (MAIN, SECOND, TRACE, FACTORY, FACTORY_DEPLOYMENT_BLOCK, POOL_CREATED,
                           SWAP, TRANSFER, WITHDRAWAL, ZEROEX, SELECTOR, SETH, WETH,
                           addr, decimal_units, fetch, log_key, need, number, pool_index, receipt_match,
                           rpc, signed, utc, words)

CHECKPOINTS = ('2021-07-09', '2021-07-16', '2021-07-23', '2021-07-24', '2021-07-31', '2021-08-07')
PERIODS = {'pre7': (1, 2), 'post7': (3, 4), 'pre14': (0, 2), 'post14': (3, 5)}
SLICES = ((0, 1), (1, 2), (3, 4), (4, 5))


def dump(root, name, value):
    path = root / (name + '.json.gz')
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as f:
        f.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n').encode())
    temporary.replace(path)


def read(root, name):
    with gzip.open(root / (name + '.json.gz'), 'rt', encoding='utf-8') as f:
        return json.load(f)


def cache(root, name, function):
    path = root / (name + '.json.gz')
    if path.exists():
        return read(root, name)
    value = function()
    dump(root, name, value)
    return value


def endpoint(label):
    variable, default = {'a': ('RESEARCH_PRIMARY_RPC', MAIN), 'b': ('RESEARCH_SECONDARY_RPC', SECOND),
                         't': ('RESEARCH_TRACE_RPC', TRACE)}[label]
    return os.getenv(variable, default)


def find_boundary(url, day):
    goal = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    lo, hi = 12750000, 13050000
    while hi - lo > 1:
        mid = (lo + hi) // 2
        head = rpc(url, 'eth_getBlockByNumber', [hex(mid), False])
        if utc(head['timestamp']) < goal:
            lo = mid
        else:
            hi = mid
    return {str(n): rpc(url, 'eth_getBlockByNumber', [hex(n), False]) for n in (lo, hi)}


def logs(url, address, event, low, high):
    params = [dict(address=address, topics=[event], fromBlock=hex(low), toBlock=hex(high))]
    try:
        return rpc(url, 'eth_getLogs', params)
    except (ValueError, RuntimeError):
        # Split a provider-side rejected range. Never treat a rejected call as an empty range.
        if high - low < 128:
            raise
        middle = (low + high) // 2
        return logs(url, address, event, low, middle) + logs(url, address, event, middle + 1, high)


def verify_logs(left, right, name):
    unique_left, unique_right = set(map(log_key, left)), set(map(log_key, right))
    need(len(unique_left) == len(left) and len(unique_right) == len(right)
         and unique_left == unique_right, f'log coverage mismatch: {name}')
    need(not any(x.get('removed') for x in left + right), f'removed log: {name}')
    return left


def manifest(folder):
    return {r['address'].lower(): r for r in json.loads((folder / 'list_2021.json').read_text())['tokens']
            if r['chainId'] == 1}


def boundaries(raw):
    points = []
    for day in CHECKPOINTS:
        pair = read(raw, f'boundary_{day}')
        prior, after = (pair[x] for x in sorted(pair, key=int))
        threshold = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need(utc(prior['timestamp']) < threshold <= utc(after['timestamp'])
             and prior['hash'] == after['parentHash']
             and number(prior['number']) + 1 == number(after['number']), f'bad boundary: {day}')
        points.append(number(after['number']))
    return points


def inventory(raw, listed, stop):
    records = verify_logs(read(raw, 'factory_a'), read(raw, 'factory_b'), 'factory')
    need(all(x['address'].lower() == FACTORY and x['topics'][0] == POOL_CREATED
             and FACTORY_DEPLOYMENT_BLOCK <= number(x['blockNumber']) < stop for x in records),
         'factory log outside filter')
    pools = pool_index(records)
    need(len(pools) == len(records), 'pool address not unique')
    result = {a: p for a, p in sorted(pools.items()) if listed.keys() & {p['token0'], p['token1']}}
    return records, result


def census_tasks(pools, points):
    return [(begin, end, low, high) for begin, end in SLICES
            for low, high in [(points[begin], points[end] - 1)]]


def audit_queries(raw, pools, points):
    found = []
    batch_size = 32
    ordered = list(pools)
    for begin, end, low, high in census_tasks(pools, points):
        for offset in range(0, len(ordered), batch_size):
            group = ordered[offset:offset + batch_size]
            key = f'swaps_{begin}_{end}_{offset}'
            chunk = verify_logs(read(raw, key + '_a'), read(raw, key + '_b'), key)
            need(all(x['address'].lower() in group and x['topics'][0] == SWAP
                     and low <= number(x['blockNumber']) <= high for x in chunk), 'swap outside filter')
            found.extend(chunk)
    return sorted(found, key=lambda x: (number(x['blockNumber']), number(x['logIndex'])))


def tx_bundle(h):
    a, t = endpoint('a'), endpoint('t')
    return {'transaction': rpc(a, 'eth_getTransactionByHash', [h]),
            'receipt': rpc(a, 'eth_getTransactionReceipt', [h]),
            'cross_receipt': rpc(t, 'eth_getTransactionReceipt', [h])}


def is_0x_native(tx):
    return tx['to'] is not None and tx['to'].lower() == ZEROEX and tx['input'].startswith(SELECTOR)


def collect(raw, ref, workers):
    raw.mkdir(parents=True, exist_ok=True)
    listed = manifest(ref)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for label in ('a', 'b', 't'):
            cache(raw, 'chain_' + label, lambda: rpc(endpoint(label), 'eth_chainId', []))
        for n in (FACTORY_DEPLOYMENT_BLOCK - 1, FACTORY_DEPLOYMENT_BLOCK):
            cache(raw, f'factory_code_{n}', lambda: rpc(endpoint('t'), 'eth_getCode', [FACTORY, hex(n)]))
        list(pool.map(lambda day: cache(raw, 'boundary_' + day, lambda: find_boundary(endpoint('t'), day)), CHECKPOINTS))
        points = boundaries(raw)
        print('UTC boundary blocks', points, flush=True)
        list(pool.map(lambda label: cache(raw, 'factory_' + label,
                      lambda: logs(endpoint(label), FACTORY, POOL_CREATED, FACTORY_DEPLOYMENT_BLOCK, points[-1] - 1)), ('a', 'b')))
        blocks, eligible = inventory(raw, listed, points[-1])
        print('factory total', len(blocks), 'matched pools', len(eligible), flush=True)

        def fetch_chunk(q):
            begin, end, idx, group, label = q
            name = f'swaps_{begin}_{end}_{idx}_{label}'
            cache(raw, name, lambda: logs(endpoint(label), group, SWAP, points[begin], points[end] - 1))

        eligible_addresses = list(eligible)
        list(pool.map(fetch_chunk, [(b, e, i, eligible_addresses[i:i + 32], label)
                    for b, e, _, _ in census_tasks(eligible, points)
                    for i in range(0, len(eligible_addresses), 32) for label in ('a', 'b')]))
        swaps = audit_queries(raw, eligible, points)
        hashes = sorted({v['transactionHash'] for v in swaps})
        block_numbers = sorted({number(v['blockNumber']) for v in swaps})
        print('logs', len(swaps), 'hashes', len(hashes), 'blocks', len(block_numbers), flush=True)
        def fetch_transaction(h):
            tx = cache(raw, 'tx_' + h, lambda: tx_bundle(h))['transaction']
            if is_0x_native(tx):
                cache(raw, 'trace_' + h, lambda: rpc(endpoint('t'),'trace_transaction',[h]))
                cache(raw, 'eoa_' + h, lambda: rpc(endpoint('t'), 'eth_getCode',
                      [tx['from'], hex(number(tx['blockNumber']) - 1)]))
        for i, _ in enumerate(pool.map(fetch_transaction, hashes), 1):
            if i % 100 == 0 or i == len(hashes):
                print(f'receipts {i}/{len(hashes)}', flush=True)

        def read_head(n):
            cache(raw, f'head_{n}', lambda: rpc(endpoint('a'), 'eth_getBlockByNumber', [hex(n), False]))
        list(pool.map(read_head, block_numbers))
        print('all headers saved', flush=True)


def receipt_transfers(receipt):
    values = []
    for event in receipt['logs']:
        if event['topics'] and event['topics'][0] == TRANSFER and len(event['topics']) == 3 and len(event['data']) == 66:
            values.append((event['address'].lower(), addr(event['topics'][1]), addr(event['topics'][2]), number(event['data'])))
    return values


def has_leg_transfer(transfers, pool, token, delta):
    # For one event at this pool in the receipt, cross-check the net ERC-20 change of the pool.
    ins = sum(value for asset, a, b, value in transfers if asset == token and b == pool)
    outs = sum(value for asset, a, b, value in transfers if asset == token and a == pool)
    return ins - outs == delta


def strict_native(raw, tx, receipt, performed, pools, transfers):
    if not is_0x_native(tx):
        return None, 'route_not_exact_0x_native'
    # All v3 Swap events of this transaction are considered, including non-list pools.
    all_v3_events = [x for x in receipt['logs'] if len(x['topics']) == 3 and x['topics'][0] == SWAP]
    if len(performed) != 1 or len(all_v3_events) != 1 or number(tx['value']) != 0:
        return None, 'multi_v3_or_native_input'
    event = performed[0]
    pool = pools[event['address'].lower()]
    delta = [signed(x) for x in words(event['data'])[:2]]
    if not ((delta[0] > 0 > delta[1]) or (delta[1] > 0 > delta[0])):
        return None, 'wrong_amount_sign'
    sold_side = 0 if delta[0] > 0 else 1
    sold_token, pay_token = pool[f'token{sold_side}'], pool[f'token{1-sold_side}']
    if pay_token != WETH:
        return None, 'output_not_weth'
    h = tx['hash'].lower()
    s, debit, gross = tx['from'].lower(), delta[sold_side], -delta[1-sold_side]
    if read(raw, 'eoa_' + h) != '0x':
        return None, 'sender_had_account_code'
    data = tx['input']
    offset, sell_param, min_param, recipient = words('0x' + data[10:266])
    cursor = 10 + 2 * offset
    path_len = int(data[cursor:cursor + 64], 16)
    path = data[cursor + 64:cursor + 64 + 2 * path_len]
    want = sold_token[2:] + f"{pool['fee_millionths']:06x}" + pay_token[2:]
    if (path != want or sell_param != debit or min_param > gross or recipient not in (0, int(s, 16))
            or addr(event['topics'][1]) != ZEROEX or addr(event['topics'][2]) != ZEROEX):
        return None, 'calldata_or_pool_participant_mismatch'
    if (transfers.count((sold_token, s, pool['pool'], debit)) != 1
            or transfers.count((WETH, pool['pool'], ZEROEX, gross)) != 1):
        return None, 'missing_exact_transfer'
    unwrapped = [l for l in receipt['logs'] if l['address'].lower() == WETH and len(l['topics']) == 2
                 and l['topics'][0] == WITHDRAWAL and addr(l['topics'][1]) == ZEROEX and number(l['data']) == gross]
    if len(unwrapped) != 1:
        return None, 'missing_exact_weth_unwrap'
    trace = {tuple(t['traceAddress']): t for t in read(raw, 'trace_' + h)}
    matches = {}
    for route, step in trace.items():
        a = step['action']
        if step['type'] != 'call' or a.get('callType') != 'call' or number(a['value']) != gross:
            continue
        if any('error' in trace[route[:i]] for i in range(len(route) + 1)):
            continue
        if step['blockHash'] != tx['blockHash'] or step['transactionHash'] != h:
            return None, 'trace_identity_mismatch'
        if (a['from'].lower(), a['to'].lower()) in ((WETH, ZEROEX), (ZEROEX, s)):
            matches.setdefault((a['from'].lower(), a['to'].lower()), []).append(route)
    if not all(len(matches.get(k, [])) == 1 for k in [(WETH, ZEROEX), (ZEROEX, s)]):
        return None, 'missing_native_final_delivery'
    return {'hash': h, 'block': number(tx['blockNumber']), 'sender': s, 'sold_token': sold_token,
            'pool': pool['pool'], 'pool_fee': pool['fee_millionths'], 'input_raw': debit,
            'native_eth_wei': gross, 'minimum_wei': min_param, 'gas_used': number(receipt['gasUsed']),
            'gas_price_wei': number(receipt['effectiveGasPrice']),
            'gas_wei': number(receipt['gasUsed']) * number(receipt['effectiveGasPrice']),
            'swap_log_index': number(event['logIndex']),
            'payout_trace': '.'.join(map(str, matches[ZEROEX, s][0]))}, 'matched'


def write_csv(root, name, rows):
    if rows:
        with (root / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def audit(raw, ref, output):
    output.mkdir(parents=True, exist_ok=True)
    need(all(number(read(raw, 'chain_' + e)) == 1 for e in ('a', 'b', 't')), 'not mainnet')
    prior = read(raw, f'factory_code_{FACTORY_DEPLOYMENT_BLOCK-1}')
    initial = read(raw, f'factory_code_{FACTORY_DEPLOYMENT_BLOCK}')
    need(prior=='0x' and initial.startswith('0x') and len(initial)>2,'factory start code mismatch')
    listed = manifest(ref)
    need(len(listed) == 129 and SETH in listed, 'versioned list count')
    points = boundaries(raw)
    full, eligible = inventory(raw, listed, points[-1])
    events = audit_queries(raw, eligible, points)
    event_sets = defaultdict(list)
    for line in events:
        event_sets[line['transactionHash']].append(line)
    transactions, event_rows, sales = [], [], []
    for h, performed in event_sets.items():
        bundle = read(raw, 'tx_' + h)
        tx, receipt = bundle['transaction'], bundle['receipt']
        receipt_match(receipt, bundle['cross_receipt'])
        n = number(tx['blockNumber'])
        block_header = read(raw, f'head_{n}')
        stamp = utc(block_header['timestamp']).isoformat()
        need(tx['hash'] == receipt['transactionHash'] == h and receipt['status'] == '0x1'
             and tx['blockHash'] == receipt['blockHash'] == block_header['hash']
             and h in block_header['transactions'], f'not canonical tx {h}')
        receipt_keys = set(map(log_key, receipt['logs']))
        need(all(log_key(e) in receipt_keys and e['blockHash'] == tx['blockHash'] for e in performed),
             'swap log absent from receipt')
        transfers = receipt_transfers(receipt)
        summed = defaultdict(lambda: [0, 0])
        for e in performed:
            values = [signed(v) for v in words(e['data'])[:2]]
            for side, v in enumerate(values):
                summed[e['address'].lower()][side] += v
        pool_checked = set()
        for pool, deltas in summed.items():
            if all(has_leg_transfer(transfers, pool, eligible[pool][f'token{i}'], d)
                   for i, d in enumerate(deltas)):
                pool_checked.add(pool)
        strict, reason = strict_native(raw, tx, receipt, performed, eligible, transfers)
        if strict:
            strict.update(utc=stamp, sold_listed=strict['sold_token'] in listed,
                          symbol=listed.get(strict['sold_token'], {}).get('symbol', ''))
            sales.append(strict)
        transactions.append({'hash': h, 'block': n, 'utc': stamp, 'sender': tx['from'], 'to': tx['to'],
                             'selector': tx['input'][:10], 'eligible_swaps': len(performed),
                             'gas_wei': number(receipt['gasUsed']) * number(receipt['effectiveGasPrice']),
                             'strict_native_outcome': reason})
        for e in performed:
            pool = e['address'].lower()
            row = eligible[pool]
            a0, a1 = (signed(x) for x in words(e['data'])[:2])
            event_rows.append({'hash': h, 'block': n, 'utc': stamp, 'pool': pool, 'token0': row['token0'],
                               'token1': row['token1'], 'log_index': number(e['logIndex']), 'amount0_raw': a0,
                               'amount1_raw': a1, 'pool_net_transfer_verified': pool in pool_checked})
    events_sorted = sorted(event_rows, key=lambda r: (r['block'], r['log_index']))
    study = {}
    token_rows = []
    for label, (start, end) in PERIODS.items():
        lo, hi = points[start], points[end]
        subset = [e for e in events_sorted if lo <= e['block'] < hi]
        live = {t for e in subset for t in (e['token0'], e['token1']) if t in listed}
        reconciled = {t for e in subset if e['pool_net_transfer_verified'] for t in (e['token0'],e['token1']) if t in listed}
        native = [r for r in sales if lo <= r['block'] < hi and r['sold_listed']]
        subset_s = [e for e in subset if SETH in (e['token0'], e['token1'])]
        study[label] = {
            'bounds': [lo, hi], 'swap_logs': len(subset), 'txs': len({e['hash'] for e in subset}),
            'active_pools': len({e['pool'] for e in subset}), 'active_list_tokens': len(live),
            'pool_reconciled_logs': sum(e['pool_net_transfer_verified'] for e in subset),
            'pool_reconciled_tokens': len(reconciled),
            'strict_list_0x_txs': len(native),
            'strict_list_0x_tokens': len({x['sold_token'] for x in native}),
            'strict_list_0x_addresses': len({x['sender'] for x in native}),
            'seth_swap_logs': len(subset_s), 'seth_txs': len({e['hash'] for e in subset_s}),
            'seth_sale_logs': sum(e['amount0_raw' if e['token0'] == SETH else 'amount1_raw'] > 0 for e in subset_s),
            'seth_strict_txs': sum(x['sold_token'] == SETH for x in native),
        }
        for token, metadata in listed.items():
            focus = [e for e in subset if token in (e['token0'], e['token1'])]
            token_rows.append({'window':label, 'token':token, 'symbol':metadata['symbol'],
                               'pool_count_by_end':sum(token in (p['token0'], p['token1']) and p['created_block'] < hi
                                                       for p in eligible.values()),
                               'swap_logs':len(focus), 'txs':len({e['hash'] for e in focus}),
                               'reconciled_logs':sum(e['pool_net_transfer_verified'] for e in focus),
                               'strict_0x_sales':sum(x['sold_token']==token for x in native)})
    summary = {'factory_logs': len(full), 'eligible_pools': len(eligible),
               'list_count': len(listed), 'list_tokens_with_pools': len({t for e in eligible.values()
                                      for t in (e['token0'],e['token1']) if t in listed}),
               'boundaries': dict(zip(CHECKPOINTS, points)),
               'windows': study,
               'transactions_28_observed_days':len(transactions), 'swap_logs_28_observed_days':len(event_rows),
               'route_outcomes': dict(sorted(Counter(x['strict_native_outcome'] for x in transactions).items())),
               'strict_paths': [x for x in sales if x['sold_listed']]}
    (output / 'census_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_csv(output,'pool_inventory',list(eligible.values()))
    write_csv(output,'census_swaps',events_sorted)
    write_csv(output,'census_transactions',transactions)
    write_csv(output,'census_tokens_by_window',token_rows)
    write_csv(output,'strict_native_0x',sales)
    print(json.dumps({k:v for k,v in summary.items() if k != 'strict_paths'},ensure_ascii=False,indent=2),flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', type=Path, default=ROOT / 'raw' / 'census')
    ap.add_argument('--baseline', type=Path, default=ROOT / 'baseline' / 'raw')
    ap.add_argument('--out', type=Path, default=ROOT / 'derived')
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()
    if args.collect:
        collect(args.raw, args.baseline, args.workers)
    audit(args.raw, args.baseline, args.out)


if __name__ == '__main__':
    main()
