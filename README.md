# Tanium-MS_EOL

Microsoft 공식 Lifecycle 페이지에서 제품별 EOL(End-of-Life) 정보를 수집하여
[endoflife.date](https://endoflife.date) JSON 포맷으로 변환하는 스크립트와 데이터입니다.

## 구조

```
Tanium-MS_EOL/
├── Generate_MS_Lifecycle_JSON.py   # 수집 스크립트
└── data/                           # 생성된 EOL JSON 파일
    ├── mssqlserver-eol.json        SQL Server 2014~2025
    ├── msexchange-eol.json         Exchange Server 2013~Subscription Ed
    ├── sharepoint-eol.json         SharePoint 2013~Subscription Ed
    ├── visual-studio-eol.json      Visual Studio 2013~2022
    ├── office-eol.json             Office 2016~2024 / Microsoft 365
    ├── dotnetfx-eol.json           .NET Framework 3.0~4.8.1
    └── visual-cpp-eol.json         Visual C++ 2013~2022
```

## 데이터 소스

- **Microsoft 공식 Lifecycle 페이지**: https://learn.microsoft.com/en-us/lifecycle/products/
- Visual C++ Redistributable은 Visual Studio와 동일한 Lifecycle 적용

## JSON 포맷 (endoflife.date 호환)

```json
[
  {
    "cycle": "2022",
    "releaseLabel": "SQL Server 2022",
    "releaseDate": "2022-11-16",
    "eol": "2033-01-11",
    "support": "2028-01-11",
    "lts": false,
    "link": "https://learn.microsoft.com/en-us/lifecycle/products/sql-server-2022"
  }
]
```

| 필드 | 설명 |
|---|---|
| `cycle` | 연도 기반 버전 (2022, 2019 등) |
| `releaseLabel` | 제품 표시명 |
| `releaseDate` | 출시일 |
| `eol` | Extended Support 종료일 (지원 중이면 `false`) |
| `support` | Mainstream Support 종료일 |
| `lts` | LTS 여부 |
| `link` | Microsoft Lifecycle 페이지 URL |

## 사용법

```bash
# 전체 제품 생성
python3 Generate_MS_Lifecycle_JSON.py

# 특정 제품만
python3 Generate_MS_Lifecycle_JSON.py --product mssqlserver

# 저장 경로 지정
python3 Generate_MS_Lifecycle_JSON.py --output ./my-output
```

## 업데이트

Microsoft Lifecycle 페이지가 업데이트되면 스크립트를 재실행하여 JSON을 갱신하세요.

```bash
python3 Generate_MS_Lifecycle_JSON.py --output ./data
```

## 생성일

2026-06-02
