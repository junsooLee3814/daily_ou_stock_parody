import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description, tags):
    youtube = get_authenticated_service()
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # People & Blogs 카테고리 (명언/노트에 적합)
        },
        'status': {
            'privacyStatus': 'private'
        }
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    response = request.execute()
    print('업로드 성공! 영상 ID:', response['id'])

if __name__ == '__main__':
    # 오늘 날짜 구하기
    today = datetime.now().strftime('%Y%m%d')

    # 제목, 설명, 태그 자동 생성 (명언/노트용)
    title = f"[오늘의 한줄노트] {today} 세대별 명언/노트 카드영상"
    description = "오늘의 세대별 명언/노트 카드 영상을 만나보세요. AI가 자동으로 요약/제작합니다."
    tags = ["명언", "한줄노트", "AI명언", "세대별명언", "동기부여", "힐링"]

    # 동영상 파일 경로 (명언 영상 워크플로우의 최종 파일)
    video_path = os.path.join(
        "quote_video", "00combine", "merged_quotes_bgm.mp4"
    )

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"업로드할 동영상 파일이 없습니다: {video_path}")

    upload_video(
        video_path,
        title,
        description,
        tags
    )
