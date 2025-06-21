import os
import glob
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 유튜브 업로드를 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """
    인증된 YouTube API 서비스 객체를 생성하여 반환합니다.
    'youtube_uploader/token.json' 파일이 필요합니다.
    """
    # 스크립트 실행 전, google-auth-oauthlib 를 사용하여 token.json을 미리 발급받아야 합니다.
    # 예: python -m google_auth_oauthlib.flow --client_secrets_file=client_secret.json --scope="https://www.googleapis.com/auth/youtube.upload"
    # 위 명령 실행 후 나타나는 URL에 접속하여 인증하고, 받은 코드를 터미널에 붙여넣으면 token.json이 생성됩니다.
    creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description, tags):
    """
    지정된 동영상 파일을 YouTube에 업로드합니다.
    """
    youtube = get_authenticated_service()
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # 'Entertainment' 카테고리
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
    
    print(f"업로드 성공! 영상 ID: {response['id']}")
    print(f"YouTube Studio에서 확인: https://studio.youtube.com/video/{response['id']}/edit")
    return response['id']

if __name__ == '__main__':
    # 오늘 날짜를 "YYYY년 MM월 DD일" 형식으로 구하기
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # 유튜브 영상 제목, 설명, 태그 자동 생성
    title = f"{today} 주식뉴스 | AI가 분석한 오늘의 증시 핵심 포인트 | OU증권 경제뉴스 패러디. 이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."
    
    description = f"""매일 아침 AI가 전하는 재미있는 주식 뉴스!

이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다.

딱딱한 증권방송은 이제 그만! OU증권의 AI가 오늘의 핫한 경제뉴스를 위트 넘치는 밈과 패러디로 재해석해드립니다. 복잡한 주식 시장 소식을 쉽고 재미있게 이해하고, 투자 인사이트까지 얻어가세요!

▶ 이런 분들께 추천:
- 주식 초보자도 쉽게 이해할 수 있는 경제뉴스가 필요한 분
- 재미있게 투자 정보를 얻고 싶은 분
- 매일 아침 간단한 시장 브리핑이 필요한 직장인
- AI가 분석한 시장 트렌드가 궁금한 분

▶ 매일 업데이트되는 콘텐츠:
- 당일 주요 경제/주식 뉴스 패러디
- AI 기반 시장 분석
- 투자자들이 놓치기 쉬운 숨은 포인트
- 밈으로 보는 증시 동향

구독과 좋아요로 매일 아침 재미있는 투자 정보를 받아보세요!

※ 본 콘텐츠는 정보 제공 목적이며, 투자 권유가 아닙니다. 투자 결정은 본인 판단하에 신중히 하시기 바랍니다.

#주식뉴스 #AI증시분석 #경제뉴스 #투자정보 #OU증권 #주식초보 #증시패러디 #경제유머 #투자교육 #시장분석 #주식밈 #AI투자 #매일경제뉴스 #주식방송 #투자유튜브
"""
    
    tags = ["OU증권", "주식", "증시", "패러디", "AI", "주식유머", "투자", "경제뉴스", "밈", "자동생성"]

    # 업로드할 영상 파일 경로 설정
    video_dir = 'parody_video'
    # 'parody_video' 폴더 내의 mp4 파일 목록 가져오기
    video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
    
    if not video_files:
        raise FileNotFoundError(f"'{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")

    # 가장 최근에 수정된 파일을 업로드 대상으로 선택
    latest_video = max(video_files, key=os.path.getmtime)
    video_path = latest_video

    print(f"업로드할 동영상: {video_path}")

    # 동영상 업로드 함수 호출
    upload_video(
        video_path,
        title,
        description,
        tags
    )
