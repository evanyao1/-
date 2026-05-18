#!/usr/bin/env python3
"""Fetch US market data from Chinese domestic APIs, save as data.json"""
import re, json, time
from datetime import datetime, timezone, timedelta
import requests

STOCKS = [
    ('AAPL',  'gb_aapl',  '苹果'),
    ('MSFT',  'gb_msft',  '微软'),
    ('NVDA',  'gb_nvda',  '英伟达'),
    ('GOOGL', 'gb_googl', '谷歌'),
    ('AMZN',  'gb_amzn',  '亚马逊'),
    ('META',  'gb_meta',  'Meta'),
    ('TSLA',  'gb_tsla',  '特斯拉'),
    ('AMD',   'gb_amd',   'AMD'),
    ('BABA',  'gb_baba',  '阿里巴巴'),
    ('PDD',   'gb_pdd',   '拼多多'),
    ('MSTR',  'gb_mstr',  'MicroStrategy'),
    ('INTC',  'gb_intc',  '英特尔'),
]

INDICES = [
    ('SPX',  'gb_$inx',   '标普500 SPX'),
    ('COMP', 'gb_$compx', '纳斯达克综合'),
    ('DJI',  'gb_$dji',   '道琼斯 DJIA'),
    ('NDX',  'gb_$ndx',   '纳指100 NDX'),
]

FUND_CODES = [
    '110026',  # 易方达标普500
    '270042',  # 广发纳斯达克100
    '000834',  # 工银全球精选
    '050025',  # 博时标普500
    '160213',  # 国泰纳斯达克
    '501500',  # 华夏纳斯达克
    '000071',  # 华夏标普500
    '040046',  # 华安标普500
]

SINA_HEADERS = {
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

FUND_HEADERS = {
    'Referer': 'https://fund.eastmoney.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}


def parse_sina_quote(raw, name=''):
    p = raw.split(',')
    if len(p) < 10 or not p[1]:
        return None
    try:
        price = float(p[1])
        if price <= 0:
            return None
        ah_price = float(p[16]) if len(p) > 16 and p[16] else None
        ah_pct   = float(p[18]) if len(p) > 18 and p[18] else None
        valid_ah = ah_price and ah_price > 0 and abs(ah_price - price) > 0.001
        return {
            'name':      name or p[0],
            'price':     round(price, 4),
            'change':    round(float(p[2]), 4) if p[2] else 0,
            'changePct': round(float(p[3]), 4) if p[3] else 0,
            'high':      round(float(p[8]), 4) if len(p) > 8 and p[8] else 0,
            'low':       round(float(p[9]), 4) if len(p) > 9 and p[9] else 0,
            'ahPrice':   round(ah_price, 4) if valid_ah else None,
            'ahPct':     round(ah_pct, 4)   if valid_ah and ah_pct else None,
        }
    except (ValueError, IndexError) as e:
        print(f'  parse error: {e}')
        return None


def fetch_sina():
    all_codes = [s[1] for s in STOCKS] + [i[1] for i in INDICES]
    url = 'https://hq.sinajs.cn/list=' + ','.join(all_codes)
    print(f'Fetching Sina Finance...')
    r = requests.get(url, headers=SINA_HEADERS, timeout=20)
    text = r.content.decode('gbk', errors='replace')
    print(f'  Got {len(text)} chars')

    raw = {}
    for m in re.finditer(r'var hq_str_([^=\s]+)\s*=\s*"([^"]*)"', text):
        raw[m.group(1)] = m.group(2)
    print(f'  Parsed {len(raw)} quotes')

    stocks = {}
    for ticker, sina_code, name in STOCKS:
        if sina_code in raw:
            q = parse_sina_quote(raw[sina_code], name)
            if q:
                stocks[sina_code] = q

    indices = {}
    for key, sina_code, name in INDICES:
        if sina_code in raw:
            q = parse_sina_quote(raw[sina_code], name)
            if q:
                indices[sina_code] = q

    print(f'  {len(stocks)} stocks, {len(indices)} indices')
    return stocks, indices


def fetch_one_fund(code):
    url = f'https://fundgz.1234567.com.cn/js/{code}.js'
    r = requests.get(url, headers=FUND_HEADERS, timeout=10)
    m = re.search(r'jsonpgz\((\{[^}]+\})\)', r.text)
    if not m:
        return None
    return json.loads(m.group(1))


def fetch_funds():
    print('Fetching fund estimates...')
    funds = {}
    for code in FUND_CODES:
        try:
            data = fetch_one_fund(code)
            if data:
                funds[code] = data
                print(f'  {code} {data.get("name","")} gsz={data.get("gsz","?")} {data.get("gszzl","?")}%')
            else:
                print(f'  {code} no data')
        except Exception as e:
            print(f'  {code} error: {e}')
        time.sleep(0.3)
    return funds


def main():
    print('=== fetch_data.py ===')
    stocks, indices = fetch_sina()
    funds = fetch_funds()

    now_utc = datetime.now(timezone.utc)
    now_cst = now_utc + timedelta(hours=8)

    output = {
        'updated':   now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updatedCN': now_cst.strftime('%Y-%m-%d %H:%M'),
        'stocks':  stocks,
        'indices': indices,
        'funds':   funds,
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)

    print(f'data.json saved — {len(stocks)} stocks, {len(indices)} indices, {len(funds)} funds')
    print(f'Updated: {output["updatedCN"]} CST')


if __name__ == '__main__':
    main()
