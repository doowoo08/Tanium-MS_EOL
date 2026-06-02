"""
Generate_MS_Lifecycle_JSON.py

Microsoft Lifecycle 공식 페이지에서 EOL 정보를 수집하여
endoflife.date JSON 포맷으로 변환/저장합니다.

사용법:
    python3 Generate_MS_Lifecycle_JSON.py
    python3 Generate_MS_Lifecycle_JSON.py --output ./files   (저장 경로 지정)
    python3 Generate_MS_Lifecycle_JSON.py --product mssqlserver   (단일 제품)

출력 파일 (endoflife.date 포맷):
    mssqlserver-eol.json       - SQL Server
    msexchange-eol.json        - Exchange Server
    sharepoint-eol.json        - SharePoint
    visual-studio-eol.json     - Visual Studio
    office-eol.json            - Microsoft Office
    dotnetfx-eol.json          - .NET Framework
    visual-cpp-eol.json        - Visual C++ Redistributable (신규)

Copyright (c) 2026 Tanium
"""

import json
import re
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, date
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────────

BASE_URL = "https://learn.microsoft.com/en-us/lifecycle/products"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# 제품 정의: output_file -> [(cycle, ms_product_slug), ...]
# cycle: endoflife.date와 동일한 cycle 값 (연도 또는 버전)
PRODUCTS = {
    "mssqlserver-eol.json": {
        "description": "Microsoft SQL Server",
        "items": [
            ("2025", "sql-server-2025"),
            ("2022", "sql-server-2022"),
            ("2019", "sql-server-2019"),
            ("2017", "sql-server-2017"),
            ("2016", "sql-server-2016"),
            ("2014", "sql-server-2014"),
            ("2012", "sql-server-2012"),
            ("2008", "sql-server-2008"),
        ]
    },
    "msexchange-eol.json": {
        "description": "Microsoft Exchange Server",
        "items": [
            ("Subscription Edition", "exchange-server-subscription-edition"),
            ("2019",                 "exchange-server-2019"),
            ("2016",                 "exchange-server-2016"),
            ("2013",                 "exchange-server-2013"),
        ]
    },
    "sharepoint-eol.json": {
        "description": "Microsoft SharePoint Server",
        "items": [
            ("Subscription Edition", "sharepoint-server-subscription-edition"),
            ("2019",                 "sharepoint-server-2019"),
            ("2016",                 "sharepoint-server-2016"),
            ("2013",                 "sharepoint-server-2013"),
        ]
    },
    "visual-studio-eol.json": {
        "description": "Microsoft Visual Studio",
        "items": [
            ("2022", "visual-studio-2022"),
            ("2019", "visual-studio-2019"),
            ("2017", "visual-studio-2017"),
            ("2015", "visual-studio-2015"),
            ("2013", "visual-studio-2013"),
        ]
    },
    "office-eol.json": {
        "description": "Microsoft Office / Microsoft 365",
        "items": [
            ("2024",            "office-ltsc-2024"),
            ("2021",            "office-2021"),
            ("2019",            "microsoft-office-2019"),
            ("2016",            "microsoft-office-2016"),
            ("Microsoft 365",   "microsoft-365-apps"),
        ]
    },
    "dotnetfx-eol.json": {
        "description": "Microsoft .NET Framework",
        # 단일 페이지에 모든 버전이 포함 - single_page=True 로 처리
        "single_page": "microsoft-net-framework",
        "version_map": {
            "4.8.1": ".NET Framework 4.8.1",
            "4.8":   ".NET Framework 4.8",
            "4.7.2": ".NET Framework 4.7.2",
            "4.7.1": ".NET Framework 4.7.1",
            "4.7":   ".NET Framework 4.7",
            "4.6.2": ".NET Framework 4.6.2",
            "4.6.1": ".NET Framework 4.6.1",
            "4.6":   ".NET Framework 4.6",
            "4.5.2": ".NET Framework 4.5.2",
            "4.5.1": ".NET Framework 4.5.1",
            "4.5":   ".NET Framework 4.5",
            "4.0":   ".NET Framework 4.0",
            "3.5":   ".NET Framework 3.5 Service Pack 1",
            "3.0":   ".NET Framework 3.0",
        },
        "items": []  # single_page 방식에서는 items 불필요
    },
    "visual-cpp-eol.json": {
        "description": "Microsoft Visual C++ Redistributable",
        # Visual C++ 은 Visual Studio 와 동일한 lifecycle 적용
        # (MS 공식: VC++ Redistributable은 동일 버전 VS의 EOL을 따름)
        "items": [
            ("2022", "visual-studio-2022"),
            ("2019", "visual-studio-2019"),
            ("2017", "visual-studio-2017"),
            ("2015", "visual-studio-2015"),
            ("2013", "visual-studio-2013"),
        ]
    },
}

# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

def fetch_page(slug: str) -> str:
    url = f"{BASE_URL}/{slug}"
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
    """ISO 8601 날짜 문자열을 yyyy-MM-dd 로 정규화"""
    raw = raw.strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def parse_lifecycle_page(html: str, slug: str):
    """
    Microsoft Lifecycle 페이지에서 Support Dates 테이블 파싱
    반환: [(listing, start_date, mainstream_end, extended_end), ...]
    """
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
    results = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not cells:
            continue
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        # 날짜가 포함된 행만
        if not any(re.search(r"\d{4}-\d{2}-\d{2}", c) for c in clean):
            continue
        # 컬럼 수에 따라 파싱
        if len(clean) >= 4:
            listing      = clean[0]
            start_date   = parse_date(clean[1])
            mainstream   = parse_date(clean[2])
            extended     = parse_date(clean[3])
        elif len(clean) == 3:
            listing      = clean[0]
            start_date   = parse_date(clean[1])
            mainstream   = ""
            extended     = parse_date(clean[2])
        else:
            continue
        results.append({
            "listing":     listing,
            "releaseDate": start_date,
            "mainstream":  mainstream,
            "eol":         extended or mainstream,  # extended가 없으면 mainstream 사용
        })
    return results


def build_eol_entry(cycle: str, slug: str, rows: list) -> dict:
    """
    endoflife.date 포맷으로 변환 (필드명 endoflife.date 동일하게 맞춤)
    {
        "cycle":        "2022",           <- 연도 기반 (센서 year 타입과 매칭)
        "releaseLabel": "SQL Server 2022" <- 표시용 이름
        "releaseDate":  "2022-11-16",
        "eol":          "2033-01-11",     <- Extended Support End
        "support":      "2028-01-11",     <- Mainstream Support End (endoflife.date와 동일 필드명)
        "lts":          false,
        "link":         "https://..."
    }
    """
    if not rows:
        return None

    main_row = rows[0]

    # eol 날짜가 없으면 False (endoflife.date 규칙: 지원 중 = False)
    eol_val = main_row["eol"] if main_row["eol"] else False

    entry = {
        "cycle":        cycle,
        "releaseLabel": main_row["listing"],
        "releaseDate":  main_row["releaseDate"],
        "eol":          eol_val,
        "lts":          False,
        "link":         f"{BASE_URL}/{slug}",
    }

    # Mainstream → support 필드 (endoflife.date 동일)
    if main_row.get("mainstream") and main_row["mainstream"] != main_row["eol"]:
        entry["support"] = main_row["mainstream"]

    return entry


# ── 메인 실행 ──────────────────────────────────────────────────────────────────

def generate(output_dir: Path, product_filter: str = None):
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    targets = PRODUCTS
    if product_filter:
        targets = {k: v for k, v in PRODUCTS.items()
                   if product_filter.lower() in k.lower()}
        if not targets:
            print(f"제품 '{product_filter}' 없음. 가능한 키: {list(PRODUCTS.keys())}")
            return

    for filename, meta in targets.items():
        print(f"\n[{meta['description']}] → {filename}")
        eol_list = []

        # ── single_page 방식 (.NET Framework 등) ─────────────────────────
        if meta.get("single_page"):
            slug = meta["single_page"]
            print(f"  Fetching (single page): {slug} ...", end=" ", flush=True)
            html = fetch_page(slug)
            if not html:
                print("SKIP")
            else:
                rows = parse_lifecycle_page(html, slug)
                print(f"OK ({len(rows)} rows)")
                version_map = meta.get("version_map", {})
                for cycle, label in version_map.items():
                    matched = [r for r in rows if label.lower() in r["listing"].lower()]
                    if matched:
                        entry = build_eol_entry(cycle, slug, matched)
                        if entry:
                            entry["releaseLabel"] = label
                            eol_list.append(entry)
                    else:
                        # eol 날짜 없는 경우 (지원 중)
                        base = [r for r in rows if r["listing"] == "Microsoft .NET Framework"]
                        release_row = [r for r in rows if label.lower() in r["listing"].lower()]
                        if release_row:
                            eol_list.append({
                                "cycle": cycle,
                                "releaseLabel": label,
                                "releaseDate": release_row[0]["releaseDate"],
                                "eol": False,
                                "lts": False,
                                "link": f"{BASE_URL}/{slug}",
                            })

        # ── items 방식 (일반) ─────────────────────────────────────────────
        else:
            for cycle, slug in meta["items"]:
                print(f"  Fetching: {slug} ...", end=" ", flush=True)
                html = fetch_page(slug)

                if not html:
                    print("SKIP (페이지 없음)")
                    continue

                rows = parse_lifecycle_page(html, slug)
                if not rows:
                    print("SKIP (날짜 파싱 실패)")
                    continue

                entry = build_eol_entry(cycle, slug, rows)
                if entry:
                    eol_list.append(entry)
                    eol_str = entry.get("eol", "?")
                    print(f"OK  eol={eol_str}")
                else:
                    print("SKIP (엔트리 생성 실패)")

                time.sleep(0.5)

        if eol_list:
            out_path = output_dir / filename
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(eol_list, f, indent=2, ensure_ascii=False)
            print(f"  -> {out_path} ({len(eol_list)}개 항목)")
        else:
            print(f"  -> 저장 스킵 (데이터 없음)")

    print(f"\n완료. 생성일: {today}")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Microsoft Lifecycle → endoflife.date 포맷 JSON 생성"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(Path(__file__).parent / "files"),
        help="JSON 저장 경로 (기본: ./files)"
    )
    parser.add_argument(
        "--product", "-p",
        default=None,
        help="특정 제품만 생성 (예: mssqlserver, visual-cpp)"
    )
    args = parser.parse_args()

    generate(Path(args.output), args.product)
