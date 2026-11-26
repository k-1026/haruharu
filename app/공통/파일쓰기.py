"""임시 파일을 진짜 파일로 바꿔 넣는다.

Windows는 다른 프로그램(진행 화면이 몇 초마다 읽는 서버 등)이 파일을 열고 있으면
교체를 잠깐 거부한다(PermissionError, WinError 5). 그때는 잠깐 기다렸다 다시 시도한다.
"""
import os
import time

대기초 = [0.05, 0.1, 0.2, 0.4, 0.8]  # 모두 합쳐 약 1.5초


def 바꿔쓰기(임시, 대상):
    for 초 in [*대기초, None]:
        try:
            os.replace(임시, 대상)
            return
        except PermissionError:
            if 초 is None:
                raise
            time.sleep(초)
