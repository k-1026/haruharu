// 사람 결정 대상 지적 목록 (bm/redteam_log.md 와 같은 내용)
// 결정 값: "수용" | "수정" | "반려" | "" (빈칸)
window.REVIEW_ITEMS = [
  { id: "I-1", agent: "투자자", target: "⑨ 수익원", summary: "월 수익이 상인회 1곳에 전부 기댐. 방문객 과금 없음", severity: "상" },
  { id: "I-2", agent: "투자자", target: "⑨ 수익 숫자", summary: "5천~1만 원 확인값은 원자료 파일 없음. 1만 원 · 80곳이 가상 데이터와 같은 숫자", severity: "상" },
  { id: "I-3", agent: "투자자", target: "⑧ 비용 · 손익", summary: "비용 금액 전부 미확인. 손익분기 · 투자금 회수 항목 없음", severity: "상" },
  { id: "I-4", agent: "투자자", target: "⑧ 비용 누락", summary: "대면 안내 인력 · 이동, 법적 검토 · 약관 대응, 가림 이미지 보관, AI 호출, 신고 응대 인력이 빠짐", severity: "중" },
  { id: "I-5", agent: "투자자", target: "⑧ · ⑤ 확장 비용", summary: "매대 증가 시 사무국 작업이 선형으로 늘어남. 사람 승인이 병목", severity: "상" },
  { id: "I-6", agent: "투자자", target: "⑥ · ⑨ 데이터 전제", summary: "D5 데이터가 운영 후 생기고 초기 확보 방법 미확인. 데이터 없이 지불 가치 성립 근거 없음", severity: "상" },
  { id: "I-7", agent: "투자자", target: "② 근거", summary: "P1 '직접' 판정의 근거 점수 60이 VOC 미확인 가정값", severity: "중" },
  { id: "I-8", agent: "투자자", target: "전체 · ④ · ⑤ 책임", summary: "확인 · 수정 · 신고 · 비용을 사무국에 몰았고, 사무국이 지불 주체도 됨. 지불 중단 시 운영 전체 정지", severity: "상" },
  { id: "C-1", agent: "고객", target: "① 고객 세그먼트", summary: "'현금 없는 방문객'은 P1 행위자 전체를 못 담음. 카드 소지 구매자, 외국인 동반 방문 빠짐", severity: "중" },
  { id: "C-2", agent: "고객", target: "② · ⑤ 3단계", summary: "'오늘 영업 여부'가 사무국 승인 뒤 게시됨. 승인 기한 · 미승인 표시 방식 미정", severity: "상" },
  { id: "C-3", agent: "고객", target: "② 품절 · ⑤ 입력", summary: "품절은 상인 버튼만으로 확정. 상인이 버튼을 쓸 수 있는지는 추정이고 인터뷰도 없음", severity: "상" },
  { id: "C-4", agent: "고객", target: "③ 채널", summary: "QR은 현장에서만 닿음. P2는 방문 전 탐색에서 생기는 문제. 방문 전 채널 기각 근거가 저작권뿐", severity: "상" },
  { id: "C-5", agent: "고객", target: "② · ③ 대체 수단", summary: "고객의 현재 대체 행동(매대에 직접 묻기, 현금 준비, ATM 등)이 캔버스에 없음", severity: "중" },
  { id: "C-6", agent: "고객", target: "⑨ · ① 지불 주체", summary: "지불자는 상인회인데 실제로는 상인이 자릿세를 냄. 입력 노동을 하는 상인의 가치가 칸 ②에 없음", severity: "상" },
  { id: "C-7", agent: "고객", target: "⑨ 수익 숫자", summary: "설문 응답자 · 표본 · 조사 시점 미기재. 1만 원 상한이 독립 근거가 아님", severity: "상" },
  { id: "C-8", agent: "고객", target: "④ · ⑤ 신고", summary: "방문객이 신고하는 동기 · 절차 · 결과 통보가 없음. 수정 기한 목표 미정", severity: "중" },
  { id: "R-1", agent: "경쟁자", target: "② · ⑥", summary: "결제 · 영업 표시는 지도 앱 등록 정보와 겹쳐 복제가 쉬움. 차별점이 '한 화면 카드'뿐", severity: "상" },
  { id: "R-2", agent: "경쟁자", target: "전체 · ⑥ 진입장벽", summary: "⑥이 '대체 가능'으로 판정됨. 데이터 해자는 수정 쌍 축적에 기대지만 목표 · 확보 방법 미정", severity: "상" },
  { id: "R-3", agent: "경쟁자", target: "⑦ · ⑨", summary: "파트너 · 지불자가 상인회 한 곳. 경쟁자나 상인회 내재화가 먼저 계약하면 수익과 채널이 함께 끊김", severity: "상" },
  { id: "R-4", agent: "경쟁자", target: "⑨ · ⑧", summary: "경쟁 무료화 시 정액 수익 흔들림. 지불 의사 원자료 미확보. 비용 금액 미확인", severity: "상" },
  { id: "R-5", agent: "경쟁자", target: "③ · 전체 대체재", summary: "지도 앱 · 블로그 · SNS · 상인회 공지 · 손글씨 · 직접 묻기가 경쟁 대상으로 안 나옴. 경쟁 · 시장 자료 없음", severity: "상" },
  { id: "R-6", agent: "경쟁자", target: "③ · ⑦", summary: "QR 안내판 부착 공간 · 허가 주체 근거 없음. 지도 앱 약관 미확인으로 채널 선점 판단 불가", severity: "중" },
  { id: "R-7", agent: "경쟁자", target: "전체 차별화", summary: "'결제 정보 없음'의 차별화 근거 자료 없음. VOC 원자료 미독. 원자료는 가상 데이터 표시", severity: "중" }
];
