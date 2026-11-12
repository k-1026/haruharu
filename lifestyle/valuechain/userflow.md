# 유저 플로우 — 공공 관광기관 담당자 기획 서비스 (v0)

> 기준: 2026-11-13. 화면 5개(S1~S5)와 예외 경로(E1·E2·E3·E5)를 담은 순서도입니다. 화면 설명과 예외 상세는 `유저플로우_초안_v0.html`을 봅니다.

## 기호

| 기호 | 뜻 |
| --- | --- |
| 둥근 상자 | 시작·끝 |
| 사각 상자 | 화면 하나 (번호 S1~S5) |
| 마름모 | 분기 (예 / 아니오 질문) |
| 실선 화살표 | 정상 진행 |
| 주황 점선 화살표 | 예외·수정 경로 (라벨에 E 번호) |
| 화살표 라벨 | 사용자의 행동 또는 분기 조건 |

**확정과 설계 제안의 구분:** 운영 조건 충돌과 근거 확인은 담당자가 확인하는 단계입니다. 시스템이 자동으로 판별하는 기능은 아직 합의되지 않아 순서도에 넣지 않았습니다.

```mermaid
flowchart TD
  START(["시작 · 기획 시작"]) -->|"조건 입력"| S1["S1 기획 조건 입력<br/>월·계절·국가·기간·예산"]
  S1 --> D1{"필수 조건<br/>입력됨?"}
  D1 -.->|"아니오 · 다시 입력"| S1
  D1 -->|"예 · 숙박형 또는 당일형"| S2["S2 수요 근거 확인<br/>지역·소비·활동 구분"]
  S2 --> D2{"담당자 확인<br/>출처·시점 확인됨?"}
  D2 -->|"예"| S3["S3 코스 검토·수정<br/>중구→동구 기본안 · 스탬프 설정"]
  D2 -.->|"아니오 · E1 근거 부족"| D3{"진행 방식 선택"}
  D3 -.->|"조건 변경"| S1
  D3 -.->|"자료 재검토"| S2
  D3 -.->|"한계 표시 후 진행"| S3
  S3 --> D4{"담당자 확인<br/>운영 조건 충돌?"}
  D4 -.->|"예 · E2 담당자 수정"| S3
  D4 -->|"아니오"| S4["S4 홍보 콘텐츠 검토<br/>방향·문구·번역"]
  S4 --> D5{"코스 수정 필요?"}
  D5 -.->|"예 · E3 S3에서 수정 후 재검토"| S3
  D5 -->|"아니오"| S5["S5 기획안 PDF 저장"]
  S5 --> D6{"저장 성공?"}
  D6 -.->|"아니오 · E5 재시도"| S5
  D6 -->|"예"| END(["완료 · 기획안 PDF"])
  END -.-> FOLLOW["후속 업무<br/>운영 주체 전달 (범위 밖)"]

  classDef term fill:#1e2a4a,stroke:#1e2a4a,color:#ffffff
  classDef dec fill:#fff8e6,stroke:#d98b00,color:#1f2937
  classDef s1 fill:#e8f0fd,stroke:#2f6fdb,stroke-width:2px,color:#1f2937
  classDef s2 fill:#e6f6f4,stroke:#0e9384,stroke-width:2px,color:#1f2937
  classDef s3 fill:#f0ebfb,stroke:#7a4fd0,stroke-width:2px,color:#1f2937
  classDef s4 fill:#fbe9f2,stroke:#c2417f,stroke-width:2px,color:#1f2937
  classDef s5 fill:#f0f5e6,stroke:#557a1a,stroke-width:2px,color:#1f2937
  classDef out fill:#f3f4f6,stroke:#9ca3af,color:#4b5563
  class START,END term
  class D1,D2,D3,D4,D5,D6 dec
  class S1 s1
  class S2 s2
  class S3 s3
  class S4 s4
  class S5 s5
  class FOLLOW out
  linkStyle 2,6,7,8,9,11,14,17 stroke:#e8730c,stroke-width:2px,stroke-dasharray:6 4,color:#9a3f00
  linkStyle 19 stroke:#9ca3af,stroke-dasharray:3 3
```

## 예외 경로 요약

| 번호 | 발생 지점 | 경로 |
| --- | --- | --- |
| E1 | S2 근거 확인 | 조건 변경 → S1 · 자료 재검토 → S2 · 한계 표시 후 진행 → S3 |
| E2 | S3 운영 조건 충돌 | 담당자가 S3에서 수정 |
| E3 | S4 코스 수정 필요 | S3에서 수정한 뒤 S4 재검토 |
| E5 | S5 PDF 저장 실패 | S5에서 재시도 |

**미정 (순서도에 넣지 않음):** 자동 판별과 진행 차단, 저장 제한 조건, 코스 초안 생성 방식, 번역 언어와 범위, 캐릭터·영상 활용 범위, PDF 생성 방식, 운영 주체 전달 방식 (후속 업무).
