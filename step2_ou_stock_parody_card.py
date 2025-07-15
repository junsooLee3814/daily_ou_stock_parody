import os
import glob
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from common_utils import get_gsheet, get_today_kst
from datetime import datetime
import sys
from dotenv import load_dotenv
load_dotenv()

print("1. 초기화 시작...")

# --- 카드 디자인 상수 ---
CARD_WIDTH = 1080
CARD_HEIGHT = 1920
LEFT_MARGIN = 80
RIGHT_MARGIN = 80
TOP_MARGIN = 300
BOTTOM_MARGIN = 200
LINE_SPACING_RATIO = 1.2
SECTION_GAP = 40

# --- 폰트 크기 ---
DATE_FONT_SIZE = 45
PARODY_TITLE_FONT_SIZE = 70
SETUP_FONT_SIZE = 48
PUNCHLINE_FONT_SIZE = 48
LESSON_LABEL_FONT_SIZE = 48
LESSON_FONT_SIZE = 60
DISCLAIMER_FONT_SIZE = 28
SOURCE_FONT_SIZE = 28

# --- 색상 ---
GREEN_COLOR = (0, 60, 200, 255) # 짙은 파란색(RGBA)
BLACK_COLOR = (34, 34, 34)
GRAY_COLOR = (120, 120, 120)

print("2. 폰트 로드 시작...")

# 폰트 경로 설정
KOR_FONT_PATH = os.path.join("asset", "Pretendard-Regular.otf")
KOR_FONT_BOLD_PATH = os.path.join("asset", "Pretendard-Bold.otf")

def load_font(path, size):
    try:
        if os.path.exists(path):
            font = ImageFont.truetype(path, size)
            print(f"[성공] 폰트 로드: {path} (크기: {size})")
            return font
        else:
            print(f"[실패] 폰트 파일 없음: {path}")
            return ImageFont.load_default()
    except Exception as e:
        print(f"[실패] 폰트 로드 ({path}): {str(e)}")
        return ImageFont.load_default()

# 폰트 로드
try:
    date_font = load_font(KOR_FONT_PATH, DATE_FONT_SIZE)
    parody_title_font = load_font(KOR_FONT_BOLD_PATH, PARODY_TITLE_FONT_SIZE)
    setup_font = load_font(KOR_FONT_PATH, SETUP_FONT_SIZE)
    punchline_font = load_font(KOR_FONT_PATH, PUNCHLINE_FONT_SIZE)
    lesson_label_font = load_font(KOR_FONT_PATH, LESSON_LABEL_FONT_SIZE)
    lesson_font = load_font(KOR_FONT_BOLD_PATH, LESSON_FONT_SIZE)
    disclaimer_font = load_font(KOR_FONT_PATH, DISCLAIMER_FONT_SIZE)
    source_font = load_font(KOR_FONT_PATH, SOURCE_FONT_SIZE)
except Exception as e:
    print(f"[치명적 오류] 폰트 로드 중 예외 발생: {e}")
    sys.exit(1)

# asset 리소스 체크
asset_files = [KOR_FONT_PATH, KOR_FONT_BOLD_PATH, os.path.join("asset", "card_1080x1920.png"), os.path.join("asset", "bgm.mp3"), os.path.join("asset", "intro_OU_stock.jpg")]
for af in asset_files:
    if not os.path.exists(af):
        print(f"[경고] 리소스 파일 누락: {af}")

print("3. 구글 시트 연결 시작...")

# 구글 시트에서 데이터 가져오기
try:
    sheet = get_gsheet(os.getenv('GSHEET_ID'), 'today_stock_parody')
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    print(f"불러온 데이터 수: {len(df)}")
except Exception as e:
    print(f"구글 시트 데이터 로드 실패: {e}")
    df = pd.DataFrame()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def draw_text(draw, position, text, font, fill, max_width, line_spacing_ratio=1.5, align='left', spacing=0):
    """주어진 위치에 텍스트를 그리는 함수 (줄바꿈 및 정렬 지원)"""
    x, y = position
    
    # 텍스트 줄바꿈 처리
    words = str(text).split()
    if not words:
        return y

    lines = []
    current_line = words[0]
    for word in words[1:]:
        if font.getlength(current_line + ' ' + word) <= max_width:
            current_line += ' ' + word
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    line_height = font.size * line_spacing_ratio
    
    # 각 줄을 그림
    for line in lines:
        line_width = font.getlength(line)
        
        draw_x = x
        if align == 'center':
            # 중앙 정렬 시 x 위치를 카드 전체 너비 기준으로 계산
            draw_x = (CARD_WIDTH - line_width) / 2
            
        draw.text((draw_x, y), line, font=font, fill=fill, spacing=spacing)
        y += line_height
        
    return y

print("4. 출력 폴더 생성...")

# 출력 폴더 생성 및 정리
os.makedirs('parody_card', exist_ok=True)
for f in glob.glob('parody_card/*.png'):
    os.remove(f)

print("5. 카드 생성 시작...")

if df.empty:
    print("[경고] 구글 시트에서 불러온 데이터가 없습니다. 카드 생성 작업을 건너뜁니다.")
else:
    # 각 패러디 데이터에 대해 카드 생성
    for idx_int, (idx, row) in enumerate(df.iterrows()):
        try:
            print(f"\n[{idx_int+1}/{len(df)}] 카드 생성 중...")
            
            card_path = os.path.join(BASE_DIR, "asset", "card_1080x1920.png")
            try:
                card = Image.open(card_path).convert("RGBA")
            except Exception as e:
                print(f"  - 템플릿 로드 실패: {str(e)}")
                continue
                
            draw = ImageDraw.Draw(card)
            max_text_width = CARD_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

            # --- 상단부터 순서대로 그리는 텍스트 ---
            y = TOP_MARGIN

            # [오늘의 유머] 및 페이지 번호 추가
            total_pages = len(df)
            page_info_text = f"[오늘의 유머 {idx_int+1}/{total_pages}]"
            draw.text((LEFT_MARGIN, y), page_info_text, font=date_font, fill=GRAY_COLOR, spacing=-3)
            y += DATE_FONT_SIZE + 20

            if 'date' in row and bool(pd.notna(row['date'])):
                date_str = str(row['date'])
                try:
                    # 날짜 문자열을 datetime 객체로 변환
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    # 영어 요일 약어 (e.g., Fri)
                    day_of_week = date_obj.strftime('%a')
                    # 최종 날짜 문자열 형식 지정 (예: 2025-06-20.Fri.)
                    formatted_date = f"{date_str}.{day_of_week}."
                except ValueError:
                    # 날짜 형식이 잘못된 경우를 대비한 예외 처리
                    formatted_date = date_str

                draw.text((LEFT_MARGIN, y), formatted_date, font=date_font, fill=GRAY_COLOR, spacing=-3)
                y += DATE_FONT_SIZE + SECTION_GAP

            # setup 위에 original_title 추가
            if 'original_title' in row and bool(pd.notna(row['original_title'])):
                y = draw_text(draw, (LEFT_MARGIN, y), str(row['original_title']), 
                                        setup_font, BLACK_COLOR, 
                                        max_text_width, line_spacing_ratio=LINE_SPACING_RATIO, spacing=-3)
                y += int(SECTION_GAP * 0.7)
            if 'setup' in row and bool(pd.notna(row['setup'])):
                y = draw_text(draw, (LEFT_MARGIN, y), str(row['setup']), 
                                        setup_font, BLACK_COLOR, 
                                        max_text_width, line_spacing_ratio=LINE_SPACING_RATIO, spacing=-3)
                y += SECTION_GAP
                
            if 'punchline' in row and bool(pd.notna(row['punchline'])):
                y = draw_text(draw, (LEFT_MARGIN, y), str(row['punchline']), 
                                        punchline_font, BLACK_COLOR, 
                                        max_text_width, line_spacing_ratio=LINE_SPACING_RATIO, spacing=-3)
                # 펀치라인 아래 2줄 간격 추가
                y += int(PUNCHLINE_FONT_SIZE * 2)
                # parody_title 블록 ([오유_제목] + parody_title)
                if 'parody_title' in row and bool(pd.notna(row['parody_title'])):
                    # [오유_제목] 라벨 ([오유_교훈]과 동일한 폰트/색상/크기)
                    oyutitle_label = "[오유_제목]"
                    y = draw_text(draw, (LEFT_MARGIN, y), oyutitle_label, lesson_label_font, GREEN_COLOR, max_text_width, line_spacing_ratio=1.5, align='left', spacing=-4)
                    # parody_title (기존 폰트/색상/크기)
                    y = draw_text(draw, (LEFT_MARGIN, y), str(row['parody_title']), parody_title_font, GREEN_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO, spacing=-3)
                    y += SECTION_GAP * 1.5

            # 오유-교훈(유머레슨) 블록을 펀치라인 바로 아래에 출력
            if 'humor_lesson' in row and bool(pd.notna(row['humor_lesson'])):
                lesson_label_text = "[오유_교훈]"
                lesson_content_text = str(row['humor_lesson'])
                # 라벨
                y = draw_text(draw, (LEFT_MARGIN, y), lesson_label_text, lesson_label_font, GREEN_COLOR, max_text_width, line_spacing_ratio=1.5, align='left', spacing=-4)
                # 내용
                y = draw_text(draw, (LEFT_MARGIN, y), lesson_content_text, lesson_font, GREEN_COLOR, max_text_width, line_spacing_ratio=1.5, align='left', spacing=-4)

            # --- 하단부터 역순으로 그리는 텍스트 ---
            bottom_y = CARD_HEIGHT - BOTTOM_MARGIN

            # 출처
            if 'original_title' in row and bool(pd.notna(row['original_title'])):
                title_part = str(row['original_title'])
                url_part = ""
                if 'source_url' in row and bool(pd.notna(row['source_url'])):
                    url_part = f",{str(row['source_url'])}"

                source_text = f"출처: {title_part}{url_part}"

                # 텍스트가 너무 길면 줄여서 표시
                if len(source_text) > 80:
                    source_text = source_text[:80] + "..."

                source_y_start = bottom_y - SOURCE_FONT_SIZE
                draw.text((LEFT_MARGIN, source_y_start), source_text, font=source_font, fill=GRAY_COLOR, spacing=-3)
                bottom_y = source_y_start - 20

            # 면책조항
            if 'disclaimer' in row and bool(pd.notna(row['disclaimer'])):
                disclaimer_text = str(row['disclaimer'])
                # "면책조항:" 접두어가 없는 경우를 대비해 추가
                if not disclaimer_text.startswith("면책조항:"):
                    disclaimer_text = f"면책조항:{disclaimer_text}"

                # 높이를 추정하여 아래에서부터 그리기
                words = disclaimer_text.split()
                lines_for_height_calc = []
                if words:
                    current_line = words[0]
                    for word in words[1:]:
                        if disclaimer_font.getlength(current_line + ' ' + word) <= max_text_width:
                            current_line += ' ' + word
                        else:
                            lines_for_height_calc.append(current_line)
                            current_line = word
                    lines_for_height_calc.append(current_line)
                
                estimated_height = len(lines_for_height_calc) * int(DISCLAIMER_FONT_SIZE * 1.3)
                disclaimer_y_start = bottom_y - estimated_height
                
                draw_text(draw, (LEFT_MARGIN, disclaimer_y_start), disclaimer_text, 
                                disclaimer_font, GRAY_COLOR, max_text_width, spacing=-4)
                bottom_y = disclaimer_y_start - 10

            # 카드 저장
            out_path = os.path.join('parody_card', f'parody_card_{idx_int+1:02d}.png')
            try:
                card.save(out_path)
                print(f"  - 카드 저장 완료: {out_path}")
            except Exception as e:
                print(f"  - 카드 저장 실패: {str(e)}")
        except Exception as e:
            print(f"[오류] 카드 생성 실패 (index={idx_int}, title={row.get('original_title', '')}): {e}")

if not df.empty:
    print(f"\n6. 모든 작업 완료! 생성된 카드: {len(df)}장")
else:
    print("\n데이터가 없어 작업을 완료할 수 없습니다.") 