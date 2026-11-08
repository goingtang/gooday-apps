"""Builds the Taiwan pet-business directory from Ministry of Agriculture open data.

Sources (政府資料開放授權條款－第 1 版, free for commercial use with attribution):
  - 獸醫師(佐)開業執照 (animal hospitals): data.moa.gov.tw UnitId=078
  - 合法特定寵物業名單 (breeding / selling / boarding): data.moa.gov.tw UnitId=fNT9RMo8PQRO
Privacy: owner and staff names of pet businesses are NOT kept. The responsible vet of a
hospital is public licensing information and is kept.

Usage (from the repo root):  python3 scripts/build-tw-pets.py
Writes petpal/data/tw-pets.json (served by GitHub Pages; the PetPal app downloads it).
"""
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_WEB = os.path.join(HERE, '..', 'petpal', 'data', 'tw-pets.json')

VET_URL = 'https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=078&IsTransData=1'
BIZ_URL = 'https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=fNT9RMo8PQRO&IsTransData=1'

COUNTY_CODES = {
    'A010': '臺北市', 'A020': '新北市', 'A030': '基隆市', 'A040': '高雄市', 'A060': '臺中市', 'A090': '桃園市',
    'A100': '新竹市', 'A110': '新竹縣', 'A130': '苗栗縣', 'A150': '南投縣', 'A170': '彰化縣', 'A180': '雲林縣',
    'A190': '嘉義市', 'A200': '嘉義縣', 'A210': '臺南市', 'A240': '屏東縣', 'A260': '宜蘭縣', 'A280': '花蓮縣',
    'A300': '臺東縣', 'A310': '澎湖縣', 'A320': '金門縣', 'A330': '連江縣',
}
COUNTIES = list(COUNTY_CODES.values())
RANKS = {'A': '優等', 'B': '甲等', 'C': '乙等', 'D': '丙等'}  # from the API spec


def fetch(url):
    # Any network or JSON error raises, so the script exits non-zero and the workflow commits nothing.
    req = urllib.request.Request(url, headers={'User-Agent': 'PetPal-data-builder (+https://goingtang.github.io/gooday-apps/)'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8-sig'))


def clean(s, n=120):
    # Same limits the app's validator enforces (src/lib/twpets-core.ts): no control characters or angle brackets.
    s = re.sub(r'[\x00-\x1f<>]', ' ', str(s or ''))
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:n]


def norm_county(s):
    return s.replace('台', '臺')


DISTRICT = re.compile(r'^(.{2,3}?[縣市])(.{1,4}?[鄉鎮市區])')


def split_area(addr, county_hint=''):
    a = norm_county(re.sub(r'^\d{3,6}', '', addr.replace(' ', '')))
    county, district = '', ''
    for c in COUNTIES:
        if a.startswith(c):
            county = c
            rest = a[len(c):]
            m = re.match(r'(.{1,4}?[鄉鎮市區])', rest)
            district = m.group(1) if m else ''
            break
    if not county:
        county = norm_county(county_hint)
        m = re.match(r'(.{1,4}?[鄉鎮市區])', a)
        district = m.group(1) if m and not a.startswith(county) else ''
    return county, district


def phone(s):
    s = clean(s, 40)
    return s if re.search(r'\d{6,}', re.sub(r'\D', '', s) or '') else ''


def main():
    today = datetime.date.today().isoformat()
    vets_raw = fetch(VET_URL)
    biz_raw = fetch(BIZ_URL)

    vets = []
    for x in vets_raw:
        if x.get('狀態') not in ('開業', '補發'):
            continue
        name, addr = clean(x.get('機構名稱')), clean(x.get('機構地址'), 160)
        if not name or not addr:
            continue
        county, district = split_area(addr, x.get('縣市', ''))
        vets.append({'n': name, 'a': addr, 'c': county, 'd': district, 'p': phone(x.get('機構電話')), 'v': clean(x.get('負責獸醫'), 20)})

    biz = []
    for x in biz_raw:
        if x.get('state_flag') != 'N':  # N = 營業中 (P 歇業, S 停業, B 廢止)
            continue
        valid = str(x.get('validdate') or '')[:10].replace('/', '-')
        if not re.match(r'\d{4}-\d{2}-\d{2}', valid) or valid < today:
            continue
        name, addr = clean(x.get('legalname')), clean(x.get('legaladdress'), 160)
        items = ''.join(ch for ch in str(x.get('busitem') or '') if ch in 'ABC')
        if not name or not addr or not items:
            continue
        county, district = split_area(addr, COUNTY_CODES.get(x.get('legaltype', ''), ''))
        rank = RANKS.get(x.get('rank_code', '')) if x.get('rank_flag_1') == 'Y' else None
        row = {'n': name, 'a': addr, 'c': county, 'd': district, 'b': items, 's': clean(x.get('animaltype'), 40), 'l': clean(x.get('validnum'), 40), 'e': valid}
        if rank:
            row['r'] = rank
            row['y'] = clean(x.get('rank_year'), 4)
        biz.append(row)

    # A bad upstream day (outage, empty or truncated export) must never replace good data: fail instead.
    if len(vets) < 1000 or len(biz) < 1000:
        sys.exit(f'refusing to write: only {len(vets)} hospitals and {len(biz)} businesses (expected 1000+ each)')

    vets.sort(key=lambda r: (r['c'], r['d'], r['n']))
    biz.sort(key=lambda r: (r['c'], r['d'], r['n']))
    out = {
        'v': 1,
        'updatedAt': today,
        'source': '農業部「獸醫師(佐)開業執照」「合法特定寵物業名單」',
        'license': '政府資料開放授權條款－第 1 版',
        'vets': vets,
        'biz': biz,
    }
    data = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    for path in (OUT_WEB,):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        # keep the old file when only the date changed, so the monthly job doesn't make empty commits
        if old and json.loads(old) | {'updatedAt': today} == out:
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
    no_district = sum(1 for r in vets + biz if not r['d'])
    print(f'vets {len(vets)}/{len(vets_raw)}  businesses {len(biz)}/{len(biz_raw)}  no district {no_district}  size {len(data.encode()) / 1024:.0f} KB', file=sys.stderr)


if __name__ == '__main__':
    main()
