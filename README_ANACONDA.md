# 아나콘다 환경에서 파이썬 사용법

## 🎯 개요
이 프로젝트는 아나콘다 환경에서 파이썬을 사용하여 주식 뉴스 패러디를 생성하는 프로그램입니다.

## 📋 설치된 환경
- **아나콘다 버전**: 25.5.1
- **파이썬 버전**: 3.13.5
- **설치 경로**: `C:\Users\juncp\anaconda3\`

## 🚀 실행 방법

### 방법 1: 배치 파일 사용 (권장)
1. `run_with_anaconda.bat` 파일을 더블클릭
2. 실행할 스크립트 번호 선택 (1-4)
3. 자동으로 아나콘다 파이썬으로 실행

### 방법 2: 직접 명령어 실행
```cmd
C:\Users\juncp\anaconda3\python.exe step1_ou_stock_parody_collection.py
```

### 방법 3: 간단한 배치 파일 사용
```cmd
anaconda_python.bat step1_ou_stock_parody_collection.py
```

## 📁 프로젝트 구조
```
50_ou_stock_parady/
├── step1_ou_stock_parody_collection.py  # 뉴스 수집 및 패러디 생성
├── step2_ou_stock_parody_card.py        # 패러디 카드 생성
├── step3_ou_stock_parody_video.py       # 패러디 비디오 생성
├── step4_ou_stock_parody_final.py       # 최종 통합 실행
├── run_with_anaconda.bat                # 메인 실행 배치 파일
├── anaconda_python.bat                  # 간단한 파이썬 실행기
├── requirements.txt                     # 필요한 패키지 목록
└── README_ANACONDA.md                   # 이 파일
```

## 📦 설치된 패키지
- `anthropic` - Claude AI API
- `gspread` - 구글 시트 연동
- `pandas` - 데이터 처리
- `Pillow` - 이미지 처리
- `python-dotenv` - 환경변수 관리
- `feedparser` - RSS 피드 파싱
- `google-api-python-client` - 구글 API 클라이언트
- 기타 필요한 패키지들

## ⚙️ 환경 설정
프로젝트 실행을 위해 다음 파일들이 필요합니다:
- `.env` 파일 (API 키 설정)
- `service_account.json` (구글 서비스 계정)
- `asset/rawdata.txt` (설정 파일)

## 🔧 문제 해결

### 아나콘다가 인식되지 않는 경우
```cmd
C:\Users\juncp\anaconda3\Scripts\conda.exe init powershell
```
실행 후 PowerShell을 재시작하세요.

### 패키지 설치 오류 시
```cmd
C:\Users\juncp\anaconda3\Scripts\pip.exe install --upgrade pip
C:\Users\juncp\anaconda3\Scripts\pip.exe install -r requirements.txt
```

### 파이썬 경로 확인
```cmd
C:\Users\juncp\anaconda3\python.exe --version
```

## 📝 사용 예시

### 1단계: 뉴스 수집 및 패러디 생성
```cmd
run_with_anaconda.bat
# 1번 선택
```

### 2단계: 패러디 카드 생성
```cmd
run_with_anaconda.bat
# 2번 선택
```

### 3단계: 패러디 비디오 생성
```cmd
run_with_anaconda.bat
# 3번 선택
```

### 4단계: 전체 통합 실행
```cmd
run_with_anaconda.bat
# 4번 선택
```

## 🎉 완료!
이제 아나콘다 환경에서 파이썬을 사용하여 주식 뉴스 패러디 생성 프로그램을 실행할 수 있습니다!




