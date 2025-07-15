import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# .env 파일에서 환경 변수를 로드
load_dotenv()

def get_gsheet(sheet_id, worksheet_name=None):
    """구글 시트와 연결하여 워크시트 객체를 반환합니다. sheet_id는 구글 시트의 ID, worksheet_name은 탭 이름입니다."""
    
    scope = 'https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive'

    creds = None
    # GitHub Actions Secret에 저장된 환경 변수를 우선적으로 확인
    credentials_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    try:
        if credentials_json_str:
            # GitHub Actions 환경: 환경 변수에서 JSON 내용을 읽어옴
            creds_dict = json.loads(credentials_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # 로컬 환경: 파일에서 직접 읽어옴
            credentials_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'service_account.json'))
            print("[DEBUG] service_account.json 경로:", credentials_path)
            if not os.path.exists(credentials_path):
                 raise FileNotFoundError(f"로컬 실행을 위한 '{credentials_path}' 파일을 찾을 수 없습니다.")
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        
        client = gspread.authorize(creds)  # type: ignore
        if worksheet_name:
            sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        else:
            sheet = client.open_by_key(sheet_id).sheet1
        return sheet

    except FileNotFoundError as e:
        print(e)
        raise
    except Exception as e:
        print(f"구글 시트 연결 중 오류가 발생했습니다. API 활성화, 서비스 계정 키, 시트 공유 설정을 확인해주세요.")
        print(f"원본 오류: {e}")
        raise 

def get_today_kst():
    """현재 한국 시각(시/분/초 포함) 반환"""
    try:
        import pytz
        return datetime.now(pytz.timezone('Asia/Seoul'))
    except ImportError:
        # pytz가 없으면 UTC+9로 계산
        return datetime.utcnow() + timedelta(hours=9) 