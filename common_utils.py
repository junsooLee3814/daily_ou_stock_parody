import os
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_gsheet(sheet_name):
    """구글 스프레드시트 연결 및 시트 반환"""
    try:
        # 환경 변수에서 구글 서비스 계정 파일 경로 가져오기
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS 환경 변수가 설정되지 않았습니다.")
        
        # 사용할 API 범위 지정
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 인증 정보 생성 (파일 경로 사용)
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        
        # gspread 클라이언트 생성
        gc = gspread.authorize(credentials)
        
        # 스프레드시트 ID 가져오기
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경 변수가 설정되지 않았습니다.")
        
        # 스프레드시트 열기
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # 시트 가져오기 (없으면 생성)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        
        return worksheet
        
    except Exception as e:
        print(f"구글 스프레드시트 연결 실패: {str(e)}")
        raise 