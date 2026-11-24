# 지도 캐릭터 걷기 시연

- 원본: https://github.com/k-1026/haruharu/tree/이예진/캐릭터디자인_예시/캐릭터_걷기_모션
- 2026-11-24 사용자 지정 폴더에서 너구리·족제비의 가방·랜턴 정면/측면/후면 GIF 6개를 내려받았다. 원본 바이트는 수정하지 않았다.
- 로컬 이름 `raccoon`은 너구리, `weasel`은 족제비, `front/side/back`은 정면/측면/후면이다.
- 실제 3D 모델·리깅 파일이 아닌 입체 표현의 움직이는 이미지다. Three.js 지도 위 DOM 이미지로 이동시키며 카메라와 이동 방향에 따라 면을 바꾼다. 원근 회전·관절 편집은 지원하지 않는다.
- 이미지 로딩에 실패할 때만 기본 도형의 임시 입체 캐릭터를 표시한다. 최종 디자인·비율에 대한 팀 승인을 대신하지 않는다.

## 투명 파생 모션 (2026-11-25)

- 사용자 요청으로 `transparent/*.png` 6개를 별도로 만들었다. PNG 확장자의 APNG 애니메이션이며 원본 GIF의 SHA-256·30프레임·프레임별 재생 간격을 `transparent/manifest.json`에 기록했다. 원본 GIF 바이트는 보존한다.
- `app/캐릭터투명화.cs`는 Windows 기본 이미지 디코더와 코드로 가장자리에 연결된 배경 색을 제거한다. 내부의 검은 눈·가방/꼬리 무늬는 바깥 배경과 구분하며 가장자리와 발밑 조명 잔여를 정리한다. AI·외부 API·새 패키지 설치는 없다. 원본 640×360의 모든 프레임/면에서 얻은 공통 경계에 여백을 두어 자르므로 면 전환 때 크기와 기준 위치를 유지한다.
- 파생 파일은 지도용 그림이다. 새 실제 3D 모델·리깅이나 원작 디자인 수정 승인을 뜻하지 않는다. 화면에서는 회색 타원 마스크와 원형 아바타 테두리를 제거하고 투명 실루엣과 작은 그림자만 표시한다.
- PowerShell 7의 재생성 명령(저장소 루트에서 실행):

```powershell
$characterReferences=@((Get-ChildItem -LiteralPath "$PSHOME/ref" -Filter '*.dll').FullName)+@([System.Drawing.Bitmap].Assembly.Location)+@((Get-ChildItem -LiteralPath $PSHOME -Filter 'System.Private.Windows*.dll').FullName)
Add-Type -Path app/캐릭터투명화.cs -ReferencedAssemblies $characterReferences -ErrorAction Stop
[CharacterCutout]::Build((Join-Path (Get-Location) 'app/담당자화면/characters'),(Join-Path (Get-Location) 'app/담당자화면/characters/transparent'))
```

- 시험: C# 자체 합성 이미지 시험은 바깥 배경 제거·내부 검은 눈·몸체·원본 배열 보존을 확인한다. `app/test_캐릭터자산.py`는 6개 원본 해시·GIF/APNG 프레임 간격·APNG 순서/CRC·투명 모서리와 남아 있는 캐릭터 픽셀을 검사한다.
