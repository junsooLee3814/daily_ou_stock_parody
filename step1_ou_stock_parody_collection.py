import os
import feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv
from common_utils import get_gsheet, get_today_kst
import json
import re
from pathlib import Path
import time
from zoneinfo import ZoneInfo
from anthropic.types import MessageParam

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

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0.1,
        system="",
        messages=[MessageParam(role="user", content=prompt)]
    )
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

def create_parody_with_claude(news_content, original_prompt, existing_titles, retry_context=None):
    """Claude AI를 사용하여 패러디 생성 (중복 방지 및 자동 복구 기능 포함)"""
    client = Anthropic(api_key=CLAUDE_API_KEY)
    
    # 중복 방지를 위한 프롬프트 추가
    if existing_titles:
        # f-string 표현식에서 백슬래시를 사용하지 않도록 수정
        title_list_str = "\n- ".join(existing_titles)
        duplication_warning = (
            "\n\n## ✍️ (매우 중요) 중복 패러디 방지\n"
            "- 아래는 이미 생성된 패러디 제목들입니다.\n"
            "- 절대로 아래 목록과 유사한 내용이나 스타일의 `parody_title`을 만들지 마세요.\n"
            "- 완전히 새롭고, 창의적인 제목을 만들어야 합니다.\n\n"
            "### 📜 이미 생성된 제목 목록:\n"
            f"- {title_list_str}"
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
        messages.append(MessageParam(role="assistant", content=retry_context['malformed_json']))
        messages.append(MessageParam(role="user", content=user_message))

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2000,
        temperature=0.7,
        system="",
        messages=messages
    )
    
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

def main():
    print("[1/5] 한경 증권뉴스만 중요도 순으로 뉴스 선별 중...")
    raw_config = parse_rawdata()
    if not raw_config:
        print("[오류] 설정 파일(asset/rawdata.txt)을 읽을 수 없습니다. 프로그램을 종료합니다.")
        return
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
    print(f"\n[2/5] Claude 3.5가 독자들이 가장 관심을 가질 만한 뉴스 20개를 직접 선정합니다...")
    ranked_news = rank_news_by_importance_with_claude(all_news)
    top_news = ranked_news[:20]
    print(f"\n[2.5/5] 총 {len(top_news)}개 뉴스 선별 완료! 패러디 생성을 시작합니다.")
    print(f"\n[3/5] 중요도 상위 {len(top_news)}개 뉴스로 패러디 생성 중...")
    parody_data_list = []
    today_str = get_today_kst().strftime('%Y-%m-%d')
    existing_parody_titles = []
    for i, news in enumerate(top_news):
        news_content = f"제목: {news['title']}\n내용: {news['summary']}\n링크: {news['link']}"
        current_date = today_str
        original_title_safe = news['title'].replace('"', "'")
        news_link = news['link']
        news_title = news['title']
        news_summary = news['summary']
        parody_prompt = f"""
당신은 조회수 급상승을 목표로 하는 증권 뉴스 패러디 전문가입니다.

【핵심 미션】
- 30-50대 직장인 타겟
- 90초 이내 숏폼 콘텐츠
- 아침 출근길 최적화
- 바이럴 요소 극대화

【제목 작성법】
- 20자 이내, 충격 숫자/감정/개미 관점/궁금증 유발 포함
- 날짜, 'AI가 분석한', 쿠팡파트너스 멘션 등은 절대 금지

【카드뉴스 구조】
- parody_title: 20자 이내, 클릭을 부르는 킬링 타이틀 (예: '엔비디아 4조달러! 개미 집단실신')
- setup: 현실 타격, 개미 관점, 회사 개그, 공감대, 희망 메시지, AI 증시 격언, 해시태그 전략 등에서 가장 임팩트 있는 한 줄
- punchline: 위트/반전/재치/회사 대화/밈/이모지 등 활용, 35자 이내
- humor_lesson: 투자자에게 실질적 조언 또는 명언, AI 격언, 긍정적 메시지
- disclaimer: '면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적'
- source_url: 원본 뉴스 링크

【출력 예시】
```json
{{
  "date": "{current_date}",
  "original_title": "{original_title_safe}",
  "parody_title": "엔비디아 4조달러! 개미 집단실신",
  "setup": "개미들, 오늘도 월급은 그대로인데 주가는 또 올랐다.",
  "punchline": "동료: '엔비디아 어때?' 나: '4조 달러 돌파!' 동료: '우리 회사도 4조... 적자!'",
  "humor_lesson": "주가는 계단으로 오르고 창문으로 떨어진다.",
  "disclaimer": "면책조항:패러디/특정기관,개인과 무관/투자조언아님/재미목적",
  "source_url": "{news_link}"
}}
```

【절대 규칙】
- 반드시 위 JSON 구조로만 출력
- 각 필드는 string
- 이모지(emoji)는 절대 사용하지 말 것 (어떤 필드에도 이모지 금지)
- 대신 !!!, ???, ~~~, ... 등 아날로그 방식의 강조(구두점, 느낌표, 물음표, 물결 등)는 적극적으로 활용할 것
- 밈, 회사개그, AI격언, 해시태그 전략은 setup/punchline/humor_lesson에 적극 반영
- 날짜/AI/쿠팡파트너스 멘션은 parody_title에 절대 포함하지 말 것

아래는 입력 뉴스입니다.
- 제목: {news_title}
- 요약: {news_summary}
- 링크: {news_link}

【출력 절대 규칙】
- 반드시 위 JSON 구조로만 출력(설명, 해설, 여는 말, 닫는 말 없이)
- 모든 필드는 string, 빈 값 없이 1~2문장 이내로 채울 것
- 각 필드에 이모지(emoji)는 절대 사용하지 말 것
- 대신 !!!, ???, ~~~, ... 등 아날로그 강조는 적극 활용
- 해시태그는 humor_lesson에 자연스럽게 포함
- 출력 예시와 완전히 동일한 구조, 필드명, 순서로만 출력

위 구조와 지침을 엄격히 따라, 입력 뉴스(제목/요약/링크)를 기반으로 카드뉴스 패러디 콘텐츠를 생성하라.
"""
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
                response_block = parody_result_blocks[0]
                response_text = getattr(response_block, 'text', None) or getattr(response_block, 'content', None) or str(response_block)
                json_match = re.search(r'```json\n(\{.*?\})\n```', response_text, re.DOTALL)
                if not json_match:
                    start_index = response_text.find('{')
                    end_index = response_text.rfind('}')
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        json_text = response_text[start_index:end_index+1]
                    else:
                        json_text = response_text
                else:
                    json_text = json_match.group(1)
                parody_data = json.loads(json_text)
                parody_data_list.append(parody_data)
                existing_parody_titles.append(parody_data['parody_title'])
                print("    - 성공!")
                break
            except Exception as e:
                error = e
                print(f"    ! 파싱 실패 (시도 {attempt + 1}/2)")
                if attempt == 1:
                    print(f"    - 최종 실패: {e}")
    if not parody_data_list:
        print("\n[오류] 패러디 생성에 실패했습니다. 프로그램을 종료합니다.")
        return
    print(f"\n[4/5] 총 {len(parody_data_list)}개 패러디 생성 완료! 구글 시트에 저장합니다.")
    save_to_gsheet(parody_data_list)
    print(f"\n[5/5] 구글 시트에 패러디 데이터가 저장되었습니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    main()