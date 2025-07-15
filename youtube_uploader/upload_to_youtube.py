import os
import glob
import random
import gspread
import sys
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time
import httplib2
from googleapiclient.errors import HttpError

# 상위 폴더의 common_utils 모듈을 import하기 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from common_utils import get_gspread_client  # 삭제
from common_utils import get_gsheet  # 추가

# 유튜브 업로드를 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# 기존 SEO 관련 상수 및 함수 모두 삭제

COUPANG_NOTICE = "이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."

# 오늘의 parody_title을 구글 시트에서 가져오는 함수만 남김

def get_today_parody_title_and_keyword():
    """구글 시트에서 C열 2행(parody_title)과 B열 2행(original_title)을 간단하게 반환."""
    SHEET_ID = '1tEmq2HIEg9CWyrU8vtoM9mo3CW9XWfa4iWasOiK4Z2A'
    SHEET_NAME = 'today_stock_parody'
    worksheet = get_gsheet(SHEET_ID, SHEET_NAME)
    all_values = worksheet.get_all_values()
    parody_title = all_values[1][2]
    keyword = all_values[1][1]
    return parody_title, keyword

# 태그 고정 리스트
FIXED_TAGS = [
    'AI증권뉴스패러디','증권뉴스분석','개인투자자','경제공부','경제뉴스','글로벌뉴스','금리뉴스','금융교육','금융시장','기술뉴스','뉴스분석','뉴스브리핑','뉴스요약','뉴스카드','미국뉴스','반도체뉴스','부동산뉴스','비즈니스뉴스','시장동향','시장예측','아시아뉴스','암호화폐','에너지뉴스','오늘의뉴스','유럽뉴스','인플레이션','일본뉴스','정책뉴스','주식시장','중국뉴스','중앙은행','증시분석','투자뉴스','투자정보','트렌드분석','환율뉴스'
]

# 설명 고정 포맷 함수

def get_fixed_description(keyword):
    return f"""{COUPANG_NOTICE}\n\n🌅 출근길 개미들을 위한 90초 증시 브리핑!\n\n💥 오늘의 핫이슈 '{keyword}'를 유머와 함께 쉽게 풀어드려요\n🎯 회사에서 써먹을 경제 개그까지 덤으로!\n\n⏰ 매일 아침 7시 업데이트\n📱 90초 안에 끝나는 알찬 정보\n\n▶️ 이런 분들께 딱!\n• 출근길 지하철에서 볼 재미있는 경제뉴스\n• 점심시간 동료들과 나눌 증시 개그  \n• 복잡한 뉴스를 쉽게 이해하고 싶은 분\n• 매일 아침 투자 동기부여가 필요한 분\n\n💪 오늘도 힘내서 투자하세요!\n\n👍 구독&좋아요는 더 좋은 콘텐츠의 힘!\n📢 친구들과 공유해서 함께 부자 되어요!\n\n⚠️ 투자 판단은 본인 책임, 재미로만 봐주세요!\n\n#출근길브리핑 #증시유머 #개미투자자 #경제뉴스 #투자개그 #주식밈 #월급쟁이투자 #아침뉴스 #경제패러디 #AI분석\n"""

def get_authenticated_service():
    """인증된 YouTube API 서비스 객체를 생성하여 반환합니다."""
    try:
        creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"YouTube 인증 오류: {e}")
        return None

def upload_video(file_path, title, description, tags, max_retries=3):
    """지정된 동영상 파일을 YouTube에 업로드합니다."""
    # 네트워크 타임아웃 명시 (삭제)
    # http = httplib2.Http(timeout=60)
    youtube = get_authenticated_service()
    if youtube is None:
        print("YouTube API 인증 실패. 업로드를 중단합니다.")
        return None

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24',
            'defaultLanguage': 'ko',
            'defaultAudioLanguage': 'ko'
        },
        'status': {
            'privacyStatus': 'private',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(
        file_path,
        chunksize=1024*1024,  # 1MB
        resumable=True,
        mimetype='video/mp4'
    )

    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    retry = 0
    response = None
    error = None
    print(f"🚀 증권권뉴스 패러디 업로드를 시작합니다... (파일: {file_path})")
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"업로드 진행률: {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"서버 오류: {e.resp.status}, 재시도 중..."
            else:
                print(f"API 오류: {e}\n응답 내용: {e.content}")
                break
        except Exception as e:
            error = f"예외 발생: {e}"
        if error:
            retry += 1
            if retry > max_retries:
                print(f"최대 재시도 횟수 초과. 업로드 실패: {error}")
                return None
            sleep_time = 2 ** retry
            print(f"{error} {sleep_time}초 후 재시도...")
            time.sleep(sleep_time)
            error = None
        else:
            retry = 0
    if response:
        print(f"✅ 업로드 성공! 영상 ID: {response['id']}")
        print(f"YouTube API 응답: {response}")
        return response['id']
    else:
        print("❌ 업로드 실패: 응답 없음")
        return None

if __name__ == '__main__':
    print("🔍 오늘의 증권뉴스 패러디 SEO 최적화 중...")
    
    # 오늘의 parody_title과 키워드 가져오기
    parody_title, keyword = get_today_parody_title_and_keyword()
    if not parody_title:
        print("❌ 오늘의 parody_title을 찾을 수 없습니다.")
        exit(1)
    
    # 제목 생성
    title = f"{parody_title} | {COUPANG_NOTICE}"
    print(f"🎯 생성된 제목: {title}")
    
    # 설명 생성
    description = get_fixed_description(keyword)
    print(f"📝 설명 길이: {len(description)}자")
    
    # 태그 고정
    tags = FIXED_TAGS
    print(f"🏷️ 태그 수: {len(tags)}개")
    print(f"🎯 타겟: 출근길 개미, 경제/주식 관심자")
    print(f"⚖️ 쿠팡파트너스 의무사항 준수 완료")
    
    # 업로드할 영상 파일 찾기
    video_dir = 'parody_video'
    video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
    
    if not video_files:
        print(f"❌ '{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")
        exit(1)
    
    # 가장 최근 파일 선택
    latest_video = max(video_files, key=os.path.getmtime)
    print(f"📹 업로드할 동영상: {latest_video}")
    
    # 업로드 실행
    video_id = upload_video(
        latest_video,
        title,
        description,
        tags
    )
    
    if video_id:
        print(f"\n🎉 SEO 최적화된 증권권뉴스 패러디 업로드 완료!")
        print(f"📺 영상 URL: https://youtu.be/{video_id}")
        print(f"🔍 검색 최적화: 증권권뉴스, 30대, 40대, 50대")
        print(f"⚖️ 쿠팡파트너스 의무사항 완료")
        # 업로드한 파일(latest_video)은 남기고, 나머지 .mp4 파일 삭제
        for f in glob.glob(os.path.join(video_dir, '*.mp4')):
            if os.path.abspath(f) != os.path.abspath(latest_video):
                try:
                    os.remove(f)
                    print(f"🗑️ 추가 파일 삭제 완료: {f}")
                except Exception as e:
                    print(f"⚠️ 추가 파일 삭제 실패: {f} ({e})")
        # 업로드 후 YouTube API로 영상 정보 확인 (삭제)
        # try:
        #     youtube = get_authenticated_service()
        #     if youtube is not None:
        #         video_info = youtube.videos().list(part="status,snippet,contentDetails", id=video_id).execute()
        #         print("\n[업로드 후 YouTube 영상 정보]")
        #         print(video_info)
        #     else:
        #         print("[업로드 후 영상 정보 조회 실패]: YouTube 인증 실패")
        # except Exception as e:
        #     print(f"[업로드 후 영상 정보 조회 실패]: {e}")
    else:
        print("❌ 업로드에 실패했습니다.")
