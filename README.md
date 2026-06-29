# Tanium-MS_EOL

Microsoft 제품의 EOL(End-of-Life) 정보를 공식 소스에서 수집하여
[endoflife.date](https://endoflife.date) 호환 JSON 포맷으로 생성하는 스크립트와 데이터입니다.

---

## 구조

```
Tanium-MS_EOL/
├── Generate_EOL_JSON.py        # 통합 수집 스크립트 (Microsoft Fixed/Modern)
└── data/
    ├── [Microsoft Fixed Lifecycle]
    │   ├── ms-msexchange-eol.json      Exchange Server 2013~Subscription Ed
    │   ├── ms-sharepoint-eol.json      SharePoint 2013~Subscription Ed
    │   ├── ms-visual-studio-eol.json   Visual Studio 2013~2022
    │   ├── ms-office-eol.json          Office 2016~2024 / Microsoft 365
    │   ├── ms-dotnetfx-eol.json        .NET Framework 3.0~4.8.1
    │   └── ms-visual-cpp-eol.json      Visual C++ 2013~2022
    │
    └── [Microsoft Modern Lifecycle]
        └── edge-latest.json            Microsoft Edge 최신 버전 정보
```

---

## 데이터 소스

| 벤더 | 소스 | 방식 |
|---|---|---|
| **Microsoft Fixed** | `learn.microsoft.com/en-us/lifecycle/products/` | HTTP 스크래핑 |
| **Microsoft Modern** | `edgeupdates.microsoft.com/api/products` | 공개 API |

> **SQL Server**: endoflife.date API(`mssqlserver`)에서 SP 수준 데이터를 제공하므로
> MS Lifecycle 스크래핑 대신 endoflife.date를 사용합니다.

---

## JSON 포맷

### Fixed Lifecycle (날짜 기반)

```json
[
  {
    "cycle": "2022",
    "releaseLabel": "Exchange Server 2022",
    "releaseDate": "2022-11-16",
    "eol": "2033-01-11",
    "support": "2028-01-11",
    "lts": false,
    "link": "https://learn.microsoft.com/en-us/lifecycle/products/exchange-server-2022"
  }
]
```

### Modern Lifecycle (최신 버전 비교)

```json
{
  "latest_major": 149,
  "latest_version": "149.0.4022.80",
  "published": "2026-06-02",
  "policy": "Modern Lifecycle - only the latest major version is supported"
}
```

---

## 사용법

```bash
# 전체 생성 (Microsoft Fixed + Modern)
python3 Generate_EOL_JSON.py

# 벤더별 실행
python3 Generate_EOL_JSON.py --vendor microsoft    # MS Fixed Lifecycle만
python3 Generate_EOL_JSON.py --vendor edge         # MS Modern Lifecycle (Edge)만
python3 Generate_EOL_JSON.py --vendor endoflife    # endoflife.date API만

# 특정 제품만
python3 Generate_EOL_JSON.py --product msexchange
python3 Generate_EOL_JSON.py --product mssqlserver

# 저장 경로 지정
python3 Generate_EOL_JSON.py --output ./my-output
```

---

## GitHub Actions

매주 월요일 오전 9시(UTC) 자동 실행되며, 수동으로도 실행 가능합니다.

**수동 실행**: Actions 탭 → `Update EOL Data` → `Run workflow` → vendor 선택

| vendor 옵션 | 수집 대상 |
|---|---|
| `all` (기본) | Microsoft Fixed + Edge 전체 |
| `microsoft` | MS Fixed Lifecycle만 |
| `edge` | Edge Modern Lifecycle만 |
| `endoflife` | endoflife.date API만 |

---

## 최종 업데이트

2026-06-29
