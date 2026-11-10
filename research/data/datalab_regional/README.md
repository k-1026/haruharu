# 관광데이터랩 지역별 현황 정리본 (datalab_regional)

- 기준: 외지인(비거주 방문자). 내국인·현지인 파일은 제외
- 대상: 대구광역시 중구, 동구 (+ 기준선 대구광역시 일부)
- 원본: `research/data/raw/` 의 `관광데이터랩_대구광역시중구_…`, `관광데이터랩_대구광역시동구_…` CSV
- 원본 대장(원래 파일명·다운로드 시각): 아직 없음. 만들 예정
- 열 이름 대응과 행 수는 `datalab_consolidated_spec.md` 참고

## 파일별 용도

| 파일 | 무엇 | 페르소나에서 쓰는 곳 |
|---|---|---|
| datalab_visitor_residence.csv | 방문자 거주지 분포 (월간·연간) | 출발 지역(거리) 축, 계절별 출발지 변화 |
| datalab_inflow_origin_destination.csv | 유입 출발지 - 유출 목적지 (연간) | 출발 지역 상세 (근거리·원거리 판단 근거) |
| datalab_inflow_outflow_type.csv | 유입·유출 목적지 유형 (월간·연간) | 목적지 관심사 (음식·숙박·쇼핑 등) |
| datalab_inflow_yoy_change.csv | 전년 동기 대비 유입 증감 (월간) | 계절별 증감, 출발지별 추세 |
| datalab_inflow_period_avg_change.csv | 기간 평균 유입 증감 (연간) | 출발지별 평균 추세 |
| datalab_stay_destination_inflow.csv | 숙박 목적지 유입 지역 (연간) | 숙박 여부 판단 (1박 근거) |
| datalab_spending_industry_outsider.csv | 업종별 관광소비 (월간·연간, 외지인) | 계절별 소비 패턴 (식음료·숙박 비중) |
| datalab_spending_type_outsider.csv | 관광소비 유형 (연간, 외지인) | 소비 구성 |
| datalab_navigation_search.csv | 목적지 유형별 검색량 (월간·연간, 전체) | 계절별 관심 목적지 (외지인 구분 없음) |
| datalab_spot_rankings.csv | 인기관광지(외지인), 중심관광지, 지역맛집(외지인) | 코스에 넣을 장소 후보 |
| datalab_related_spots.csv | 연관 관광지 (연간) | 코스 연결 후보 |
| datalab_paid_spot_visitors.csv | 유료 관광지 입장객 (월간, 전체·외국인) | 계절별 방문 규모, 외국인 비중 |
| datalab_foreign_interest_spots.csv | 외국인 관심 관광지 (연간, 언어별) | 글로벌 손님 코스 후보 |
| datalab_social_mentions.csv | 동반·여행유형 언급량 (월간·연간, SNS) | 동반 유형 참고 (외지인 기준 아님) |
| datalab_social_keywords.csv | 동반·여행유형 키워드 (연간, SNS) | 상품 문구·테마 참고 |
| datalab_age_popular_spots.csv | 세대별 인기관광지 (연간, 전체) | 연령 참고 (외지인 구분 없음) |
| datalab_age_hotplace_growth.csv | 세대별 핫플레이스 (2026.10 스냅샷) | 최신 연령별 핫플레이스 참고 |

## 주의
- 거리 × 동반 교차표는 없음. 거리는 출발지 분포, 동반은 SNS 언급으로 따로 봐야 함
- 외지인 연령별 소비는 없음 (성/연령별 소비는 내국인 기준이라 제외)
- 2022년 상반기는 방역 완화 과정이라 영향 가능 (팀 판단)
- 입장객 수는 잠정치 가능
- 문서 파일: `datalab_regional_collection_plan.md` (수집 계획), `datalab_consolidated_spec.md` (열 명세)
