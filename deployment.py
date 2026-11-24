#!/usr/bin/env python3
"""Audit historical production-deployment claims and listing changes."""
import argparse
import json
from datetime import datetime, timezone

from census import ROOT, fetch, need, pool_index, read

REV = '4078390a4890445d1ff0ed5196fd4cb56a44de87'
LATER = 'b416603ff483679eedb795141cb9c376ee9b5086'
REPO = 'https://api.github.com/repos/Uniswap/interface'
PROD = REPO + '/deployments/397083627'
HOST = 'https://app.uniswap.org'
TWEET = '1418697012095164420'
FILES = {
    'production_deployment.json': PROD,
    'production_statuses.json': PROD + '/statuses?per_page=100',
    'pr_2100.json': REPO + '/pulls/2100',
    'pr_comments.json': REPO + '/issues/2100/comments?per_page=100',
    'list_history_until_end.json': REPO + '/commits?path=src/constants/tokenLists/unsupported.tokenlist.json&until=2021-08-07T00%3A00%3A00Z',
    'list_20210806.json': f'https://raw.githubusercontent.com/Uniswap/interface/{LATER}/src/constants/tokenLists/unsupported.tokenlist.json',
    'hooks_20210806.ts': f'https://raw.githubusercontent.com/Uniswap/interface/{LATER}/src/state/lists/hooks.ts',
    'tweet_syndication.json': f'https://cdn.syndication.twimg.com/tweet-result?id={TWEET}&lang=en&token=0',
    'archive_available_0724.json': 'https://archive.org/wayback/available?url=https%3A%2F%2Fapp.uniswap.org%2F&timestamp=20210724064834',
    'archive_available_0727.json': 'https://archive.org/wayback/available?url=https%3A%2F%2Fapp.uniswap.org%2F&timestamp=20210727081456',
}


def parse_time(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def fmt_archive(ser):
    return datetime.strptime(ser, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)


def load(base,name):
    return json.loads((base/name).read_text(encoding='utf-8'))


def analyze(base, baseline, census, summary, output):
    commit = load(baseline,'commit_2021.json')
    deploy = load(base,'production_deployment.json')
    statuses = load(base,'production_statuses.json')
    pr = load(base,'pr_2100.json')
    msg = load(base,'tweet_syndication.json')
    need(commit['sha']==deploy['sha']==REV and pr['merge_commit_sha']==REV
         and deploy['creator']['login']=='vercel[bot]' and deploy['environment']=='Production',
         'production record and pinned commit mismatch')
    need(all(x['deployment_url']==PROD for x in statuses),'deployment status provenance mismatch')
    need(msg['id_str']==TWEET and msg['user']['screen_name'].lower()=='uniswap'
         and any('app.uniswap.org' in x['expanded_url'] for x in msg['entities']['urls']),
         'official announcement provenance mismatch')
    tweet_utc = parse_time(msg['created_at'])
    snap = load(base,'archive_available_0724.json')['archived_snapshots']['closest']
    need(snap['available'] and snap['status']=='200' and 'app.uniswap.org/' in snap['url'],'missing capture index')
    capture = fmt_archive(snap['timestamp'])
    listed = {r['address'].lower():r['symbol'] for r in load(baseline,'list_2021.json')['tokens']
              if r['chainId']==1}
    updated = {r['address'].lower():r['symbol'] for r in load(base,'list_20210806.json')['tokens']
               if r['chainId']==1}
    diff = sorted(updated.keys()-listed.keys())
    need(len(listed)==129 and len(updated)==130 and not(listed.keys()-updated.keys())
         and len(diff)==1 and updated[diff[0]]=='DYDX','updated list changed')
    history=load(base,'list_history_until_end.json')
    need([r['sha'] for r in history[:2]]==[LATER,REV],'list commit history differs')
    all_pools = pool_index(read(census,'factory_a'))
    updated_new_pools = [p['pool'] for p in all_pools.values() if set(diff) & {p['token0'],p['token1']}]
    after = min(parse_time(x['utc']) for x in load(summary.parent,summary.name)['strict_paths']
                if parse_time(x['utc']) > tweet_utc)
    commit_utc=parse_time(commit['commit']['committer']['date'])
    deployment_utc=parse_time(deploy['created_at'])
    finish_with_domain=[x for x in statuses if x['state']=='success'
                        and (x.get('environment_url') or '').rstrip('/')==HOST]
    archive_audit = load(base,'archive_probes.json')
    raw_recovered=any(x.get('name')=='snapshot_20210724063600_id_' and x.get('status')==200
                      for x in archive_audit)
    result = {
      'commit_utc':commit_utc.isoformat(),'merged_utc':pr['merged_at'],
      'deployment_requested_utc':deployment_utc.isoformat(),'environment_label':deploy['environment'],
      'production_environment_field':deploy.get('production_environment'),
      'observed_deployment_states':[x['state'] for x in statuses],
      'official_announcement_utc':tweet_utc.isoformat(),'wayback_capture_utc':capture.isoformat(),
      'wayback_capture_url':snap['url'],'first_closed_sale_utc':after.isoformat(),
      'seconds_from_commit_to_sale':int((after-commit_utc).total_seconds()),
      'seconds_from_announcement_to_sale':int((after-tweet_utc).total_seconds()),
      'seconds_from_capture_to_sale':int((after-capture).total_seconds()),
      'observed_domain_success_status':bool(finish_with_domain),'archived_html_accessed_at_capture':raw_recovered,
      'aug6_list_edit_utc':history[0]['commit']['committer']['date'],
      'new_listed_token':{'symbol':updated[diff[0]],'address':diff[0]},
      'pools_matching_aug6_new_address':updated_new_pools
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/'deployment_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=type(ROOT),default=ROOT/'raw'/'deployment')
    ap.add_argument('--baseline',type=type(ROOT),default=ROOT/'baseline'/'raw')
    ap.add_argument('--census',type=type(ROOT),default=ROOT/'raw'/'census')
    ap.add_argument('--out',type=type(ROOT),default=ROOT/'derived')
    ap.add_argument('--summary',type=type(ROOT))
    ap.add_argument('--collect',action='store_true',help='refresh official JSON snapshots, preserving archived HTTP error reports')
    args=ap.parse_args()
    if args.collect:
        args.raw.mkdir(parents=True,exist_ok=True)
        for name,url in FILES.items():
            (args.raw/name).write_bytes(fetch(url))
    analyze(args.raw,args.baseline,args.census,args.summary or args.out/'census_summary.json',args.out)


if __name__=='__main__': main()
