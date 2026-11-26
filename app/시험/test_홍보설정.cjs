const {test}=require('node:test');
const assert=require('node:assert/strict');
const {재생성설정}=require('../담당자화면/promo.js');

test('같은 코스 재생성은 이전 입력과 디자인 선택을 유지한다',()=>{
  const p={버전:2,기본값:{코스이름:'자동 제목',시작시각:'10:00'},선택지:{홍보물:['SNS','리플릿','포스터']}};
  const ctx={이전버전:2,이전확인:{코스이름:'내 제목',시작시각:'11:00',톤앤매너:'C',홍보물:['포스터']}};
  const before=JSON.stringify({p,ctx});const actual=재생성설정(p,ctx);
  assert.equal(actual.기본값.시작시각,'11:00');assert.equal(actual.기본값.코스이름,'내 제목');
  assert.equal(actual.톤앤매너,'C');assert.deepEqual(actual.홍보물,['포스터']);
  assert.equal(JSON.stringify({p,ctx}),before);
});

test('코스 버전이 바뀌면 새 일정 기본값을 쓰고 디자인 선택만 유지한다',()=>{
  const p={버전:3,기본값:{시작시각:'09:00'},선택지:{홍보물:['SNS','리플릿']}};
  const actual=재생성설정(p,{이전버전:2,이전확인:{시작시각:'11:00',톤앤매너:'B',홍보물:['SNS']}});
  assert.equal(actual.기본값.시작시각,'09:00');assert.equal(actual.톤앤매너,'B');assert.deepEqual(actual.홍보물,['SNS']);
});
