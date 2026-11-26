const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const html=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면/index.html'),'utf8');
test('운영·검사·AI 실행은 접힌 관리자 상세 안에 있으며 코스는 기본 화면에 있음',()=>{
  const admin=html.slice(html.indexOf('<details id="adminDetails"'));
  assert.ok(html.indexOf('id="reviewPeriods"')<html.indexOf('id="adminDetails"'));
  for(const id of ['reviewOperations','courseStart','courseHistory','panel'])assert.ok(admin.includes(`id="${id}"`),id);
  assert.ok(!/^<details id="adminDetails"[^>]*\bopen\b/.test(admin));
});
test('관리자로 옮긴 입력은 원래 폼과 연결되고 기획자 저장은 AI 동작과 구분',()=>{
  assert.match(html, /id="courseSave"[^>]*form="courseForm"/);
  assert.match(html, /name="방문시작일"[^>]*form="reviewForm"/);
  assert.match(html,/id="reviewSave"[^>]*>수정한 코스 저장/);
});
