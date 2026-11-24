#!/usr/bin/env python3
"""Reproduce the sETH history audit. Python 3.10+, standard library only."""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

getcontext().prec = 70
MAIN = 'https://gateway.tenderly.co/public/mainnet'
SECOND = 'https://eth-mainnet.g.alchemy.com/v2/demo/'
TRACE = 'https://eth.drpc.org'
REV = '4078390a4890445d1ff0ed5196fd4cb56a44de87'
PARENT = 'e07599ef0f5555dac306925bc191713d68548c53'
FACTORY = '0x1f98431c8ad98523631ae4a59f267346ea31f984'
SETH = '0x5e74c9036fb86bd7ecdcb084a0673efc32ea31cb'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
ZEROEX = '0xdef1c0ded9bec7f1a1670819833240f027b25eff'
V3ROUTER = '0xe592427a0aece92de3edee1f18e0157c05861564'
POOL_CREATED = '0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118'
SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
WITHDRAWAL = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'
SELECTOR = '0x803ba26d'
DATES = ('2021-07-16', '2021-07-23', '2021-07-24', '2021-07-31')
BOUNDS = dict(zip(DATES, (12834632, 12879309, 12885655, 12930042)))
WINDOWS = {'pre': (DATES[0], DATES[1]), 'post': (DATES[2], DATES[3])}
FACTORY_DEPLOYMENT_BLOCK = 12369621
WEI = 10 ** 18


def need(condition, label):
    if not condition:
        raise ValueError(label)


def load(root, name):
    return json.loads((root / f'{name}.json').read_text(encoding='utf-8'))


def save(root, name, value):
    (root / f'{name}.json').write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fetch(url, payload=None, tolerate_rpc_error=False):
    headers = {'User-Agent': 'ReadOnlyChainResearch/1.0'}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    for attempt in range(4):
        try:
            with urlopen(Request(url, data=body, headers=headers), timeout=35) as stream:
                return stream.read()
        except HTTPError as error:
            content = error.read()
            if tolerate_rpc_error and error.code in (400, 403, 500):
                try:
                    if 'error' in json.loads(content):
                        return content
                except ValueError:
                    pass
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f'{error.code} from {url}: {content[:200]!r}') from error
        except (URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(1 + attempt)


def rpc(url, method, params, allow_error=False):
    request = dict(jsonrpc='2.0', id=1, method=method, params=params)
    response = json.loads(fetch(url, request, allow_error))
    if allow_error:
        return {'request': request, 'response': response}
    if 'error' in response or response.get('result') is None:
        raise ValueError(f'{method}: {response}')
    return response['result']


def words(data):
    need(data.startswith('0x') and (len(data) - 2) % 64 == 0, 'malformed ABI words')
    return [int(data[pos:pos + 64], 16) for pos in range(2, len(data), 64)]


def number(hex_string):
    return int(hex_string, 16)


def signed(word):
    return word - (1 << 256) if word >= (1 << 255) else word


def addr(topic):
    return '0x' + topic[-40:].lower()


def utc(timestamp):
    return datetime.fromtimestamp(number(timestamp), timezone.utc)


def token_address(token):
    return token['address'].lower()


def log_key(log):
    return (log['blockHash'].lower(), log['transactionHash'].lower(), number(log['logIndex']),
            log['address'].lower(), tuple(topic.lower() for topic in log['topics']),
            log['data'].lower())


def pool_index(logs):
    return {addr(log['data']): {
        'pool': addr(log['data']), 'token0': addr(log['topics'][1]),
        'token1': addr(log['topics'][2]), 'fee_millionths': number(log['topics'][3]),
        'created_block': number(log['blockNumber']), 'created_tx': log['transactionHash'],
    } for log in logs}


def collect(root):
    root.mkdir(parents=True, exist_ok=True)
    root_url = 'https://raw.githubusercontent.com/Uniswap/interface/'
    list_paths = {
        'list_2021.json': (REV, 'src/constants/tokenLists/unsupported.tokenlist.json'),
        'list_before_2021.json': (PARENT, 'src/constants/tokenLists/uniswap-v2-unsupported.tokenlist.json'),
        'hooks_2021.ts': (REV, 'src/state/lists/hooks.ts'),
        'lists_2021.ts': (REV, 'src/constants/lists.ts'),
        'misc_2021.ts': (REV, 'src/constants/misc.ts'),
    }
    for name, (rev, path) in list_paths.items():
        (root / name).write_bytes(fetch(root_url + rev + '/' + path))
    for name, path in [('commit_2021', '/commits/' + REV), ('list_history_until_0731',
        '/commits?path=src/constants/tokenLists/unsupported.tokenlist.json&until=2021-07-31T00%3A00%3A00Z')]:
        (root / f'{name}.json').write_bytes(fetch('https://api.github.com/repos/Uniswap/interface' + path))
    primary = os.getenv('RESEARCH_PRIMARY_RPC', MAIN)
    secondary = os.getenv('RESEARCH_SECONDARY_RPC', SECOND)
    trace_provider = os.getenv('RESEARCH_TRACE_RPC', TRACE)
    def record(name, method, params, provider=primary):
        val = rpc(provider, method, params)
        save(root, name, val)
        return val

    for label, provider in [('tenderly', primary), ('alchemy', secondary), ('drpc', trace_provider)]:
        record('chain_' + label, 'eth_chainId', [], provider)
    for block in (FACTORY_DEPLOYMENT_BLOCK - 1, FACTORY_DEPLOYMENT_BLOCK):
        record(f'factory_code_{block}', 'eth_getCode', [FACTORY, hex(block)], trace_provider)
    save(root, 'bounds', BOUNDS)
    for block in BOUNDS.values():
        for neighbour in [block - 1, block]:
            record(f'block_{neighbour}', 'eth_getBlockByNumber', [hex(neighbour), False])

    def logs(name, address, topics, first, last, cross=True):
        query = [dict(address=address, topics=topics, fromBlock=hex(first), toBlock=hex(last))]
        val = record(name, 'eth_getLogs', query)
        if cross:
            record('cross_' + name, 'eth_getLogs', query, secondary)
        return val

    topic = '0x' + SETH[2:].zfill(64)
    factory_logs = []
    for index, topics in enumerate([[POOL_CREATED, topic], [POOL_CREATED, None, topic]]):
        factory_logs.extend(logs(f'factory_sETH_token{index}', FACTORY, topics, FACTORY_DEPLOYMENT_BLOCK, BOUNDS[DATES[-1]] - 1))
    hashes = {}
    for pool, info in pool_index(factory_logs).items():
        h = info['created_tx']
        record('receipt_' + h, 'eth_getTransactionReceipt', [h])
        for period, (start, stop) in WINDOWS.items():
            name = f'swaps_{pool}_{period}'
            for log in logs(name, pool, [SWAP], BOUNDS[start], BOUNDS[stop] - 1):
                hashes[log['transactionHash']] = log

    for h, log in sorted(hashes.items()):
        tx = record('tx_' + h, 'eth_getTransactionByHash', [h])
        record('receipt_' + h, 'eth_getTransactionReceipt', [h])
        record('cross_receipt_' + h, 'eth_getTransactionReceipt', [h], trace_provider)
        block = number(tx['blockNumber'])
        record(f'block_{block}', 'eth_getBlockByNumber', [hex(block), False])
        if tx['to'].lower() != ZEROEX or not tx['input'].startswith(SELECTOR):
            continue
        prev = hex(block - 1)
        record('trace_transaction_drpc_' + h, 'trace_transaction', [h], trace_provider)
        record('code_sender_' + h, 'eth_getCode', [tx['from'], prev], trace_provider)
        record('code_target_' + h, 'eth_getCode', [ZEROEX, prev], trace_provider)
        pool = log['address'].lower()
        record('prior_price_' + h, 'eth_call', [{'to': pool, 'data': '0x3850c7bd'}, prev], trace_provider)
        logs('same_block_swaps_' + h, pool, [SWAP], block, block, cross=False)
        for label, data in replay_inputs(tx['input']).items():
            call = {key: tx[key] for key in ['from', 'to', 'gas', 'gasPrice', 'value']}
            call['data'] = data
            for provider_label, provider in [('drpc', trace_provider), ('tenderly', primary)]:
                name = f'replay_{label}_{provider_label}_{h}'
                save(root, name, rpc(provider, 'eth_call', [call, prev], allow_error=True))


def receipt_match(a, b):
    for key in ('blockHash', 'blockNumber', 'transactionHash', 'status', 'gasUsed', 'effectiveGasPrice'):
        need(a[key].lower() == b[key].lower(), f'cross-provider receipt differs: {key}')
    need([log_key(l) for l in a['logs']] == [log_key(l) for l in b['logs']], 'receipt logs differ')


def audited_logs(raw, key):
    first = load(raw, key)
    second = load(raw, 'cross_' + key)
    need(sorted(map(log_key, first)) == sorted(map(log_key, second)), f'RPC logs differ: {key}')
    need(len(set(map(log_key, first))) == len(first) and not any(log.get('removed') for log in first),
         f'noncanonical or duplicate log in {key}')
    return first


def trace_payments(raw, h, receipt, sender, gross):
    traces = load(raw, 'trace_transaction_drpc_' + h)
    indexed = {tuple(t['traceAddress']): t for t in traces}
    payments = []
    for path, entry in indexed.items():
        action = entry['action']
        if entry['type'] != 'call' or action.get('callType') != 'call':
            continue
        a, b = action['from'].lower(), action['to'].lower()
        if (a, b) not in [(WETH, ZEROEX), (ZEROEX, sender)] or number(action['value']) != gross:
            continue
        need(not any('error' in indexed[path[:i]] for i in range(len(path) + 1)), 'payment reverted')
        need(entry['blockHash'].lower() == receipt['blockHash'].lower()
             and entry['transactionHash'].lower() == h, 'trace identity mismatch')
        payments.append((a, b, '.'.join(map(str, path))))
    need(len(payments) == 2 and {(p[0], p[1]) for p in payments} == {(WETH, ZEROEX), (ZEROEX, sender)},
         'missing unwrapping payout or final ETH delivery')
    return next(p[2] for p in payments if p[1] == sender)


def replay_inputs(data):
    # ABI words: encodedPath offset, sellAmount, minBuyAmount, recipient.
    begin = 10 + 2 * 64
    return {'actual_input': data, 'raise_minimum': data[:begin] + f'{2 * WEI:064x}' + data[begin + 64:]}


def outcome(raw, tx, receipt, swap, pool, commit_date):
    h = tx['hash'].lower()
    sender = tx['from'].lower()
    pool_addr = pool['pool']
    amount0, amount1, after_sqrt, *_ = words(swap['data'])
    amount0, amount1 = signed(amount0), signed(amount1)
    need(amount0 * amount1 < 0, 'unexpected swap signs')
    debit, gross = amount0, -amount1
    need(pool['token0'] == SETH and pool['token1'] == WETH and debit > 0, 'wrong sold asset or output token')
    need(number(tx['value']) == 0 and int(receipt['status'], 16) == 1, 'unsuccessful or payable route')
    need(load(raw, 'code_sender_' + h) == '0x' and
         load(raw, 'code_target_' + h) != '0x', 'unexpected sender or recipient code')
    need(addr(swap['topics'][1]) == addr(swap['topics'][2]) == ZEROEX, 'pool sender or recipient differs')

    def one_event(contract, topics, amount):
        matches = [x for x in receipt['logs'] if x['address'].lower() == contract
                   and tuple(x['topics'][0:1]) + tuple(map(addr, x['topics'][1:])) == topics
                   and len(x['data']) == 66 and number(x['data']) == amount]
        need(len(matches) == 1, f'expected one matching event in {h}: {topics}')
        return number(matches[0]['logIndex'])

    debit_log = one_event(SETH, (TRANSFER, sender, pool_addr), debit)
    weth_log = one_event(WETH, (TRANSFER, pool_addr, ZEROEX), gross)
    unwrap_log = one_event(WETH, (WITHDRAWAL, ZEROEX), gross)
    swap_log = number(swap['logIndex'])
    need(weth_log < debit_log < swap_log < unwrap_log, 'unexpected event order')
    payout_trace = trace_payments(raw, h, receipt, sender, gross)

    data = tx['input']
    args = words('0x' + data[10:10 + 4 * 64])
    offset, input_amount, minimum, recipient = args
    path_start = 10 + 2 * offset
    path_size = int(data[path_start:path_start + 64], 16)
    path = data[path_start + 64:path_start + 64 + path_size * 2]
    expected_path = SETH[2:] + f"{pool['fee_millionths']:06x}" + WETH[2:]
    need(path == expected_path and input_amount == debit and recipient in (0, int(sender, 16))
         and gross >= minimum, 'calldata does not match transfers')

    before_sqrt = words(load(raw, 'prior_price_' + h))[0]
    same_block = sorted(load(raw, 'same_block_swaps_' + h), key=lambda l: number(l['logIndex']))
    need(sum(log_key(l) == log_key(swap) for l in same_block) == 1, 'same-block event mismatch')
    prev_swaps = [l for l in same_block if number(l['logIndex']) < swap_log]
    if prev_swaps:
        before_sqrt = words(prev_swaps[-1]['data'])[2]
    ideal = Decimal(debit) * Decimal(before_sqrt ** 2) / Decimal(1 << 192)
    fee = number(receipt['gasUsed']) * number(receipt['effectiveGasPrice'])
    replay = {}
    for label, data in replay_inputs(tx['input']).items():
        snapshot = load(raw, f'replay_{label}_drpc_{h}')
        args = snapshot['request']['params']
        need(args[0]['data'] == data and number(args[1]) == number(tx['blockNumber']) - 1
             and all(args[0][k] == tx[k] for k in ['from', 'to', 'gas', 'gasPrice', 'value']),
             'replay input outside protocol')
        need(snapshot['request']['method'] == 'eth_call', 'unexpected replay method')
        response = snapshot['response']
        cross = load(raw, f'replay_{label}_tenderly_{h}')
        need(cross['request'] == snapshot['request'], 'replay provider request differs')
        if label == 'actual_input':
            need(number(response['result']) == number(cross['response']['result']) == gross,
                 'baseline replay does not reproduce the observed payout')
            replay[label] = decimal_units(number(response['result']))
            continue
        err, cross_err = response['error'], cross['response']['error']
        raw_error = err['data']
        need(raw_error == cross_err['data'] and raw_error.startswith('0x08c379a0'),
             'revert payload does not match across providers')
        data_bytes = bytes.fromhex(raw_error[10:])
        string_offset = int.from_bytes(data_bytes[:32], 'big')
        string_size = int.from_bytes(data_bytes[string_offset:string_offset + 32], 'big')
        reason = data_bytes[string_offset + 32:string_offset + 32 + string_size].decode()
        need(reason == 'UniswapV3Feature/UNDERBOUGHT', 'unexpected replay error')
        replay[label] = reason
    return {
        'transaction_hash': h, 'sender': sender, 'pool': pool_addr, 'sell_wei': debit,
        'gross_eth_wei': gross, 'gas_wei': fee, 'gross_sETH': decimal_units(debit),
        'gross_ETH': decimal_units(gross), 'gas_ETH': decimal_units(fee),
        'net_ETH_after_trade_gas': decimal_units(gross - fee),
        'gas_pct_of_gross': str(100 * Decimal(fee) / gross),
        'execution_deviation_bps': str(10000 * (1 - Decimal(gross) / ideal)),
        'all_in_deviation_bps': str(10000 * (1 - Decimal(gross - fee) / ideal)),
        'min_out_wei': minimum, 'min_out_ETH': decimal_units(minimum),
        'calldata_to_realized_bps': str(10000 * (1 - Decimal(minimum) / gross)),
        'slot0_before_sqrtPriceX96': before_sqrt, 'after_sqrtPriceX96': after_sqrt,
        'weth_transfer_log': weth_log, 'seth_transfer_log': debit_log, 'swap_log': swap_log,
        'withdrawal_log': unwrap_log, 'payout_trace_address': payout_trace,
        'commit_before_transaction': commit_date,
        'replay': replay,
    }


def decimal_units(value):
    return format(Decimal(value) / WEI, 'f')


def output_csv(dest, name, rows):
    if not rows:
        return
    with (dest / (name + '.csv')).open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(raw, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for name in ('tenderly', 'alchemy', 'drpc'):
        need(number(load(raw, 'chain_' + name)) == 1, 'wrong network')
    need(load(raw, f'factory_code_{FACTORY_DEPLOYMENT_BLOCK - 1}') == '0x' and
         len(load(raw, f'factory_code_{FACTORY_DEPLOYMENT_BLOCK}')) > 2,
         'factory bytecode does not begin at the chosen block')
    bounds = load(raw, 'bounds')
    need(bounds == BOUNDS, 'block bounds changed')
    for date, n in bounds.items():
        at = load(raw, f'block_{n}')
        before = load(raw, f'block_{n-1}')
        threshold = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        need(before['hash'] == at['parentHash'] and number(at['number']) == n
             and number(before['number']) == n - 1
             and utc(before['timestamp']) < threshold <= utc(at['timestamp']), 'wrong block boundary')

    current = [t for t in load(raw, 'list_2021')['tokens'] if t['chainId'] == 1]
    old = [t for t in load(raw, 'list_before_2021')['tokens'] if t['chainId'] == 1]
    commit = load(raw, 'commit_2021')
    commit_time = datetime.fromisoformat(commit['commit']['committer']['date'].replace('Z', '+00:00'))
    revisions = load(raw, 'list_history_until_0731')
    need(commit['sha'] == REV and commit['parents'][0]['sha'] == PARENT
         and revisions[0]['sha'] == REV and len({token_address(t) for t in current}) == len(current),
         'list history or identity failure')
    missing_before = all(token_address(t) != SETH for t in old)
    need(missing_before and any(token_address(t) == SETH and t['decimals'] == 18 for t in current),
         'sETH does not match the archived lists')
    hooks = (raw / 'hooks_2021.ts').read_text(encoding='utf-8')
    domains = (raw / 'misc_2021.ts').read_text(encoding='utf-8')
    need('IS_ON_APP_URL ? listToTokenMap(UNSUPPORTED_TOKEN_LIST)' in hooks and
         'app.uniswap.org' in domains and 'IS_ON_APP_URL' in domains, 'host condition missing')

    factory = [log for i in (0, 1) for log in audited_logs(raw, f'factory_sETH_token{i}')]
    pools = pool_index(factory)
    for log in factory:
        need(log['address'].lower() == FACTORY and log['topics'][0] == POOL_CREATED,
             'pool creation source mismatch')
        creation = load(raw, 'receipt_' + log['transactionHash'])
        need(creation['status'] == '0x1' and log_key(log) in map(log_key, creation['logs']),
             'pool creation receipt does not match')

    events, trades, strict = [], {}, []
    for pool, pi in sorted(pools.items()):
        for period, (start, end) in WINDOWS.items():
            for log in audited_logs(raw, f'swaps_{pool}_{period}'):
                h = log['transactionHash'].lower()
                tx, receipt = load(raw, 'tx_' + h), load(raw, 'receipt_' + h)
                receipt_match(receipt, load(raw, 'cross_receipt_' + h))
                block_number = number(log['blockNumber'])
                block = load(raw, f'block_{block_number}')
                stamp = utc(block['timestamp'])
                need(bounds[start] <= block_number < bounds[end] and
                     datetime.fromisoformat(start).date() <= stamp.date() < datetime.fromisoformat(end).date(),
                     'swap outside the window')
                need(tx['hash'].lower() == receipt['transactionHash'].lower() == h and
                     log['blockHash'] == tx['blockHash'] == receipt['blockHash'] == block['hash']
                     and h in block['transactions'] and receipt['status'] == '0x1'
                     and log['address'].lower() == pool and log['topics'][0] == SWAP and
                     log_key(log) in map(log_key, receipt['logs']), 'transaction/log mismatch')
                a0, a1, *_ = words(log['data'])
                delta0, delta1 = signed(a0), signed(a1)
                need(delta0 * delta1 < 0, 'unexpected signed pool amounts')
                seth_delta = delta0 if pi['token0'] == SETH else delta1
                events.append({'period': period, 'block': block_number, 'utc': stamp.isoformat(),
                               'pool': pool, 'transaction_hash': h, 'log_index': number(log['logIndex']),
                               'amount0_raw': delta0, 'amount1_raw': delta1,
                               'seth_direction_from_trader': 'sell' if seth_delta > 0 else 'buy'})
                gas_wei = number(receipt['effectiveGasPrice']) * number(receipt['gasUsed'])
                row = trades.setdefault(h, {
                    'period': period, 'utc': stamp.isoformat(), 'block': block_number,
                    'transaction_hash': h, 'sender': tx['from'], 'target': tx['to'],
                    'selector': tx['input'][:10], 'gas_used': number(receipt['gasUsed']),
                    'gas_price_wei': number(receipt['effectiveGasPrice']), 'gas_wei': gas_wei,
                    'gas_ETH': decimal_units(gas_wei), 'swap_count': 0, 'strict_0x_close': False})
                row['swap_count'] += 1
                if tx['to'].lower() == ZEROEX and tx['input'].startswith(SELECTOR) and seth_delta > 0:
                    row['strict_0x_close'] = True
                    result = outcome(raw, tx, receipt, log, pi, stamp > commit_time)
                    need(period == 'pre' or result['commit_before_transaction'], 'post sale preceded commit')
                    result.update(period=period, utc=stamp.isoformat(), block=block_number,
                                  gas_used=row['gas_used'], gas_price_wei=row['gas_price_wei'])
                    strict.append(result)
    for verified in strict:
        need(trades[verified['transaction_hash']]['swap_count'] == 1, 'multiple pool events in 0x evidence')
    strict.sort(key=lambda a: a['utc'])
    events.sort(key=lambda a: (a['block'], a['log_index']))
    trades_all = sorted(trades.values(), key=lambda a: (a['block'], a['transaction_hash']))
    summary = {}
    for period in WINDOWS:
        rows = [r for r in trades_all if r['period'] == period]
        amounts = sorted(r['gas_wei'] for r in rows)
        event_rows = [r for r in events if r['period'] == period]
        summary[period] = {
            'swap_logs': len(event_rows), 'unique_hashes': len(rows),
            'sell_events': sum(r['seth_direction_from_trader'] == 'sell' for r in event_rows),
            'buy_events': sum(r['seth_direction_from_trader'] == 'buy' for r in event_rows),
            'strict_0x_sales': sum(r['strict_0x_close'] for r in rows),
            'v3_legacy_router_txs': sum(r['target'].lower() == V3ROUTER for r in rows),
            'gas_ETH_min_median_max': [decimal_units(v) for v in [amounts[0], median([Decimal(x) for x in amounts]), amounts[-1]]]
        }
    evidence = {'commit_utc': commit_time.isoformat(), 'list_count_before': len(old),
                'list_count_mainnet': len(current), 'pools': list(pools.values()),
                'window_summary': summary, 'strict_0x_paths': strict}
    save(dest, 'results', evidence)
    output_csv(dest, 'pools', list(pools.values()))
    output_csv(dest, 'swap_events', events)
    output_csv(dest, 'transactions', trades_all)
    output_csv(dest, 'matched_0x_sales', [{k: v for k, v in row.items() if k != 'replay'} for row in strict])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=here / 'raw')
    parser.add_argument('--out', type=Path, default=here / 'derived')
    parser.add_argument('--collect', action='store_true',
                        help='fetch a fresh raw-data directory before auditing (network required)')
    args = parser.parse_args()
    if args.collect:
        collect(args.raw)
    audit(args.raw, args.out)


if __name__ == '__main__':
    main()
