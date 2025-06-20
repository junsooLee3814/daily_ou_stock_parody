import os
import glob
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    # youtube_uploader 폴더 내에 token.json 파일이 있어야 합니다.
    # 스크립트 실행 전, google-auth-oauthlib 를 사용하여 token.json을 미리 발급받아야 합니다.
    # 예: python -m google_auth_oauthlib.flow --client_secrets_file=client_secret.json --scope="https://www.googleapis.com/auth/youtube.upload"
    # 위 명령 실행 후 나타나는 URL에 접속하여 인증하고, 받은 코드를 터미널에 붙여넣으면 token.json이 생성됩니다.
    creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description, tags):
    youtube = get_authenticated_service()
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # Entertainment 카테고리
        },
        'status': {
            'privacyStatus': 'private'  # 'private', 'public', 'unlisted' 중 선택
        }
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    print("동영상 업로드를 시작합니다...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"업로드 진행률: {int(status.progress() * 100)}%")
    
    print('업로드 성공! 영상 ID:', response['id'])
    print(f"YouTube Studio에서 확인: https://studio.youtube.com/video/{response['id']}/edit")
    return response['id']

if __name__ == '__main__':
    # 오늘 날짜 구하기
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # 제목, 설명, 태그 자동 생성 (OU 증시 패러디용)
    title = f"[OU증권] {today} AI가 만든 오늘의 증시 패러디"
    description = f"""AI가 매일 아침 전해드리는 가장 신박한 증시 패러디!
오늘의 주요 경제 뉴스를 AI가 위트있는 밈과 패러디로 재해석해 드립니다.
딱딱한 증권 방송은 이제 그만! OU증권과 함께 웃음 가득한 투자 인사이트를 얻어가세요.

#OU증권 #주식 #증시 #패러디 #AI #주식유머 #투자 #경제뉴스 #밈 #자동화"""
    tags = ["OU증권", "주식", "증시", "패러디", "AI", "주식유머", "투자", "경제뉴스", "밈", "자동생성"]

    # 가장 최근에 생성된 패러디 영상 파일 찾기
    video_dir = 'parody_video'
    # parody_video 폴더 내의 mp4 파일 목록 가져오기
    video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
    
    if not video_files:
        raise FileNotFoundError(f"'{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")

    # 가장 최근에 수정된 파일 찾기
    latest_video = max(video_files, key=os.path.getmtime)
    video_path = latest_video

    print(f"업로드할 동영상: {video_path}")

    upload_video(
        video_path,
        title,
        description,
        tags
    )
