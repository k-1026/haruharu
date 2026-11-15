# 대구 체류 기획 도구 밸류체인 v0

- 단계: ① 지역 자원·수요 → ② 상품 기획 → ③ 홍보·채널 → ④ 예약·판매 → ⑤ 현장·사후
- 이해관계자 상세: `stakeholders.md`
- 표기 규칙
  - 상품·활동 흐름: 실선 `-->`
  - 돈 흐름: 굵은 선 `==>` (라벨: 수수료·정산·예산)
  - 데이터 흐름: 점선 `-.->` (라벨: 데이터 이름·보유자)
  - 병목 (B): 노란색 · 기회 (O): 초록색 · 비용 (C): 주황색
- 주의: 이 흐름도는 보조 자료다. 본 맵은 사례 페이지의 HTML 맵을 쓴다.

```mermaid
flowchart LR
  subgraph S1["① 지역 자원·수요"]
    A1["**중구청 관광콘텐츠팀**"]
    A2["외국인 방문객"]
    A3["관광데이터랩"]
  end
  subgraph S2["② 상품 기획"]
    B1["**우리 팀**"]
    B2["중구청 승인"]
  end
  subgraph S3["③ 홍보·채널"]
    C1["**구청 관광콘텐츠팀**"]
    C2["네이버·OTA"]
  end
  subgraph S4["④ 예약·판매"]
    D1["**여행사**"]
    D2["숙박업소"]
  end
  subgraph S5["⑤ 현장·사후"]
    E1["**해설사·안내소**"]
    E2["방문객 후기"]
  end

  A1 --> B1
  B1 --> C1
  C1 --> D1
  D1 --> E1

  A3 -.->|"거주지·관심 데이터 · 관광데이터랩"| B1
  E2 -.->|"재방문 · 비공개"| B1

  A1 ==>|"사업 예산 1,500여만 원"| B1
  D2 ==>|"객실 요금 [U]"| D1
  E1 ==>|"정산 [U]"| A1

  classDef bottleneck fill:#FEF3DC,stroke:#E89B00
  classDef opp fill:#EEF7E2,stroke:#9BD24B
  classDef cost fill:#FCEBE5,stroke:#E8603C
  class C1 bottleneck
  class A2 opp
  class D2 cost
```
