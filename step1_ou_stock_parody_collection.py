import os
import feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv
from common_utils import get_gsheet
from difflib import SequenceMatcher
import json
import re
from pathlib import Path
import time

# .env 파일의 절대 경로를 지정하여 로드
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

# Claude AI API 키
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")

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

def is_similar(str1, str2, threshold=0.8):
    """두 문자열의 유사도를 계산하여 중복 여부 판단"""
    return SequenceMatcher(None, str1, str2).ratio() > threshold

def is_duplicate_news(news_item, existing_news):
    """뉴스 중복 여부 확인"""
    for existing in existing_news:
        if is_similar(news_item['title'], existing['title']):
            return True
    return False

def fetch_news(rss_url, existing_news=None):
    """RSS 피드에서 오늘과 어제 날짜의 뉴스를 가져오는 함수"""
    if existing_news is None:
        existing_news = []
    
    feed = feedparser.parse(rss_url)
    news_list = []
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    for entry in feed.entries:
        published_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            # feedparser가 파싱한 9-tuple 날짜 구조를 datetime 객체로 변환
            published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed)).date()
        
        # 오늘 또는 어제 뉴스가 아니면 건너뜀
        if published_date not in [today, yesterday]:
            continue
            
        title = entry.title
        summary = entry.summary if hasattr(entry, 'summary') else ''
        # 날짜 형식은 YYYY-MM-DD로 통일
        published = published_date.strftime('%Y-%m-%d')
        link = entry.link if hasattr(entry, 'link') else ''
        
        news_item = {
            'title': title,
            'summary': summary,
            'published': published,
            'link': link
        }
        
        # 중복 체크
        if not is_duplicate_news(news_item, existing_news):
            news_list.append(news_item)
            existing_news.append(news_item)
    
    return news_list

def rank_news_by_importance_with_claude(news_list):
    """Claude AI를 사용하여 뉴스 목록을 중요도에 따라 순위 매기기"""
    client = Anthropic(api_key=CLAUDE_API_KEY)

    formatted_news = ""
    for i, news in enumerate(news_list):
        formatted_news += f"ID: {i}\\n제목: {news['title']}\\n\\n"

    prompt = f"""당신은 대한민국 최고의 금융 뉴스 큐레이터입니다.
다음은 오늘과 어제 수집된 주식/증권 관련 뉴스 목록입니다. 
각 뉴스의 중요도를 판단하여, 가장 중요한 뉴스부터 순서대로 ID 목록을 만들어주세요.

## 🌟 중요도 판단 기준 (아래 기준으로 엄격하게 평가해주세요)

### 1. 시장 전체에 미치는 영향 (거시경제, 정책)
- **통화정책 (최우선):** 한국은행, Fed 금리, 양적완화/긴축
- **거시경제 지표:** 환율 급변동, 유가, 물가지수(CPI)
- **정부 정책/규제:** 세법 개정, 부동산 정책, 산업 규제

### 2. 특정 산업 및 기업에 미치는 영향
- **핵심 산업 동향:**
  - **반도체:** 삼성전자, SK하이닉스 실적, HBM, AI칩, 미중갈등
  - **자동차/2차전지:** 현대차/기아 판매량, 전기차, 배터리 수주
  - **바이오/신약:** FDA 승인, 임상 결과 발표
  - **플랫폼/IT:** 네이버, 카카오 관련 규제, 신작 발표
- **주요 기업 실적:** 분기 실적 발표, 어닝 서프라이즈/쇼크

### 3. 투자자 동향
- **외국인/기관:** 대규모 순매수/순매도, 연기금 동향

## 📰 뉴스 목록
{formatted_news}

## 💻 출력 형식
- 다른 설명 없이, 가장 중요도가 높은 뉴스부터 순서대로 ID를 **쉼표(,)로만 구분**하여 한 줄로 출력해주세요.
- 예시: 5,12,3,1,8,2,7,11,0,4

가장 중요한 순서대로 ID 목록을 작성해주세요:
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text.strip()
    
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

def create_parody_with_claude(news_content, original_prompt, existing_titles, retry_context=None):
    """Claude AI를 사용하여 패러디 생성 (중복 방지 및 자동 복구 기능 포함)"""
    client = Anthropic(api_key=CLAUDE_API_KEY)
    
    # 중복 방지를 위한 프롬프트 추가
    if existing_titles:
        duplication_warning = (
            "\\n\\n## ✍️ (매우 중요) 중복 패러디 방지\\n"
            "- 아래는 이미 생성된 패러디 제목들입니다.\\n"
            "- 절대로 아래 목록과 유사한 내용이나 스타일의 `parody_title`을 만들지 마세요.\\n"
            "- 완전히 새롭고, 창의적인 제목을 만들어야 합니다.\\n\\n"
            "### 📜 이미 생성된 제목 목록:\\n"
            f"- {'\\n- '.join(existing_titles)}"
        )
        original_prompt += duplication_warning

    messages = [{"role": "user", "content": original_prompt}]
    
    if retry_context:
        user_message = f"""이전 응답에 오류가 있었습니다. 오류를 수정해서 다시 유효한 JSON만 출력해주세요.
## 이전 응답 (잘못된 부분)
{retry_context['malformed_json']}
## 발생한 오류
{retry_context['error_message']}
위 오류를 참고하여, 유효한 JSON 형식에 맞춰 수정된 응답을 ```json ... ``` 코드 블록 안에 다시 생성해주세요.
"""
        messages.append({"role": "assistant", "content": retry_context['malformed_json']})
        messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2000,
        temperature=0.7,
        messages=messages
    )
    
    return response.content

def save_to_gsheet(parody_data_list):
    """패러디 데이터를 구글 시트에 저장 (시트 초기화 후 저장)"""
    sheet = get_gsheet(SHEET_NAME)
    
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

def main():
    print("[1/5] 뉴스 소스별 중요도 순으로 뉴스 선별 중...")
    
    # 설정 파일 로드
    raw_config = parse_rawdata()
    if not raw_config:
        print("[오류] 설정 파일(asset/rawdata.txt)을 읽을 수 없습니다. 프로그램을 종료합니다.")
        return

    # RSS 피드 URL 설정
    rss_urls = raw_config.get('RSS_URL 지정', [])
    if isinstance(rss_urls, str): # 값이 하나일 경우 문자열일 수 있음
        rss_urls = [rss_urls]

    if not rss_urls:
        print("[오류] asset/rawdata.txt 파일에서 'RSS_URL 지정'을 찾을 수 없습니다.")
        return
        
    RSS_FEEDS = {}
    for url in rss_urls:
        if 'mk.co.kr' in url:
            RSS_FEEDS["매일경제_증권"] = url
        elif 'yna.co.kr' in url:
            RSS_FEEDS["연합뉴스_증권"] = url

    # 최종적으로 선택될 뉴스 목록
    top_news = []
    # 전체 소스에서 중복을 확인하기 위한 뉴스 제목 집합
    collected_titles = set()
    # 각 소스별로 순위가 매겨진 뉴스 후보군
    source_candidates = {}

    # 1. 각 소스별로 뉴스 후보군 생성
    for source, url in RSS_FEEDS.items():
        print(f"\\n  -> '{source}' 후보군 생성 중...")
        
        # 뉴스 가져오기 (이전 단계는 없으므로, 소스 내 중복만 체크)
        news_from_source = fetch_news(url)
        
        if not news_from_source:
            print("    - 오늘/어제 뉴스가 없어 후보군을 생성할 수 없습니다.")
            continue
            
        print(f"    - 오늘/어제 뉴스 {len(news_from_source)}건 수집 완료.")
        
        print("    - AI를 통해 중요도 순위 선정 중...")
        try:
            # 후보군을 넉넉하게 10개로 설정
            ranked_news = rank_news_by_importance_with_claude(news_from_source)
            source_candidates[source] = ranked_news
            print(f"    - '{source}' 후보군 {len(ranked_news)}개 생성 완료.")
        except Exception as e:
            print(f"      - AI 순위 선정 실패: {e}")
            source_candidates[source] = news_from_source # 실패 시 원래 순서대로

    # 2. 소스별 후보군에서 중복을 피해 최종 뉴스 20개 선별 (교차 방식)
    print("\\n[2/5] 최종 뉴스 20개 선별 중 (매경/연합 교차, 중복 제거)...")
    
    mk_candidates = source_candidates.get("매일경제_증권", [])
    yn_candidates = source_candidates.get("연합뉴스_증권", [])
    
    mk_idx, yn_idx = 0, 0

    # 20개가 채워지거나, 두 후보군 모두 소진될 때까지 반복
    while len(top_news) < 20 and (mk_idx < len(mk_candidates) or yn_idx < len(yn_candidates)):
        
        # 매경 턴 (top_news가 20개 미만일 때)
        if len(top_news) < 20 and mk_idx < len(mk_candidates):
            while mk_idx < len(mk_candidates):
                candidate = mk_candidates[mk_idx]
                is_new = not any(is_similar(candidate['title'], existing['title']) for existing in top_news)
                mk_idx += 1
                if is_new:
                    top_news.append(candidate)
                    break

        # 연합 턴 (top_news가 20개 미만일 때)
        if len(top_news) < 20 and yn_idx < len(yn_candidates):
            while yn_idx < len(yn_candidates):
                candidate = yn_candidates[yn_idx]
                is_new = not any(is_similar(candidate['title'], existing['title']) for existing in top_news)
                yn_idx += 1
                if is_new:
                    top_news.append(candidate)
                    break
    
    if not top_news:
        print("\\n[오류] 모든 소스에서 뉴스를 가져오지 못했습니다. 프로그램을 종료합니다.")
        return

    print(f"\\n[2.5/5] 총 {len(top_news)}개 고유 뉴스 선별 완료! 패러디 생성을 시작합니다.")
    
    print(f"\\n[3/5] 중요도 상위 {len(top_news)}개 뉴스로 패러디 생성 중...")
    parody_data_list = []

    today_str = datetime.now().strftime('%Y-%m-%d')
    existing_parody_titles = [] # 생성된 패러디 제목을 저장할 리스트
    for i, news in enumerate(top_news):
        news_content = f"제목: {news['title']}\\n내용: {news['summary']}\\n링크: {news['link']}"
        
        # 프롬프트에 사용될 변수들을 미리 준비하여 f-string 오류 방지
        current_date = datetime.now().strftime('%Y-%m-%d')
        original_title_safe = news['title'].replace('"', "'")
        news_link = news['link']

        parody_prompt = f"""당신은 유머 감각이 뛰어난 금융 전문가이자 시나리오 작가입니다. 
주어진 뉴스를 바탕으로, 주식 시장의 상황을 재치있게 풍자하는 짧은 패러디를 만들어 주세요.

## 📰 분석할 뉴스 원문
- **제목:** {news['title']}
- **요약:** {news['summary']}

## 📝 패러디 생성 가이드라인
1.  **패러디 제목 (parody_title):**
    - **(중요) 15~20자 내외로 매우 짧고 컴팩트하게** 만들어주세요.
    - 뉴스 내용을 한 문장으로 압축하면서도, 웃음을 유발하는 반전이나 과장을 담아주세요.
    - 예시: "삼전, HBM 테스트 통과? AI는 안도의 한숨"
2.  **상황 설정 (setup):**
    - **(중요) 35자 내외의 초단문으로** 배경을 설명해주세요.
    - 뉴스 내용을 바탕으로, 유머를 위한 무대를 만들어주세요.
3.  **반전/웃음 포인트 (punchline):**
    - **(중요) 35자 내외의 초단문으로** 상황을 비틀어 웃음을 주세요.
    - 의인화, 과장, 예상치 못한 연결 등을 활용하여 창의적인 유머를 구사해주세요.
4.  **유머로 풀어본 교훈 (humor_lesson):**
    - 패러디의 내용을 주식 투자와 연결하여, 가볍지만 생각해볼 만한 교훈을 한 문장으로 제시해주세요.
    - 예시: "진정한 저점은 AI도 모르는 법, 분산 투자가 정답이다."
5.  **면책조항 (disclaimer):**
    - 항상 다음 문구를 그대로 사용해주세요: "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적"
    
## 💻 출력 형식
- 반드시 아래와 같은 JSON 형식으로만 응답해주세요.


- 각 필드의 값은 문자열(string)이어야 합니다.
- **(절대 규칙) 절대로 이모지(emoji)는 사용하지 마세요.**

```json
{{
  "date": "{current_date}",
  "original_title": "{original_title_safe}",
  "parody_title": "여기에 패러디 제목",
  "setup": "여기에 상황 설정",
  "punchline": "여기에 반전/웃음 포인트",
  "humor_lesson": "여기에 유머로 풀어본 교훈",
  "disclaimer": "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적",
  "source_url": "{news_link}"
}}
```

위 가이드라인을 엄격히 따라서, 창의적이고 재미있는 패러디를 만들어주세요."""

        print(f"  - [{i+1}/{len(top_news)}] 패러디 생성 중...")
        
        response_text = ""
        error = None
        
        for attempt in range(2):
            try:
                retry_context = None
                if attempt > 0:
                    retry_context = {"malformed_json": response_text, "error_message": str(error)}
                
                parody_result_blocks = create_parody_with_claude(
                    news_content, parody_prompt, existing_parody_titles, retry_context
                )
                
                response_text = parody_result_blocks[0].text
                
                json_match = re.search(r'```json\n(\{.*?\})\n```', response_text, re.DOTALL)
                if not json_match:
                    json_text = response_text
                else:
                    json_text = json_match.group(1)

                parody_data = json.loads(json_text)
                
                parody_data_list.append(parody_data)
                existing_parody_titles.append(parody_data['parody_title']) # 생성된 제목을 목록에 추가
                print("    - 성공!")
                break
            
            except Exception as e:
                error = e
                print(f"    ! 파싱 실패 (시도 {attempt + 1}/2)")
                if attempt == 1:
                    print(f"    - 최종 실패: {e}")
    
    print(f"\\n[4/5] 구글 시트에 저장 중... (총 {len(parody_data_list)}개)")
    save_to_gsheet(parody_data_list)
    
    print(f"\\n[5/5] 모든 작업 완료! {len(parody_data_list)}개의 패러디가 구글 시트에 저장되었습니다.")

if __name__ == "__main__":
    main() 