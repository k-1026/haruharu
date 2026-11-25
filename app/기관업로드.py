"""기관 표 업로드: 읽기·숫자 검사·원래 행 추적은 코드가 맡는다. 공식 자료는 수정하지 않는다."""
import base64
import binascii
import csv
import io
import json
import re
import secrets
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

필수열=['출처','기간','지역','대상','항목','값','단위','표본수']
최대파일=1024*1024
최대행=100  # 로컬 MVP의 명시적 한도. 전체 자유 형식 보고서 분석은 별도 범위다.


def _표(이름, rows):
    head=next(rows,[])
    head=[str(v or '').strip() for v in head]
    while head and not head[-1]:head.pop()
    if len(head)>25:raise ValueError('열은 25개 이하로 정리해 주세요.')
    if any(k not in head for k in 필수열) or len(set(head))!=len(head):
        return {'이름':이름,'행수':0,'행':[],'경고':['필수 열이 없거나 열 이름이 중복됩니다: '+', '.join(필수열)]}
    result=[];warnings=[]
    for line,values in enumerate(rows,2):
        if line>최대행+1:raise ValueError(f'시트당 {최대행}행까지 읽습니다. 사용할 표만 남겨 주세요.')
        if not any(v is not None and str(v).strip() for v in values):continue
        row={k:str(v if v is not None else '').strip() for k,v in zip(head,values)}
        if any(len(v)>300 for v in row.values()):raise ValueError('한 칸의 내용은 300자 이내로 정리해 주세요.')
        try:
            n=Decimal(row.get('값',''))
            if not n.is_finite() or n<0 or n>Decimal('1e12') or (n and n.adjusted() < -12):raise InvalidOperation
            if row.get('단위')=='%' and n>100:raise InvalidOperation
            sample=row.get('표본수','')
            if sample and (not sample.isdigit() or int(sample)<1):raise InvalidOperation
        except (InvalidOperation,ValueError):
            warnings.append(f'{line}행: 값·단위·표본수를 확인해야 하므로 제외했습니다.');continue
        if not row.get('항목') or not row.get('단위'):
            warnings.append(f'{line}행: 항목 또는 단위가 없어 제외했습니다.');continue
        for key in ['출처','기간','지역','대상']:
            if not row.get(key):row[key]='미확인';warnings.append(f'{line}행: {key} 미확인. 간접 참고로만 사용합니다.')
        row['값']=format(n,'f');row['원래행']=line
        result.append(row)
    return {'이름':이름,'행수':len(result),'행':result,'경고':list(dict.fromkeys(warnings))}

_구군='중구|동구|서구|남구|북구|수성구|달서구|달성군|군위군'


def _월(text):
    """기간 글자에 적힌 월만 읽는다. 연도만 있거나 모호하면 빈 집합(추측하지 않음)."""
    months=set()
    def add(a,b=None):
        a=int(a);b=int(b) if b else a
        if not (1<=a<=12 and 1<=b<=12):return
        m=a
        while True:
            months.add(m)
            if m==b:break
            m=m%12+1
    for a,b in re.findall(r'(?<!\d)(\d{1,2})\s*월?\s*[~\-–]\s*(\d{1,2})\s*월',text):add(a,b)
    for a,b in re.findall(r'\d{4}\s*[.\-/]\s*(\d{1,2})(?!\d)\s*[~–]\s*(?:\d{4}\s*[.\-/]\s*)?(\d{1,2})(?!\d)',text):add(a,b)
    for a in re.findall(r'(?<!\d)(\d{1,2})\s*월',text):add(a)
    for a in re.findall(r'\d{4}\s*[.\-/]\s*(\d{1,2})(?![\d.\-/])',text):add(a)
    for a in re.findall(r'(?<!\d)\d{4}(0[1-9]|1[0-2])(?!\d)',text):add(a)
    return months


def 행계절(기간):
    """기간 글자에서 계절을 정한다. 계절 이름이나 월이 없으면 빈 집합을 돌려준다."""
    from 흐름 import 계절_월
    seasons=set(re.findall('봄|여름|가을|겨울',기간))
    months=_월(기간)
    seasons.update(k for k,v in 계절_월.items() if months.intersection(v))
    return seasons


def _행번호(lines):
    """[2,3,4,7] → '2~4, 7'"""
    parts=[];start=prev=None
    for n in sorted(lines)+[None]:
        if start is not None and n==prev+1:prev=n;continue
        if start is not None:parts.append(str(start) if start==prev else f'{start}~{prev}')
        start=prev=n
    return ', '.join(parts)


def 조건대조(rows,조건):
    """각 행의 기간·지역을 기획 조건과 대조한다. 돌려주는 값: (적용행, 제외행, 경고)."""
    from 흐름 import 계절_월
    적용=[];제외=[];사유={};계절미상=[];지역미상=[]
    season=조건.get('계절');areas=조건.get('지역') or []
    for row in rows:
        districts=set(re.findall(_구군,row.get('지역','')))
        seasons=행계절(row.get('기간',''))
        reasons=[]
        if districts and not districts.intersection(areas):reasons.append('지역')
        if season and seasons and season not in seasons:reasons.append('계절')
        if reasons:
            why='·'.join(reasons)
            제외.append({**row,'제외이유':f"{why}이 기획 조건과 다름 (기간 '{row.get('기간','')}', 지역 '{row.get('지역','')}')"})
            사유.setdefault(why,[]).append(row['원래행']);continue
        if not seasons:계절미상.append(row['원래행'])
        if not districts:지역미상.append(row['원래행'])
        적용.append(row)
    target=f"{season}({'·'.join(map(str,계절_월.get(season,[])))}월)" if season else '미지정'
    경고=[]
    for why,lines in 사유.items():
        경고.append(f"{why}이 기획 조건(계절 {target}, 지역 {', '.join(areas) or '미지정'})과 달라 "
                   f"{len(lines)}행을 코스 근거에서 제외했습니다 (원래 {_행번호(lines)}행).")
    if 계절미상:
        경고.append(f"계절 확인 불가 {len(계절미상)}행: {_행번호(계절미상)}행. 기간 글자로 계절을 정할 수 없어 제외하지 않고 간접 참고로 둡니다. 기간에 계절이나 월을 적어 주세요.")
    if 지역미상:
        경고.append(f"지역 확인 불가 {len(지역미상)}행: {_행번호(지역미상)}행. 구·군 이름이 없어 제외하지 않고 간접 참고로 둡니다.")
    return 적용,제외,경고


class 보관함:
    def __init__(self,root):self.root=Path(root)

    def 미리보기(self,값):
        name=값.get('파일명');content=값.get('내용')
        if not isinstance(name,str) or len(name)>120 or re.search(r'[\\/:\x00-\x1f]',name):
            raise ValueError('파일 이름을 확인하세요. 경로는 받을 수 없습니다.')
        ext=Path(name).suffix.lower()
        if ext not in ['.csv','.xlsx']:raise ValueError('CSV 또는 XLSX 파일만 올릴 수 있습니다.')
        if not isinstance(content,str) or len(content)>최대파일*4//3+8:raise ValueError('파일은 1MB 이하여야 합니다.')
        try:data=base64.b64decode(content,validate=True)
        except (ValueError,binascii.Error):raise ValueError('파일 내용을 읽지 못했습니다.') from None
        if not data or len(data)>최대파일:raise ValueError('빈 파일이거나 1MB를 넘었습니다.')
        if ext=='.csv':
            try:
                sheets=[_표('CSV',iter(csv.reader(io.StringIO(data.decode('utf-8-sig')))))]
            except (UnicodeError,csv.Error):raise ValueError('CSV는 UTF-8로 저장한 뒤 올려 주세요.') from None
        else:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    if len(z.infolist())>200 or sum(i.file_size for i in z.infolist())>16*1024*1024:
                        raise ValueError('압축을 푼 엑셀 내용이 너무 큽니다.')
                import openpyxl
                book=openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=False,keep_links=False)
                try:
                    if len(book.worksheets)>10:raise ValueError('엑셀 시트는 10개 이하로 정리해 주세요.')
                    sheets=[]
                    for sheet in book:
                        if (sheet.max_column or 0)>25:raise ValueError('시트는 25열 이하로 정리해 주세요.')
                        # 수식은 실행하거나 캐시를 신뢰하지 않는다. 값으로 저장한 표만 받는다.
                        rows=sheet.iter_rows(values_only=True)
                        sheets.append(_표(sheet.title,iter(rows)))
                finally:book.close()
            except ValueError:
                raise
            except Exception:
                raise ValueError('정상적인 XLSX 파일인지 확인하세요.') from None
        if not any(s['행수'] for s in sheets):raise ValueError('읽을 수 있는 데이터가 없습니다. 필수 열과 숫자 값을 확인하세요.')
        ident=secrets.token_hex(16);folder=self.root/ident
        folder.mkdir(parents=True,exist_ok=False)
        (folder/('원본'+ext)).write_bytes(data)
        result={'업로드id':ident,'파일명':name,'시트':sheets,
                '안내':'출처·기간·지역·대상별 원래 수치를 따로 사용합니다. 서로 다른 조사 수치를 합산하지 않습니다. 가상 자료는 실제 조사 근거로 쓰지 않습니다.'}
        (folder/'미리보기.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result

    def 선택(self,ident,sheet,confirmed,조건=None):
        if confirmed is not True:raise ValueError('읽힌 내용과 경고를 확인한 뒤 적용해 주세요.')
        if not isinstance(ident,str) or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('올린 파일을 다시 선택하세요.')
        try:data=json.loads((self.root/ident/'미리보기.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):raise ValueError('업로드 기록이 없습니다. 다시 올려 주세요.') from None
        s=next((s for s in data['시트'] if s['이름']==sheet and s['행수']),None)
        if not s:raise ValueError('읽을 수 있는 시트를 골라 주세요.')
        result={'업로드id':ident,'파일명':data['파일명'],'시트':s['이름'],'행':s['행'],'경고':s['경고'],'확인':True}
        if 조건 is not None:
            # 적용자료.json에는 실제로 코스에 쓸 행만 남기고, 뺀 행과 이유를 함께 보존한다.
            적용,제외,경고=조건대조(s['행'],조건)
            result.update({'행':적용,'제외행':제외,'경고':list(dict.fromkeys(s['경고']+경고)),
                           '대조조건':{'계절':조건.get('계절'),'지역':조건.get('지역')}})
        return result

    def 실행에보존(self,data,folder):
        target=Path(folder)/'기관데이터';target.mkdir(parents=True,exist_ok=True)
        ext=Path(data['파일명']).suffix.lower()
        (target/('원본'+ext)).write_bytes((self.root/data['업로드id']/('원본'+ext)).read_bytes())
        (target/'적용자료.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def 근거합치기(r,data):
    """업로드 행을 독립 근거로 추가. 필수 열·행 번호와 가상/범위 한계를 이어 전달한다."""
    condition=r['조건'];ids=[]
    # 조건 없이 고른 예전 기록도 여기서 한 번 더 걸러 낸다. 이미 걸렀다면 결과가 같다.
    rows,dropped,check=조건대조(data['행'],condition)
    dropped=list(data.get('제외행',[]))+dropped
    for row in dropped:
        r['미확인'].append(f"[미확인: 업로드 제외] 업로드 {row['원래행']}행: 선택 지역·계절과 달라 코스 근거에서 제외")
    for row in rows:
        districts=set(re.findall(_구군,row['지역']))
        seasons=행계절(row['기간'])
        ident=f"R{len(r['근거'])+1}";ids.append(ident)
        fake='가상' in row['출처'] or '가상' in row['대상'] or '가상' in data['파일명']
        limit='담당자 업로드. 다른 조사와 합산·평균하지 않음. '
        limit+='시연용 가상 자료이며 실제 조사 아님.' if fake else '입력된 출처 정보이며 진위·대표성은 별도 확인 필요.'
        if not districts or not seasons:limit+=' 지역·계절이 이번 조건과 직접 일치하는지 미확인.'
        subject=row['대상']+' / n='+str(row.get('표본수') or '미확인')
        r['근거'].append({'ID':ident,'항목':'기관자료','원자료 항목명':row['지역']+' / '+row['항목']+' / '+row.get('세부항목',''),
                         '수치':row['값']+row['단위'],'파일 · 행 위치':f"업로드/{data['파일명']} [{data['시트']}] 행 {row['원래행']}",
                         '출처':row['출처'],'연도':row['기간'],'표본 · 대상':subject,'한계':limit,'경고':'업로드 자료 확인 필요',
                         '업로드':True,'가상자료':fake,'지역':row['지역']})
    warnings=list(dict.fromkeys(list(data['경고'])+check))+['기관 업로드 자료는 원래 대상·기간·지역·단위별로 따로 참고합니다. 출처 진위와 대표성은 확인 전입니다.']
    fake=any('가상' in row['출처'] or '가상' in row['대상'] for row in data['행']+dropped) or '가상' in data['파일명']
    if fake:warnings.append('시연용 가상 자료 포함: 실제 조사 아님. 공식 통계나 실제 일본인 선호로 해석하지 마세요.')
    if not ids:
        warnings.insert(0,'선택한 지역·계절에 맞는 업로드 행이 없어 이번 코스에 적용하지 않았습니다. 선택 조건과 파일의 기간·지역을 확인하세요.')
    for text in warnings:
        if ids:
            r['경고'].append({'경고ID':f"W{len(r['경고'])+1}",'종류':'기관 업로드','문구':text,'적용근거ID':ids})
        else:
            # W 경고는 실제 채택한 R 근거에만 연결한다. 제외된 자료에 임의 R을 붙이지 않는다.
            r['미확인'].append('[미확인: 기관 업로드 미적용] '+text)
    r['선택파일'].append({'파일':'업로드/'+data['파일명'],'선택행수':len(ids)})
    r['기관업로드']={'파일명':data['파일명'],'시트':data['시트'],'적용행수':len(ids),'근거ID':ids,'제외행수':len(dropped),
                   '가상자료':fake,'경고':warnings}
    return r
