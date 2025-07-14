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
from common_utils import get_today_kst, get_gsheet

# 환경변수에서 민감 정보 및 설정값을 읽어옴
SHEET_NAME = os.environ.get('SHEET_NAME')
COUPANG_NOTICE = os.environ.get('COUPANG_NOTICE')
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')

# 환경변수 체크
if not SHEET_NAME:
    print("[환경설정오류] SHEET_NAME 환경변수가 필요합니다.")
    sys.exit(1)
if not COUPANG_NOTICE:
    print("[환경설정오류] COUPANG_NOTICE 환경변수가 필요합니다.")
    sys.exit(1)
if not CLAUDE_API_KEY:
    print("[환경설정오류] CLAUDE_API_KEY 환경변수가 필요합니다.")
    sys.exit(1)

# 유튜브 업로드를 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_today_rows_from_sheet():
    sheet = get_gsheet(SHEET_NAME)
    today = get_today_kst().strftime('%Y-%m-%d')
    records = sheet.get_all_records()
    return [row for row in records if str(row.get('date', '')) == today]

def ask_claude_best_row(rows, api_key):
    # 20개 row를 요약해서 클로드에게 가장 임팩트 있는 row index를 추천받음
    prompt = """
아래는 오늘의 패러디 카드뉴스 20개입니다.\n\n"""
    for idx, row in enumerate(rows):
        prompt += f"{idx+1}. parody_title: {row['parody_title']}\n   setup: {row['setup']}\n   punchline: {row['punchline']}\n   humor_lesson: {row['humor_lesson']}\n\n"
    prompt += """
이 중에서 유튜브 제목/설명/태그로 가장 임팩트 있고, SEO에 최적화되고, 독자 반응이 좋을 것 같은 row 1개만 골라줘. 반드시 아래와 같은 JSON으로만 답변해.\n{\n  \"index\": 3,  // 0부터 시작\n  \"reason\": \"이유 간단히\"\n}\n"""
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 256,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data
    )
    text = response.json().get("content", "")
    match = re.search(r'\{[^\}]*\}', text)
    if match:
        meta = match.group(0)
        try:
            return eval(meta)  # 안전하게 하려면 json.loads(meta)
        except:
            return {"index": 0, "reason": "파싱실패-기본값"}
    return {"index": 0, "reason": "파싱실패-기본값"}

def make_youtube_description(parody_title):
    # parody_title에서 대표 키워드 추출 (한글/영문/숫자 단어)
    m = re.search(r"[가-힣A-Za-z0-9]+", parody_title)
    keyword = m.group(0) if m else parody_title
    return f"""{COUPANG_NOTICE}

🌅 출근길 개미들을 위한 90초 증시 브리핑!

💥 오늘의 핫이슈 '{keyword}'를 유머와 함께 쉽게 풀어드려요
🎯 회사에서 써먹을 경제 개그까지 덤으로!

⏰ 매일 아침 7시 업데이트
📱 90초 안에 끝나는 알찬 정보

▶️ 이런 분들께 딱!
• 출근길 지하철에서 볼 재미있는 경제뉴스
• 점심시간 동료들과 나눌 증시 개그  
• 복잡한 뉴스를 쉽게 이해하고 싶은 분
• 매일 아침 투자 동기부여가 필요한 분

💪 오늘도 힘내서 투자하세요!

👍 구독&좋아요는 더 좋은 콘텐츠의 힘!
📢 친구들과 공유해서 함께 부자 되어요!

⚠️ 투자 판단은 본인 책임, 재미로만 봐주세요!

#출근길브리핑 #증시유머 #개미투자자 #경제뉴스 #투자개그 #주식밈 #월급쟁이투자 #아침뉴스 #경제패러디 #AI분석
"""

def extract_tags(row):
    # parody_title, humor_lesson, original_title에서 키워드 추출, 10개 이내, #포함
    text = f"{row['parody_title']} {row['humor_lesson']} {row['original_title']}"
    words = re.findall(r"[가-힣A-Za-z0-9]+", text)
    # 중복 제거, 길이 1 이상, 숫자만 제외
    tags = []
    for w in words:
        if len(w) > 1 and not w.isdigit() and w not in tags:
            tags.append(w)
        if len(tags) >= 10:
            break
    return [f"#{t}" for t in tags]

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
    print("🔍 구글시트에서 오늘의 패러디 데이터 20개를 불러옵니다...")
    rows = get_today_rows_from_sheet()
    if not rows:
        print("오늘 날짜의 데이터가 없습니다.")
        sys.exit(1)
    print(f"총 {len(rows)}개 패러디 데이터 로드 완료.")
    # 클로드에게 가장 임팩트 있는 row index 추천받기
    best = ask_claude_best_row(rows, CLAUDE_API_KEY)
    idx = best['index'] if 'index' in best else 0
    row = rows[idx]
    print(f"🎯 추천 패러디 제목: {row['parody_title']}")
    print(f"(추천 사유: {best.get('reason', '')})")
    # 제목: parody_title + 쿠팡파트너스 문구
    title = str(row['parody_title']) + " | " + COUPANG_NOTICE
    # 설명: 고정 템플릿 + parody_title에서 키워드 추출
    description = make_youtube_description(row['parody_title'])
    # 태그: parody_title, humor_lesson, original_title에서 키워드 추출
    tags = extract_tags(row)
    print(f"📝 생성된 제목: {title}")
    print(f"📝 생성된 설명: {description}")
    print(f"🏷️ 태그: {tags}")
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

    # === 업로드 후 parody_video 폴더 내 mp4 파일 중 타겟파일을 제외한 나머지 삭제 ===
    for f in video_files:
        if f != video_path:
            try:
                os.remove(f)
                print(f"[정리] 업로드 후 파일 삭제: {f}")
            except Exception as e:
                print(f"[경고] 파일 삭제 실패: {f} ({e})")
