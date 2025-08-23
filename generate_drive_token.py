"""
Google Drive API 인증 토큰 생성 스크립트
YouTube 업로더와 동일한 방식으로 Google Drive API 토큰을 생성합니다.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Google Drive API 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/youtube.upload'
]

def generate_drive_token():
    """Google Drive API 인증 토큰을 생성합니다."""
    creds = None
    
    # 기존 토큰 파일 확인
    token_path = 'youtube_uploader/token.json'
    if os.path.exists(token_path):
        print(f"✅ 기존 토큰 파일 발견: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("✅ 기존 토큰이 유효합니다.")
            return True
        except Exception as e:
            print(f"⚠️ 기존 토큰이 유효하지 않습니다: {e}")
    
    # 클라이언트 보안 비밀번호 파일 확인
    client_secrets_path = 'youtube_uploader/client_secrets.json'
    if not os.path.exists(client_secrets_path):
        print(f"❌ 클라이언트 보안 비밀번호 파일을 찾을 수 없습니다: {client_secrets_path}")
        print("\n📋 설정 방법:")
        print("1. Google Cloud Console에서 OAuth 2.0 클라이언트 ID 생성")
        print("2. client_secrets.json 파일을 youtube_uploader/ 폴더에 저장")
        print("3. 이 스크립트를 다시 실행")
        return False
    
    # 토큰이 없거나 만료된 경우 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ 토큰이 갱신되었습니다.")
            except Exception as e:
                print(f"❌ 토큰 갱신 실패: {e}")
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ 새로운 토큰이 생성되었습니다.")
            except Exception as e:
                print(f"❌ 토큰 생성 실패: {e}")
                return False
    
    # 토큰을 파일에 저장
    try:
        os.makedirs('youtube_uploader', exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ 토큰이 저장되었습니다: {token_path}")
        return True
    except Exception as e:
        print(f"❌ 토큰 저장 실패: {e}")
        return False

if __name__ == '__main__':
    print("🔐 Google Drive API 인증 토큰 생성 중...")
    success = generate_drive_token()
    
    if success:
        print("\n🎉 인증 설정이 완료되었습니다!")
        print("이제 step1_ou_stock_parody_collection.py에서 Google Drive 업로드가 가능합니다.")
    else:
        print("\n❌ 인증 설정에 실패했습니다.")
        print("위의 설정 방법을 따라 다시 시도해주세요.")
