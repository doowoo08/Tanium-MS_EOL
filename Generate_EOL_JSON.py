"""
Generate_EOL_JSON.py

여러 벤더의 공식 소스에서 EOL(End-of-Life) 정보를 수집하여
endoflife.date 호환 JSON 포맷으로 생성합니다.

지원 벤더:
  - Microsoft  : Lifecycle 공식 페이지 스크래핑 (날짜 기반 EOL)
  - Microsoft  : Edge API (Modern Lifecycle 최신 버전 비교)
  - Adobe      : EOL Matrix 페이지 (Selenium, JavaScript 렌더링 필요)

출력 파일:
  [Microsoft Fixed Lifecycle]
    ms-mssqlserver-eol.json    SQL Server
    ms-msexchange-eol.json     Exchange Server
    ms-sharepoint-eol.json     SharePoint
    ms-visual-studio-eol.json  Visual Studio
    ms-office-eol.json         Microsoft Office / Microsoft 365
    ms-dotnetfx-eol.json       .NET Framework
    ms-visual-cpp-eol.json     Visual C++ Redistributable

  [Microsoft Modern Lifecycle]
    edge-latest.json           Microsoft Edge (+ Copilot, Edge WebView2 공용)

  [Adobe]
    adobe-acrobat-eol.json     Acrobat Pro / Standard / Reader (Classic Track)
    adobe-elements-eol.json    Photoshop Elements / Premiere Elements
    adobe-discontinued-eol.json Flash Player, Photoshop Camera 등 완전 종료 제품

사용법:
    python3 Generate_EOL_JSON.py                        # 전체 생성
    python3 Generate_EOL_JSON.py --vendor microsoft     # Microsoft만
    python3 Generate_EOL_JSON.py --vendor adobe         # Adobe만
    python3 Generate_EOL_JSON.py --vendor edge          # Edge Modern Lifecycle만
    python3 Generate_EOL_JSON.py --product mssqlserver  # 특정 제품만
    python3 Generate_EOL_JSON.py --output ./files       # 저장 경로 지정

사전 요구사항 (Adobe):
    pip install selenium webdriver-manager

Copyright (c) 2026 Tanium
"""

import json
import re
import time
import argparse
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

# ── 공통 설정 ──────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":     "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
MS_LIFECYCLE_BASE = "https://learn.microsoft.com/en-us/lifecycle/products"

# ══════════════════════════════════════════════════════════════════════════════
# PART 1: Microsoft Fixed Lifecycle
# ══════════════════════════════════════════════════════════════════════════════

FIXED_PRODUCTS = {
    "ms-mssqlserver-eol.json": {
        "description": "Microsoft SQL Server",
        "items": [
            ("2025", "sql-server-2025"), ("2022", "sql-server-2022"),
            ("2019", "sql-server-2019"), ("2017", "sql-server-2017"),
            ("2016", "sql-server-2016"), ("2014", "sql-server-2014"),
            ("2012", "sql-server-2012"), ("2008", "sql-server-2008"),
        ]
    },
    "ms-msexchange-eol.json": {
        "description": "Microsoft Exchange Server",
        "items": [
            ("Subscription Edition", "exchange-server-subscription-edition"),
            ("2019", "exchange-server-2019"), ("2016", "exchange-server-2016"),
            ("2013", "exchange-server-2013"),
        ]
    },
    "ms-sharepoint-eol.json": {
        "description": "Microsoft SharePoint Server",
        "items": [
            ("Subscription Edition", "sharepoint-server-subscription-edition"),
            ("2019", "sharepoint-server-2019"), ("2016", "sharepoint-server-2016"),
            ("2013", "sharepoint-server-2013"),
        ]
    },
    "ms-visual-studio-eol.json": {
        "description": "Microsoft Visual Studio",
        "items": [
            ("2022", "visual-studio-2022"), ("2019", "visual-studio-2019"),
            ("2017", "visual-studio-2017"), ("2015", "visual-studio-2015"),
            ("2013", "visual-studio-2013"),
        ]
    },
    "ms-office-eol.json": {
        "description": "Microsoft Office / Microsoft 365",
        "items": [
            ("2024", "office-ltsc-2024"),      ("2021", "office-2021"),
            ("2019", "microsoft-office-2019"), ("2016", "microsoft-office-2016"),
            ("Microsoft 365", "microsoft-365-apps"),
        ]
    },
    "ms-dotnetfx-eol.json": {
        "description": "Microsoft .NET Framework",
        "single_page": "microsoft-net-framework",
        "version_map": {
            "4.8.1": ".NET Framework 4.8.1", "4.8":   ".NET Framework 4.8",
            "4.7.2": ".NET Framework 4.7.2", "4.7.1": ".NET Framework 4.7.1",
            "4.7":   ".NET Framework 4.7",   "4.6.2": ".NET Framework 4.6.2",
            "4.6.1": ".NET Framework 4.6.1", "4.6":   ".NET Framework 4.6",
            "4.5.2": ".NET Framework 4.5.2", "4.5.1": ".NET Framework 4.5.1",
            "4.5":   ".NET Framework 4.5",   "4.0":   ".NET Framework 4.0",
            "3.5":   ".NET Framework 3.5 Service Pack 1",
            "3.0":   ".NET Framework 3.0",
        },
        "items": []
    },
    "ms-visual-cpp-eol.json": {
        "description": "Microsoft Visual C++ Redistributable",
        "items": [
            ("2022", "visual-studio-2022"), ("2019", "visual-studio-2019"),
            ("2017", "visual-studio-2017"), ("2015", "visual-studio-2015"),
            ("2013", "visual-studio-2013"),
        ]
    },
}

# ── Microsoft Fixed Lifecycle 헬퍼 ────────────────────────────────────────────

def fetch_page(slug: str) -> str:
    url = f"{MS_LIFECYCLE_BASE}/{slug}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {url}")
        return ""
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return ""

def parse_date(raw: str) -> str:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw.strip())
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def parse_lifecycle_page(html: str, slug: str):
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
    results = []
    esu_dates = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not cells: continue
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if not any(re.search(r"\d{4}-\d{2}-\d{2}", c) for c in clean): continue
        # ESU 행: 3컬럼 + "Extended Security Updates" 포함
        if len(clean) == 3 and "extended security" in clean[0].lower():
            esu_end = parse_date(clean[2])
            if esu_end:
                esu_dates.append(esu_end)
            continue
        if len(clean) >= 4:
            listing, start, mainstream, extended = clean[0], parse_date(clean[1]), parse_date(clean[2]), parse_date(clean[3])
        elif len(clean) == 3:
            listing, start, mainstream, extended = clean[0], parse_date(clean[1]), "", parse_date(clean[2])
        else:
            continue
        results.append({"listing": listing, "releaseDate": start,
                         "mainstream": mainstream, "eol": extended or mainstream})
    esu_end = max(esu_dates) if esu_dates else None
    return results, esu_end

def build_ms_entry(cycle: str, slug: str, rows: list, esu_end: str = None) -> dict:
    if not rows: return None
    row = rows[0]
    eol_val = row["eol"] if row["eol"] else False
    entry = {"cycle": cycle, "releaseLabel": row["listing"],
             "releaseDate": row["releaseDate"], "eol": eol_val, "lts": False,
             "link": f"{MS_LIFECYCLE_BASE}/{slug}"}
    if row.get("mainstream") and row["mainstream"] != row["eol"]:
        entry["support"] = row["mainstream"]
    if esu_end:
        entry["extendedSupport"] = esu_end
    return entry

def generate_ms_fixed(output_dir: Path, product_filter: str = None):
    targets = FIXED_PRODUCTS
    if product_filter:
        targets = {k: v for k, v in FIXED_PRODUCTS.items()
                   if product_filter.lower() in k.lower()}
        if not targets: return

    for filename, meta in targets.items():
        print(f"\n[MS Fixed] [{meta['description']}] → {filename}")
        eol_list = []

        if meta.get("single_page"):
            slug = meta["single_page"]
            print(f"  Fetching: {slug} ...", end=" ", flush=True)
            html = fetch_page(slug)
            if not html: print("SKIP"); continue
            rows, _ = parse_lifecycle_page(html, slug)
            print(f"OK ({len(rows)} rows)")
            for cycle, label in meta.get("version_map", {}).items():
                matched = [r for r in rows if label.lower() in r["listing"].lower()]
                if matched:
                    entry = build_ms_entry(cycle, slug, matched)
                    if entry: entry["releaseLabel"] = label; eol_list.append(entry)
        else:
            for cycle, slug in meta["items"]:
                print(f"  Fetching: {slug} ...", end=" ", flush=True)
                html = fetch_page(slug)
                if not html: print("SKIP"); continue
                rows, esu_end = parse_lifecycle_page(html, slug)
                if not rows: print("SKIP (날짜 없음)"); continue
                entry = build_ms_entry(cycle, slug, rows, esu_end)
                if entry:
                    eol_list.append(entry)
                    ext = f"  extendedSupport={entry['extendedSupport']}" if "extendedSupport" in entry else ""
                    print(f"OK  eol={entry.get('eol','?')}{ext}")
                else: print("SKIP")
                time.sleep(0.5)

        if eol_list:
            out_path = output_dir / filename
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(eol_list, f, indent=2, ensure_ascii=False)
            print(f"  → {out_path} ({len(eol_list)}개)")


# ══════════════════════════════════════════════════════════════════════════════
# PART 2: Microsoft Modern Lifecycle (Edge API)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_edge() -> dict:
    url = "https://edgeupdates.microsoft.com/api/products"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    for item in data:
        if item.get("Product") != "Stable": continue
        releases = item.get("Releases", [])
        win = next((r for r in releases if r.get("Platform") == "Windows"),
                   releases[0] if releases else None)
        if win:
            version   = win["ProductVersion"]
            major     = int(version.split(".")[0])
            published = win.get("PublishedTime", "")[:10]
            return {"latest_major": major, "latest_version": version,
                    "published": published,
                    "policy": "Modern Lifecycle - only the latest major version is supported",
                    "note": "instMajor >= latest_major → Supported / else → Not Latest",
                    "source": url, "fetched": str(date.today())}
    raise RuntimeError("Edge Stable Windows 릴리스 없음")

def generate_edge(output_dir: Path):
    print(f"\n[Edge Modern Lifecycle] → edge-latest.json")
    try:
        result = fetch_edge()
        out_path = output_dir / "edge-latest.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  latest_major={result['latest_major']}  version={result['latest_version']}")
        print(f"  → {out_path}")
    except Exception as e:
        print(f"  ERROR: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PART 3: Adobe EOL Matrix (Selenium 필요)
# ══════════════════════════════════════════════════════════════════════════════

ADOBE_EOL_URL = "https://helpx.adobe.com/support/programs/eol-matrix.html"

def parse_date_us(s: str) -> str:
    """MM/DD/YYYY → YYYY-MM-DD 변환"""
    s = re.sub(r'\xa0.*', '', s).strip()  # extended 날짜 제거
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}" if m2 else ""

def fetch_adobe_eol_html() -> str:
    """Selenium headless Chrome으로 Adobe EOL Matrix 페이지 로드"""
    try:
        import sys
        sys.path.insert(0, '/tmp/pylibs')
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
    except ImportError:
        raise RuntimeError("Selenium이 필요합니다: pip install selenium webdriver-manager")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={HEADERS['User-Agent']}")

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(ADOBE_EOL_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        time.sleep(3)
        return driver.page_source
    finally:
        driver.quit()

def parse_adobe_eol(html: str):
    """Adobe EOL Matrix 파싱 → 제품별 분류"""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)

    acrobat     = []
    elements    = []
    discontinued = []

    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        clean = [re.sub(r'<[^>]+>', '', c).strip().replace('\xa0', '').replace('\n', ' ')
                 for c in cells]
        clean = [c for c in clean if c]
        if len(clean) < 4: continue
        if 'Product name' in clean[0]: continue

        name, ver = clean[0], clean[1]
        # GA = col[3], EOL core = col[4]
        ga_raw  = clean[3] if len(clean) > 3 else ''
        eol_raw = clean[4] if len(clean) > 4 else ''

        ga  = parse_date_us(ga_raw)
        eol = parse_date_us(eol_raw)
        if not ga and not eol: continue

        # Modern Lifecycle 정책 명시 → 스킵 (날짜 없음)
        if any(x in eol_raw.lower() for x in ['current version','n-1','bug fix','security fix']):
            continue

        entry = {"cycle": ver, "releaseLabel": f"{name} {ver}",
                 "releaseDate": ga, "eol": eol if eol else False,
                 "lts": False, "link": ADOBE_EOL_URL}

        name_l = name.lower()

        # Acrobat 계열
        if 'acrobat' in name_l and ('pro' in name_l or 'standard' in name_l or 'reader' in name_l):
            entry["product"] = name
            acrobat.append(entry)

        # Elements 계열 (Photoshop Elements / Premiere Elements)
        elif 'photoshop elements' in name_l or 'premiere elements' in name_l:
            entry["product"] = name
            elements.append(entry)

        # 완전 종료 제품
        elif any(x in name_l for x in ['flash player', 'photoshop camera',
                                         'photoshop sketch', 'muse', 'creative suite',
                                         'illustrator draw', 'premiere clip']):
            entry["product"] = name
            discontinued.append(entry)

    return acrobat, elements, discontinued

def generate_adobe(output_dir: Path):
    print(f"\n[Adobe EOL Matrix] (Selenium 사용)")
    print(f"  URL: {ADOBE_EOL_URL}")
    print(f"  페이지 로딩 중...", end=" ", flush=True)

    try:
        html = fetch_adobe_eol_html()
        print(f"OK ({len(html)} bytes)")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    acrobat, elements, discontinued = parse_adobe_eol(html)

    outputs = [
        ("adobe-acrobat-eol.json",      acrobat,      "Adobe Acrobat (Classic Track)"),
        ("adobe-elements-eol.json",     elements,     "Adobe Elements (Photoshop/Premiere)"),
        ("adobe-discontinued-eol.json", discontinued, "Adobe Discontinued Products"),
    ]

    for filename, data, desc in outputs:
        if not data:
            print(f"  [{desc}] → 데이터 없음, 스킵")
            continue
        out_path = output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  [{desc}] → {out_path} ({len(data)}개)")

        # 샘플 출력
        for entry in data[:2]:
            print(f"    {entry['releaseLabel']}: eol={entry['eol']}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="벤더별 EOL 데이터 수집 (Microsoft Fixed/Modern + Adobe)"
    )
    parser.add_argument("--output", "-o",
        default=str(Path(__file__).parent.parent / "files"),
        help="JSON 저장 경로 (기본: ../files)")
    parser.add_argument("--vendor", "-v",
        choices=["microsoft", "edge", "adobe", "all"], default="all",
        help="수집 벤더 선택 (기본: all)")
    parser.add_argument("--product", "-p", default=None,
        help="특정 제품만 (예: mssqlserver, acrobat)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"저장 경로: {output_dir}")
    print(f"벤더: {args.vendor}  제품 필터: {args.product or '전체'}")

    if args.vendor in ("microsoft", "all"):
        generate_ms_fixed(output_dir, args.product)

    if args.vendor in ("edge", "all"):
        generate_edge(output_dir)

    if args.vendor in ("adobe", "all"):
        generate_adobe(output_dir)

    print(f"\n완료: {date.today()}")
