# 한국관광데이터랩 지역별 현황 정리본 명세

- 작성일: 2026-11-10
- 원본: `research/data/raw/` 관광데이터랩 CSV (원본 수정 없음). 정리본은 같은 지표끼리 합친 파일
- 기준: 외지인(비거주 방문자). 현지인·내국인 파일은 제외. 원본 내용은 바꾸지 않고 행만 합쳤음
- 정리본 열 이름은 원본 한글 열을 영문으로 옮긴 것. 공통 열: region(중구/동구), period(기간), source_file(원본 파일명)
- 이 문서는 공용 `data_spec.md`를 건드리지 않는 별도 명세임. 공용 명세 반영은 팀 공지 후 담당자가 결정

## 파일 목록

| 정리본 파일 | 지표 | 구분 기준 | 행 수 | 원본 파일 수 | 비고 |
|---|---|---|---|---|---|
| datalab_age_hotplace_growth.csv | 세대별 핫플레이스 (성장율) | 전체(연령별) | 114 | 12 | 2026.10 스냅샷 1회. 과거 이력 없음 |
| datalab_age_popular_spots.csv | 세대별 인기관광지 | 전체(연령별) | 360 | 12 | age_group 기준. 세대 필터 있음 |
| datalab_foreign_interest_spots.csv | 외국인 관심 관광지 (영어권·일본어·중간체·중번체) | 외국인 | 145 | 8 | language_group 기준. 연간만 |
| datalab_inflow_origin_destination.csv | 유입 출발지 - 유출 목적지 분포 | 전체 | 80 | 2 | 연간만. 지역 선택 기준 구분 |
| datalab_inflow_outflow_type.csv | 유입/유출 목적지 유형 분포 | 전체 | 464 | 14 | direction으로 유입·유출 구분 |
| datalab_inflow_period_avg_change.csv | 조회기간 평균 유입 증감 (연간) | 전체 | 51 | 6 | origin_region = 비교 출발지. 2022~2025 평균 |
| datalab_inflow_yoy_change.csv | 전년 동기 대비 유입 증감 (월간) | 전체 | 248 | 30 | origin_region = 비교 출발지. 조회기간별 전년 대비 |
| datalab_navigation_search.csv | 내비게이션 목적지 유형별 검색량 | 전체(구분 없음) | 1,157 | 12 | 외지인 선택지 없음. 내국인 포함 전체 검색량으로 해석 |
| datalab_paid_spot_visitors.csv | 주요 유료관광지점 입장객 수 | 전체 / 외국인 | 780 | 18 | visitor_basis로 구분. 잠정치 포함 가능. 동구 외국인 파일 미확인 |
| datalab_related_spots.csv | 연관 관광지 | 전체 | 100 | 2 | 연간만. 마이데이터랩 미저장 데이터 |
| datalab_social_keywords.csv | 동반유형 키워드 + 여행유형/트렌드 키워드 | SNS 전체 | 1,553 | 4 | 연간 2022~2025만 있음. category_list로 구분 |
| datalab_social_mentions.csv | 동반유형 언급량 + 여행유형/트렌드 언급량 | SNS 전체 | 2,940 | 24 | category_list로 두 목록 구분 |
| datalab_spending_industry_outsider.csv | 업종별 관광소비 추이 | 외지인 | 950 | 12 | 소비액 천원 단위, 월간/연간 |
| datalab_spending_type_outsider.csv | 관광소비 유형 (업종 분류별 비율) | 외지인 | 34 | 2 | 연간 2022~2025만 있음 |
| datalab_spot_rankings.csv | 인기관광지(외지인) + 중심관광지 + 지역맛집(외지인) | 외지인 | 1,600 | 16 | spot_list로 구분. 중심관광지·맛집은 연간만 |
| datalab_stay_destination_inflow.csv | 숙박 목적지 유입 지역 분포 | 숙박 방문자 | 497 | 2 | 연간만 |
| datalab_visitor_residence.csv | 방문자 거주지 분포 | 외지인 | 3,058 | 12 | 시군구 단위(기초지자체) 비율. 광역 값은 합산이라 참고용 |

## 열 구성

### datalab_age_hotplace_growth.csv

- 열: `region`, `period`, `rank`, `base_month`, `sido_name`, `sigungu_name`, `spot_id`, `spot_name`, `spot_type`, `age_group`, `growth_rate`, `source_file`

### datalab_age_popular_spots.csv

- 열: `region`, `period`, `rank`, `spot_id`, `spot_name`, `spot_type`, `age_group`, `ratio_pct`, `source_file`

### datalab_foreign_interest_spots.csv

- 열: `region`, `period`, `language_group`, `language`, `spot_name`, `spot_type`, `source_file`

### datalab_inflow_origin_destination.csv

- 열: `region`, `period`, `inflow_region`, `outflow_region`, `flow_ratio`, `flow_direction_code`, `source_file`

### datalab_inflow_outflow_type.csv

- 열: `region`, `period`, `direction`, `type_major`, `type_minor`, `major_ratio_pct`, `minor_ratio_pct`, `source_file`

### datalab_inflow_period_avg_change.csv

- 열: `region`, `period`, `origin_region`, `industry_minor`, `search_count`, `avg_search_change_pct`, `total_search_count`, `avg_total_search_change_pct`, `source_file`

### datalab_inflow_yoy_change.csv

- 열: `region`, `period`, `origin_region`, `industry_minor`, `search_count`, `yoy_prev_search_count`, `yoy_search_change_pct`, `total_search_count`, `yoy_prev_total_search_count`, `yoy_total_search_change_pct`, `source_file`

### datalab_navigation_search.csv

- 열: `region`, `period`, `base_month`, `destination_type`, `search_count`, `source_file`

### datalab_paid_spot_visitors.csv

- 열: `region`, `period`, `visitor_basis`, `rank`, `sido_name`, `sigungu_name`, `spot_name`, `base_month`, `visitors`, `visitors_total`, `source_file`

### datalab_related_spots.csv

- 열: `region`, `period`, `rank`, `center_spot_id`, `center_spot_name`, `center_sido`, `center_sigungu`, `center_category`, `related_spot_id`, `related_spot_name`, `related_sido`, `related_sigungu`, `spot_type`, `source_file`

### datalab_social_keywords.csv

- 열: `region`, `period`, `category_list`, `rank`, `category`, `keyword`, `mention_count`, `source_file`

### datalab_social_mentions.csv

- 열: `region`, `period`, `category_list`, `base_month`, `companion_type`, `mention_count`, `travel_trend_type`, `source_file`

### datalab_spending_industry_outsider.csv

- 열: `region`, `period`, `base_month`, `industry_major`, `spending_thousand_krw`, `source_file`

### datalab_spending_type_outsider.csv

- 열: `region`, `period`, `industry_major`, `industry_minor`, `industry_major_ratio_pct`, `industry_minor_ratio_pct`, `source_file`

### datalab_spot_rankings.csv

- 열: `region`, `period`, `spot_list`, `rank`, `spot_id`, `spot_name`, `category`, `source_file`

### datalab_stay_destination_inflow.csv

- 열: `region`, `period`, `sido_name`, `sigungu_name`, `sigungu_visitor_ratio_pct`, `source_file`

### datalab_visitor_residence.csv

- 열: `region`, `period`, `residence_name`, `ratio_pct`, `source_file`

## 확인 필요 · 한계

- 동구 주요 유료관광지점 입장객의 **외국인** 파일: 원본이 없어 동구 외국인 값은 비어 있음. 확인 필요
- 외지인 선택지가 없어 내국인 기준으로만 나오는 차트: 성/연령별 관광소비, 내국인 관심 관광지는 이번 정리본에서 제외함
- 내비게이션 목적지 검색량은 외지인 선택지가 없어 전체 기준임
- 기간: 2022~2026.09 월간 블록 + 2022~2025 연간. 2026은 1~9월만 있음
- 2022년 상반기는 코로나 방역 완화 과정이라 영향이 남았을 수 있음 (팀 판단)
- 입장객 수는 잠정치일 수 있음. 지자체 미입력 월은 0으로 나올 수 있음
- 핫플레이스는 2026.10 스냅샷 한 번뿐이라 과거 추세 분석 불가
- 방문자 수는 날짜별 중복 집계, 숙박·체류는 월 1명 집계. 총량 대신 추세 분석용
- 기초지자체 기준 값 중심. 광역 값은 합산이라 참고용
- 중구 세대별 인기관광지·핫플레이스 원본은 현재 작업 폴더에서 삭제된 상태이며, 정리본 생성은 커밋된 파일(HEAD)에서 읽음
