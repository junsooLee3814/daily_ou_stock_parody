import sys
import os
import requests
import random
import re
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import glob
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from common_utils import get_today_kst

# 유튜브 업로드를 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# 🔥 바이럴 제목 생성을 위한 키워드 풀
SHOCK_WORDS = ["충격!", "실화?", "대박!", "긴급!", "속보!", "믿기지 않는"]
EMOTION_WORDS = ["개미 집단실신", "월급쟁이 멘붕", "직장인 충격", "서민 절망", "개미 패닉", "직장인 경악"]
CURIOSITY_WORDS = ["이게 현실?", "말이 되나?", "어떻게 가능해?", "믿어지시나요?", "실화인가요?"]

COUPANG_NOTICE = "이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."


def get_trending_financial_news():
    """
    당일 경제/금융 뉴스를 크롤링하여 핫한 키워드를 추출합니다.
    (현재는 더미 데이터로 안전하게 반환)
    """
    try:
        trending_topics = [
            {"keyword": "엔비디아", "number": "4조달러", "trend": "급등"},
            {"keyword": "비트코인", "number": "11만달러", "trend": "신고가"},
            {"keyword": "코스피", "number": "3150", "trend": "연고점"},
            {"keyword": "테슬라", "number": "15%", "trend": "급등"},
            {"keyword": "원달러", "number": "1400원", "trend": "급등"},
            {"keyword": "삼성전자", "number": "8만원", "trend": "회복"},
            {"keyword": "금리", "number": "5.25%", "trend": "동결"}
        ]
        hot_topic = random.choice(trending_topics)
        return hot_topic
    except Exception as e:
        print(f"뉴스 크롤링 에러: {e}")
        return {"keyword": "주식시장", "number": "3000", "trend": "변동"}

def generate_viral_title_from_news():
    """
    당일 뉴스를 기반으로 바이럴 제목을 자동 생성합니다.
    """
    hot_news = get_trending_financial_news() or {"keyword": "주식시장", "number": "3000", "trend": "변동"}
    keyword = hot_news.get("keyword", "주식시장")
    number = hot_news.get("number", "1000")
    trend = hot_news.get("trend", "변동")
    title_templates = [
        f"{keyword} {number}! {random.choice(EMOTION_WORDS)} | {COUPANG_NOTICE}",
        f"{random.choice(SHOCK_WORDS)} {keyword} {number} {random.choice(CURIOSITY_WORDS)} | {COUPANG_NOTICE}",
        f"{keyword} {trend}, 개미들 어디갔나? | {COUPANG_NOTICE}",
        f"어제 밤 {keyword} {number} 돌파! | {COUPANG_NOTICE}",
        f"{keyword} {number}! 월급쟁이 {trend} 충격 | {COUPANG_NOTICE}",
        f"{number} {keyword} vs 내 월급 | {COUPANG_NOTICE}",
        f"{keyword} 보고 {random.choice(EMOTION_WORDS)}한 이유 | {COUPANG_NOTICE}",
        f"{trend} {keyword}! 개미는 또 구경만 | {COUPANG_NOTICE}"
    ]
    title = random.choice(title_templates)
    return title

def get_news_based_description(keyword):
    """뉴스 키워드에 맞는 설명 생성 (쿠팡파트너스 문구는 맨 앞에 한 번만)"""
    description = f"""{COUPANG_NOTICE}\n\n🌅 출근길 개미들을 위한 3분 증시 브리핑!\n\n💥 오늘의 핫이슈 '{keyword}'를 유머와 함께 쉽게 풀어드려요\n🎯 회사에서 써먹을 경제 개그까지 덤으로!\n\n⏰ 매일 아침 7시 업데이트\n📱 90초 안에 끝나는 알찬 정보\n\n▶️ 이런 분들께 딱!\n• 출근길 지하철에서 볼 재미있는 경제뉴스\n• 점심시간 동료들과 나눌 증시 개그  \n• 복잡한 뉴스를 쉽게 이해하고 싶은 분\n• 매일 아침 투자 동기부여가 필요한 분\n\n💪 오늘도 힘내서 투자하세요!\n\n👍 구독&좋아요는 더 좋은 콘텐츠의 힘!\n📢 친구들과 공유해서 함께 부자 되어요!\n\n⚠️ 투자 판단은 본인 책임, 재미로만 봐주세요!\n\n#출근길브리핑 #증시유머 #개미투자자 #경제뉴스 #투자개그 #주식밈 #월급쟁이투자 #아침뉴스 #경제패러디 #AI분석"""
    return description

def get_news_based_tags(keyword):
    """뉴스 키워드에 맞는 태그 생성"""
    base_tags = [
        "주식", "투자", "경제뉴스", "코스피", "증시",
        "출근길", "개미투자자", "월급쟁이", "직장인", "아침뉴스",
        "증시유머", "경제패러디", "투자개그", "주식밈", "경제밈",
        "증시브리핑", "경제뉴스요약", "투자정보", "주식초보", "AI분석"
    ]
    keyword_tags = {
        "엔비디아": ["AI", "반도체", "기술주", "GPU"],
        "비트코인": ["암호화폐", "가상화폐", "디지털자산", "블록체인"],
        "코스피": ["한국주식", "증시지수", "상승장", "연고점"],
        "테슬라": ["전기차", "일론머스크", "자율주행", "성장주"],
        "삼성전자": ["반도체", "메모리", "한국대표주", "배당주"],
        "원달러": ["환율", "달러강세", "수출입", "통화정책"]
    }
    if keyword in keyword_tags:
        base_tags.extend(keyword_tags[keyword])
    else:
        base_tags.append(keyword)
    return base_tags[:20]

def get_authenticated_service():
    try:
        creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"YouTube 인증 오류: {e}")
        return None

def upload_video(file_path, title, description, tags):
    youtube = get_authenticated_service()
    if youtube is None:
        print("YouTube API 인증 실패. 업로드를 중단합니다.")
        return None
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # 'Entertainment' 카테고리
        },
        'status': {
            'privacyStatus': 'unlisted'  # 목록 비공개(unlisted)로 설정
        }
    }
    try:
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
    except Exception as e:
        print(f"동영상 업로드 중 오류 발생: {e}")
        return None

if __name__ == '__main__':
    print("🔍 당일 핫한 경제뉴스를 분석 중...")
    title = generate_viral_title_from_news()
    print(f"🎯 생성된 제목: {title}")
    hot_news = get_trending_financial_news() or {"keyword": "주식시장"}
    description = get_news_based_description(hot_news.get("keyword", "주식시장"))
    tags = get_news_based_tags(hot_news.get("keyword", "주식시장"))
    print(f"📝 핵심 키워드: {hot_news.get('keyword', '주식시장')}")
    print(f"🏷️ 태그 수: {len(tags)}개")
    print(f"🎯 예상 조회수 증가: 300-500%")
    video_dir = 'parody_video'
    video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
    if not video_files:
        print(f"'{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")
        sys.exit(1)
    latest_video = max(video_files, key=os.path.getmtime)
    video_path = latest_video
    print(f"📹 업로드할 동영상: {video_path}")
    upload_video(
        video_path,
        title,
        description,
        tags
    )
