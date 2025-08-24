import os
import feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic
from anthropic._exceptions import OverloadedError, RateLimitError, APIError
from dotenv import load_dotenv
from common_utils import get_gsheet, get_today_kst
import json
import re
from pathlib import Path
import time
from zoneinfo import ZoneInfo
from anthropic.types import MessageParam
import csv
import glob
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# .env 파일의 절대 경로를 지정하여 로드
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

# Claude AI API 키
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")

# 한국 시간대 정의
KST = ZoneInfo("Asia/Seoul")

def parse_rawdata(file_path='asset/rawdata.txt'):
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_key = None
            values = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('[') and line.endswith(']'):
                    if current_key and values:
                        config[current_key] = values[0] if len(values) == 1 else values
                    current_key = line[1:-1]
                    values = []
                elif current_key:
                    values.append(line)
            if current_key and values:
                config[current_key] = values[0] if len(values) == 1 else values
    except FileNotFoundError:
        print(f"설정 파일({file_path})을 찾을 수 없습니다. 기본값으로 진행합니다.")
    return config

# 구글 시트 설정
SHEET_NAME = 'today_stock_parody'
SHEET_ID = os.getenv('GSHEET_ID')
if not SHEET_ID:
    raise ValueError("GSHEET_ID 환경 변수가 설정되지 않았습니다.")

def fetch_news(rss_url, days=7, min_news=20):
    """RSS 피드에서 최근 days(기본 7일) 내 뉴스를 가져오고, published_parsed가 없으면 published/updated 등 다른 필드도 활용. 뉴스가 없으면 날짜 필터 없이 전체 수집."""
    feed = feedparser.parse(rss_url)
    news_list = []
    today = get_today_kst().astimezone(KST).date()
    start_date = today - timedelta(days=days-1)
    print(f"[디버그] feed.entries 개수: {len(feed.entries)}")
    filtered_count = 0
    for entry in feed.entries:
        published_date = None
        # published_parsed 우선, 없으면 published/updated 등에서 날짜 추출
        if hasattr(entry, 'published_parsed') and isinstance(entry.published_parsed, time.struct_time):
            published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=KST)
            published_date = published_dt.date()
        elif hasattr(entry, 'published') and isinstance(entry.published, str):
            try:
                published_dt = datetime.strptime(entry.published[:10], '%Y-%m-%d')
                published_date = published_dt.date()
            except Exception:
                published_date = None
        elif hasattr(entry, 'updated_parsed') and isinstance(entry.updated_parsed, time.struct_time):
            published_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=KST)
            published_date = published_dt.date()
        # 디버깅: 실제 날짜 값 출력
        print(f"[디버그] published_date: {published_date}, start_date: {start_date}, today: {today}")
        if published_date and (start_date <= published_date <= today):
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else ''
            published = published_date.strftime('%Y-%m-%d') if published_date else ''
            link = entry.link if hasattr(entry, 'link') else ''
            news_item = {
                'title': title,
                'summary': summary,
                'published': published,
                'link': link
            }
            news_list.append(news_item)
        else:
            filtered_count += 1
    print(f"[디버그] 날짜 필터 통과 뉴스: {len(news_list)}, 필터링된 뉴스: {filtered_count}")
    # 만약 뉴스가 너무 적으면 날짜 필터 없이 전체 수집
    if len(news_list) < min_news:
        print("[경고] 날짜 필터로 충분한 뉴스를 수집하지 못했습니다. 날짜 필터 없이 전체 수집을 시도합니다.")
        news_list = []
        for entry in feed.entries:
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else ''
            published = ''
            if hasattr(entry, 'published_parsed') and isinstance(entry.published_parsed, time.struct_time):
                published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=KST)
                published = published_dt.strftime('%Y-%m-%d')
            elif hasattr(entry, 'published') and isinstance(entry.published, str):
                published = entry.published[:10]
            link = entry.link if hasattr(entry, 'link') else ''
            news_item = {
                'title': title,
                'summary': summary,
                'published': published,
                'link': link
            }
            news_list.append(news_item)
        print(f"[디버그] 날짜 무시 전체 수집 뉴스: {len(news_list)}")
    return news_list

def rank_news_by_importance_with_claude(news_list):
    """Claude AI를 사용하여 뉴스 목록을 중요도에 따라 순위 매기기"""
    client = Anthropic(api_key=CLAUDE_API_KEY)

    formatted_news = ""
    for i, news in enumerate(news_list):
        formatted_news += f"ID: {i}\n제목: {news['title']}\n\n"

    prompt = f"""
당신은 대한민국 최고의 금융 뉴스 큐레이터입니다.
다음은 오늘과 어제 수집된 주식/증권 관련 뉴스 전체 목록입니다.
이 중에서 '독자들이 많이 읽을 수 있고, 관심을 가질 만한 뉴스'를 20개 골라, 가장 중요한 순서대로 ID만 쉼표로 구분해 출력하세요.

## 🌟 중요도 판단 기준 (아래 기준 + 대중적 관심도/화제성/바이럴 가능성까지 고려)

### 1. 시장 전체에 미치는 영향 (거시경제, 정책)
- 통화정책(한국은행, Fed 금리, 양적완화/긴축)
- 거시경제 지표(환율 급변동, 유가, 물가지수)
- 정부 정책/규제(세법 개정, 부동산 정책, 산업 규제)

### 2. 특정 산업 및 기업에 미치는 영향
- 반도체/AI/자동차/2차전지/바이오/플랫폼/IT 등 핵심 산업 동향
- 주요 기업 실적, 신제품, 이슈

### 3. 투자자/대중 관심도
- 외국인/기관 동향, 대규모 매수/매도
- 사회적 이슈, 밈, 화제성, 대중적 궁금증

## 📰 뉴스 목록
{formatted_news}

## 💻 출력 형식
- 다른 설명 없이, 가장 중요도가 높은 뉴스 20개 ID를 **쉼표(,)로만 구분**하여 한 줄로 출력
- 예시: 5,12,3,1,8,2,7,11,0,4

가장 중요한 20개 뉴스의 ID를 순서대로 작성하세요:
"""

    try:
        response = safe_api_call(
            client, 
            [MessageParam(role="user", content=prompt)],
            max_retries=5,
            base_delay=3
        )
    except Exception as e:
        print(f"  ! Claude API 호출 실패: {e}")
        print("  ! 원래 순서대로 뉴스를 반환합니다.")
        return news_list
    response_block = response.content[0]
    response_text = getattr(response_block, 'text', None) or getattr(response_block, 'content', None) or str(response_block)
    response_text = response_text.strip()
    
    try:
        ranked_ids = [int(id_str.strip()) for id_str in response_text.split(',')]
        valid_ranked_ids = [id_val for id_val in ranked_ids if 0 <= id_val < len(news_list)]
        
        ranked_news = [news_list[i] for i in valid_ranked_ids]
        unranked_news_ids = set(range(len(news_list))) - set(valid_ranked_ids)
        unranked_news = [news_list[i] for i in unranked_news_ids]

        return ranked_news + unranked_news
    except ValueError:
        print("  ! AI 순위 응답 파싱 실패. 원래 순서대로 반환합니다.")
        return news_list

def create_parody_with_claude(news_content, original_prompt, existing_content, retry_context=None):
    """Claude AI를 사용하여 패러디 생성 (전체 콘텐츠 중복 방지 및 자동 복구 기능 포함)"""
    client = Anthropic(api_key=CLAUDE_API_KEY)
    
    # 강화된 중복 방지를 위한 프롬프트 추가
    if existing_content:
        duplication_warning = (
            "\n\n## 🚨 (매우 중요) 절대적 중복 방지 규칙\n"
            "- 아래는 이미 생성된 모든 패러디 콘텐츠입니다.\n"
            "- 절대로 아래와 유사한 제목, 표현, 패턴, 스타일을 사용하지 마세요.\n"
            "- 완전히 새롭고 창의적인 콘텐츠를 만들어야 합니다.\n\n"
            "### 📜 이미 생성된 콘텐츠 목록:\n"
        )
        
        for i, content in enumerate(existing_content):
            duplication_warning += f"\n[{i+1}]\n"
            duplication_warning += f"제목: {content.get('parody_title', '')}\n"
            duplication_warning += f"Setup: {content.get('setup', '')}\n"
            duplication_warning += f"Punchline: {content.get('punchline', '')}\n"
            duplication_warning += f"Lesson: {content.get('humor_lesson', '')}\n"
        
        duplication_warning += (
            "\n\n## ❌ 절대 금지 패턴들\n"
            "- '월급은 그대로인데' 표현 금지\n"
            "- '개미들 이럴 줄이야' 표현 금지\n"
            "- '동료: ○○ 나: △△ 동료: 우리 회사도...' 대화 패턴 금지\n"
            "- '계단으로 오르고 창문/엘리베이터로' 표현 금지\n"
            "- '천문학적', '천정부지' 등 과장 표현 반복 금지\n"
            "- '또 뚝!', '또 쾅!' 등 의성어 반복 금지\n\n"
            "## ✅ 필수 다양화 요구사항\n"
            "- 제목: 숫자형/질문형/감탄형/비교형 등 완전히 다른 스타일 사용\n"
            "- Setup: 출근/점심/퇴근/주말/휴가 등 다양한 상황 설정\n"
            "- Punchline: 독백/상황극/밈/패러디/인터뷰 등 형식 변화\n"
            "- Lesson: 실용조언/명언/유머/격언 등 톤앤매너 변화\n"
        )
        
        original_prompt += duplication_warning

    messages = [MessageParam(role="user", content=original_prompt)]
    
    if retry_context:
        user_message = f"""이전 응답에 오류가 있었습니다. 오류를 수정해서 다시 유효한 JSON만 출력해주세요.
## 이전 응답 (잘못된 부분)
{retry_context['malformed_json']}
## 발생한 오류
{retry_context['error_message']}
위 오류를 참고하여, 유효한 JSON 형식에 맞춰 수정된 응답을 ```json ... ``` 코드 블록 안에 다시 생성해주세요.
"""
        # 빈 메시지 방지를 위해 내용이 있을 때만 추가
        if retry_context['malformed_json'].strip():
            messages.append(MessageParam(role="assistant", content=retry_context['malformed_json']))
        messages.append(MessageParam(role="user", content=user_message))

    try:
        response = safe_api_call(client, messages, max_retries=5, base_delay=3)
    except Exception as e:
        print(f"  ! Claude API 호출 실패: {e}")
        raise e
    
    return response.content

def save_to_gsheet(parody_data_list):
    """패러디 데이터를 구글 시트에 저장 (시트 초기화 후 저장)"""
    sheet = get_gsheet(SHEET_ID, 'today_stock_parody')
    
    # 시트 초기화
    sheet.clear()
    
    # 헤더 추가
    headers = [
        'date', 'original_title', 'parody_title', 'setup', 
        'punchline', 'humor_lesson', 'disclaimer', 'source_url'
    ]
    sheet.append_row(headers)
    
    # 데이터 추가
    for parody_data in parody_data_list:
        row = [
            parody_data.get('date', ''),
            parody_data.get('original_title', ''),
            parody_data.get('parody_title', ''),
            parody_data.get('setup', ''),
            parody_data.get('punchline', ''),
            parody_data.get('humor_lesson', ''),
            parody_data.get('disclaimer', ''),
            parody_data.get('source_url', '')
        ]
        sheet.append_row(row)

def save_to_csv(parody_data_list):
    """패러디 데이터를 CSV 파일로 저장"""
    try:
        # 현재 날짜와 시간으로 파일명 생성
        now = get_today_kst()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_gsni.csv"
        
        # CSV 파일 경로 설정
        csv_dir = "csv_data"
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, filename)
        
        # 기존 CSV 파일 모두 삭제 (새로운 파일만 생성)
        print("🧹 기존 CSV 파일 정리 중...")
        csv_files = glob.glob(os.path.join(csv_dir, '*.csv'))
        if len(csv_files) > 0:
            deleted_count = 0
            for old_file in csv_files:
                try:
                    os.remove(old_file)
                    print(f"   - 기존 CSV 파일 삭제: {os.path.basename(old_file)}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   - 파일 삭제 실패: {os.path.basename(old_file)} ({e})")
            print(f"   - 총 {deleted_count}개 기존 CSV 파일 삭제 완료")
        else:
            print("   - 삭제할 기존 CSV 파일이 없습니다")
        
        # CSV 파일 생성
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'date', 'original_title', 'parody_title', 'setup', 
                'punchline', 'humor_lesson', 'disclaimer', 'source_url'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 헤더 작성
            writer.writeheader()
            
            # 데이터 작성
            for parody_data in parody_data_list:
                writer.writerow(parody_data)
        
        print(f"📄 CSV 파일 저장 완료: {csv_path}")
        return csv_path
        
    except Exception as e:
        print(f"❌ CSV 파일 저장 실패: {e}")
        return None

def upload_to_google_drive(csv_path, folder_id):
    """CSV 파일을 Google Drive에 업로드"""
    try:
        # Google Drive API 인증
        creds = None
        token_path = 'youtube_uploader/token.json'
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, 
                ['https://www.googleapis.com/auth/drive.file'])
        
        if not creds:
            print("⚠️ Google Drive 인증 파일을 찾을 수 없습니다.")
            return None
        
        # Google Drive 서비스 생성
        service = build('drive', 'v3', credentials=creds)
        
        # 파일 메타데이터 설정
        file_metadata = {
            'name': os.path.basename(csv_path),
            'parents': [folder_id]
        }
        
        # 파일 업로드
        media = MediaFileUpload(csv_path, mimetype='text/csv', resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        file_url = f"https://drive.google.com/file/d/{file_id}/view"
        
        print(f"☁️ Google Drive 업로드 완료: {file_url}")
        return file_url
        
    except Exception as e:
        print(f"❌ Google Drive 업로드 실패: {e}")
        return None

def safe_api_call(client, messages, max_retries=3, base_delay=2):
    """API 호출을 안전하게 수행하는 함수 (재시도 로직 포함)"""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.8,
                system="",
                messages=messages
            )
            return response
        except OverloadedError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 지수 백오프
                print(f"  ! API 과부하 오류 (시도 {attempt + 1}/{max_retries}). {delay}초 후 재시도...")
                time.sleep(delay)
            else:
                print(f"  ! 최대 재시도 횟수 초과. API 과부하로 인한 실패.")
                raise e
        except (RateLimitError, APIError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"  ! API 오류 (시도 {attempt + 1}/{max_retries}). {delay}초 후 재시도...")
                time.sleep(delay)
            else:
                print(f"  ! 최대 재시도 횟수 초과. API 오류로 인한 실패.")
                raise e
        except Exception as e:
            print(f"  ! 예상치 못한 오류: {e}")
            raise e

def main():
    try:
        print("[1/5] 한경 증권뉴스만 중요도 순으로 뉴스 선별 중...")
        raw_config = parse_rawdata()
        if not raw_config:
            print("[오류] 설정 파일(asset/rawdata.txt)을 읽을 수 없습니다. 프로그램을 종료합니다.")
            return
        
        # 카드뉴스 개수 설정 가져오기
        card_count_config = raw_config.get('카드뉴스개수', ['카드뉴스 개수 : 최대 20개.'])
        card_count_str = card_count_config[0] if isinstance(card_count_config, list) else card_count_config
        card_count = 20  # 기본값
        
        # "카드뉴스 개수 : 최대 X개." 형식에서 숫자 추출
        import re
        count_match = re.search(r'최대 (\d+)개', card_count_str)
        if count_match:
            card_count = int(count_match.group(1))
            print(f"[설정] 카드뉴스 개수: {card_count}개")
        else:
            print(f"[설정] 카드뉴스 개수 파싱 실패, 기본값 {card_count}개 사용")
        
        rss_urls = raw_config.get('RSS_URL 지정', [])
        if isinstance(rss_urls, str):
            rss_urls = [rss_urls]
        if not rss_urls:
            print("[오류] asset/rawdata.txt 파일에서 'RSS_URL 지정'을 찾을 수 없습니다.")
            return
        rss_url = rss_urls[0]  # 한경 증권뉴스만 사용
        all_news = fetch_news(rss_url)
        if not all_news:
            print("\n[오류] 한경 증권뉴스에서 뉴스를 가져오지 못했습니다. 프로그램을 종료합니다.")
            return
        print(f"\n[2/5] Claude 3.5가 독자들이 가장 관심을 가질 만한 뉴스 {card_count}개를 직접 선정합니다...")
        ranked_news = rank_news_by_importance_with_claude(all_news)
        top_news = ranked_news[:card_count]
        print(f"\n[2.5/5] 총 {len(top_news)}개 뉴스 선별 완료! 패러디 생성을 시작합니다.")
        print(f"\n[3/5] 중요도 상위 {len(top_news)}개 뉴스로 패러디 생성 중...")
        parody_data_list = []
        today_str = get_today_kst().strftime('%Y-%m-%d')
        existing_content = []  # 전체 콘텐츠 추적
        
        for i, news in enumerate(top_news):
            news_content = f"제목: {news['title']}\n내용: {news['summary']}\n링크: {news['link']}"
            current_date = today_str
            original_title_safe = news['title'].replace('"', "'")
            news_link = news['link']
            news_title = news['title']
            news_summary = news['summary']
            
            # 다양성을 위한 동적 스타일 지정
            style_index = i % 6
            style_instructions = [
                "숫자 충격형 스타일: 구체적 수치와 함께 놀라움 표현",
                "질문형 스타일: 궁금증을 유발하는 질문으로 제목 구성", 
                "비교/대조형 스타일: A vs B 또는 과거와 현재 비교",
                "상황극형 스타일: 특정 상황이나 장면을 연상시키는 제목",
                "밈/트렌드형 스타일: 최신 인터넷 문화나 밈 활용",
                "현실 풍자형 스타일: 직장인/개미 현실을 위트있게 풍자"
            ]
            
            setup_styles = [
                "출근길 지하철에서 뉴스 보는 상황",
                "점심시간 동료들과 대화하는 상황", 
                "퇴근 후 집에서 주식 확인하는 상황",
                "주말 카페에서 투자 고민하는 상황",
                "회사 화장실에서 몰래 주식 보는 상황",
                "새벽에 해외 증시 확인하는 상황"
            ]
            
            punchline_styles = [
                "내적 독백 형식으로 솔직한 심경 표현",
                "가족/친구와의 대화 형식",
                "SNS 댓글이나 메시지 형식",
                "뉴스 인터뷰 패러디 형식", 
                "광고나 홍보 문구 패러디",
                "영화/드라마 대사 패러디"
            ]
            
            parody_prompt = f"""
당신은 조회수 급상승을 목표로 하는 증권 뉴스 패러디 전문가입니다.

【핵심 미션】
- 30-50대 직장인 타겟, 90초 숏폼 콘텐츠
- 바이럴 요소 극대화, 독창성과 차별성 확보
- 기존 뻔한 패턴 완전 탈피

【이번 콘텐츠 스타일 지정】
- 제목 스타일: {style_instructions[style_index]}
- Setup 상황: {setup_styles[style_index]}  
- Punchline 형식: {punchline_styles[style_index]}

【제목 작성 원칙】
- 20자 이내, 클릭 욕구 폭발시키는 킬링 타이틀
- 지정된 스타일에 맞춰 완전히 새로운 접근
- 구체적 숫자/상황/감정 포함하되 뻔한 표현 금지

【카드뉴스 구조】
- parody_title: 지정 스타일의 20자 이내 독창적 제목
- setup: 지정 상황에 맞는 현실적이고 공감되는 한 줄
- punchline: 지정 형식의 위트있고 반전있는 35자 이내 멘트
- humor_lesson: 실용적 투자 조언이나 인생 격언 (기존 뻔한 격언 금지)
- disclaimer: '면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적'
- source_url: 원본 뉴스 링크

【새로운 표현 패턴 예시】
제목: "삼성 20% 급등, 이재용 마법?"
      "4조달러 엔비디아, 한국 GDP 넘었다"
      "파월 해임설? 개미들 '우리도 해임되고파'"
      "코인 법안 통과, 라면도 암호화폐로?"

Setup: "지하철에서 삼성 뉴스 보자마자 주식 앱 켰다"
       "점심시간, 동료가 '엔비디아 뭐냐'고 물어봤다"  
       "퇴근 후 집에서 코인 뉴스에 화들짝했다"

Punchline: "나: (속마음) '이제 월급보다 주식이 더 중요해...'"
           "아내: '또 주식해?' 나: '이건 투자야!' 아내: '망하면 이혼이야!'"
           "댓글: '대박! 나도 사고싶다' → 답글: '이미 늦었어요 ㅠㅠ'"

【출력 예시】
```json
{{
  "date": "{current_date}",
  "original_title": "{original_title_safe}",
  "parody_title": "삼성 20% 폭등! 이재용 마법 실화?",
  "setup": "지하철 2호선에서 삼성 뉴스 보자마자 주식 앱을 켰다.",
  "punchline": "나: (속마음) '드디어 내 삼성전자가...' 옆 아저씨: '뭘 그렇게 웃어?' 나: '로또 당첨됐어요!'",
  "humor_lesson": "투자의 핵심은 타이밍이 아니라 인내심이다. 급등도 좋지만 장기 관점을 잃지 말자.",
  "disclaimer": "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적",
  "source_url": "{news_link}"
}}
```

【절대 규칙】
- 반드시 위 JSON 구조로만 출력 (설명/해설 없이)
- 이모지 절대 금지, 대신 !!!, ???, ~~~ 등 적극 활용
- 지정된 스타일에 맞춰 기존과 완전히 다른 접근
- 모든 필드를 빈 값 없이 창의적으로 채우기
- 뻔한 패턴/표현/구조 완전 배제

아래는 입력 뉴스입니다.
- 제목: {news_title}
- 요약: {news_summary}
- 링크: {news_link}

지정된 스타일과 상황에 맞춰, 기존과 완전히 차별화된 독창적 패러디를 생성하세요.
"""
            print(f"  - [{i+1}/{len(top_news)}] 패러디 생성 중... (스타일: {style_instructions[style_index][:15]}...)")
            response_text = ""
            error = None
            for attempt in range(3):  # 재시도 횟수 증가
                try:
                    retry_context = None
                    if attempt > 0:
                        retry_context = {"malformed_json": response_text, "error_message": str(error)}
                    
                    # API 호출 전 잠시 대기 (API 부하 분산)
                    if attempt > 0:
                        time.sleep(2)
                    
                    parody_result_blocks = create_parody_with_claude(
                        news_content, parody_prompt, existing_content, retry_context
                    )
                    response_block = parody_result_blocks[0]
                    response_text = getattr(response_block, 'text', None) or getattr(response_block, 'content', None) or str(response_block)
                    
                    # JSON 파싱 개선
                    json_match = re.search(r'```json\n(\{.*?\})\n```', response_text, re.DOTALL)
                    if not json_match:
                        start_index = response_text.find('{')
                        end_index = response_text.rfind('}')
                        if start_index != -1 and end_index != -1 and start_index < end_index:
                            json_text = response_text[start_index:end_index+1]
                        else:
                            # JSON이 없는 경우 기본 구조 생성
                            json_text = f'{{"date": "{current_date}", "original_title": "{original_title_safe}", "parody_title": "API 오류로 인한 기본 제목", "setup": "API 호출 중 오류가 발생했습니다.", "punchline": "다시 시도해주세요.", "humor_lesson": "API 서버가 과부하 상태일 수 있습니다.", "disclaimer": "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적", "source_url": "{news_link}"}}'
                    else:
                        json_text = json_match.group(1)
                    
                    parody_data = json.loads(json_text)
                    parody_data_list.append(parody_data)
                    existing_content.append(parody_data)  # 전체 콘텐츠 추가
                    print("    - 성공!")
                    break
                except Exception as e:
                    error = e
                    print(f"    ! 패러디 생성 실패 (시도 {attempt + 1}/3): {e}")
                    if attempt == 2:  # 마지막 시도
                        print(f"    - 최종 실패: {e}")
                        # 기본 패러디 데이터 생성
                        default_parody = {
                            'date': current_date,
                            'original_title': original_title_safe,
                            'parody_title': f"API 오류 - {news_title[:20]}...",
                            'setup': "API 서버 과부하로 인한 기본 설정",
                            'punchline': "서버가 복구되면 다시 시도해주세요",
                            'humor_lesson': "투자보다 중요한 것은 인내심입니다",
                            'disclaimer': "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적",
                            'source_url': news_link
                        }
                        parody_data_list.append(default_parody)
                        existing_content.append(default_parody)
                        print("    - 기본 패러디 데이터로 대체")
        if not parody_data_list:
            print("\n[오류] 패러디 생성에 실패했습니다. 프로그램을 종료합니다.")
            return
        print(f"\n[4/5] 총 {len(parody_data_list)}개 패러디 생성 완료!")
        
        # 구글 시트 저장 시도 (실패해도 계속 진행)
        try:
            save_to_gsheet(parody_data_list)
            print(f"\n[5/5] 구글 시트에 패러디 데이터가 저장되었습니다.")
        except Exception as e:
            print(f"\n[5/5] 구글 시트 저장 실패: {e}")
            print("💡 service_account.json 파일이 필요합니다.")
        
        # CSV 파일 저장
        csv_path = save_to_csv(parody_data_list)
        if csv_path:
            print(f"📄 CSV 파일이 생성되었습니다: {csv_path}")
            print(f"📁 파일 경로: {os.path.abspath(csv_path)}")
            
            # Google Drive 업로드 시도 (선택사항)
            try:
                google_drive_folder_id = "1dpMzrdIl5iL8gmkrxwtiWBCOiMgU-toG"
                drive_url = upload_to_google_drive(csv_path, google_drive_folder_id)
                if drive_url:
                    print(f"☁️ Google Drive 업로드 성공: {drive_url}")
                else:
                    print("ℹ️ Google Drive 업로드 건너뜀 (로컬 CSV 파일만 생성됨)")
            except Exception as e:
                print(f"ℹ️ Google Drive 업로드 건너뜀: {e}")
                print("💡 Google Drive 업로드를 원한다면 generate_drive_token.py를 실행하세요.")
        else:
            print("❌ CSV 파일 생성에 실패했습니다.")
        
        # 구글 시트 저장 실패 시 콘솔에 데이터 출력
        if not csv_path:
            print("📋 생성된 패러디 데이터:")
            for i, data in enumerate(parody_data_list, 1):
                print(f"\n--- 패러디 {i} ---")
                print(f"제목: {data.get('parody_title', 'N/A')}")
                print(f"Setup: {data.get('setup', 'N/A')}")
                print(f"Punchline: {data.get('punchline', 'N/A')}")
                print(f"Lesson: {data.get('humor_lesson', 'N/A')}")
                print(f"원본: {data.get('original_title', 'N/A')}")
        
        print("프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n[치명적 오류] 프로그램 실행 중 예상치 못한 오류가 발생했습니다: {e}")
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()