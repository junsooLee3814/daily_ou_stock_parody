"""
step3_ou_stock_parody_video.py

parody_card 폴더에 생성된 카드뉴스 이미지들을 동영상으로 제작합니다.
- 인트로 이미지(intro_ou_stock.png)를 영상 처음에 추가합니다.
- 각 카드 이미지에 줌인 효과를 적용합니다.
- 배경음악(bgm.mp3)을 페이드인/아웃 효과와 함께 추가합니다.

실행 전 FFmpeg가 설치되어 있어야 합니다.
"""

import os
import glob
import subprocess
from datetime import datetime
import shutil
import re
import time
from common_utils import get_today_kst
import sys

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

print("--- 패러디 카드 동영상 제작 시작 ---")

# 설정 파일 로드
raw_config = parse_rawdata()
card_duration_str = raw_config.get('동영상길이', '카드뉴스별 동영상 길이 : 4초')
try:
    match = re.search(r'\d+', card_duration_str)
    if match:
        card_duration_val = int(match.group())
    else:
        card_duration_val = 4
except (AttributeError, ValueError):
    card_duration_val = 4

# --- 설정 ---
CARD_DURATION = card_duration_val  # 각 카드 이미지의 노출 시간 (초)
INTRO_DURATION = 4 # 인트로 이미지의 노출 시간 (초)
WIDTH, HEIGHT = 1080, 1920 # 동영상 해상도

# --- 경로 설정 ---
now_str = get_today_kst().strftime('%Y%m%d')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARD_IMG_DIR = os.path.join(BASE_DIR, 'parody_card')
VIDEO_OUT_DIR = os.path.join(BASE_DIR, 'parody_video')
SINGLE_CLIP_DIR = os.path.join(VIDEO_OUT_DIR, 'single_clips')

INTRO_IMG_PATH = os.path.join(BASE_DIR, 'asset', 'intro_OU_stock.jpg')
BGM_PATH = os.path.join(BASE_DIR, 'asset', 'bgm.mp3')

INTRO_CLIP_PATH = os.path.join(SINGLE_CLIP_DIR, f'intro_clip_{now_str}.mp4')
MERGED_CLIP_PATH = os.path.join(VIDEO_OUT_DIR, f'merged_parody_{now_str}.mp4')
FINAL_VIDEO_PATH = os.path.join(VIDEO_OUT_DIR, f'ou_stock_parody_final_{now_str}.mp4')

# --- 폴더 생성 ---
os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
os.makedirs(SINGLE_CLIP_DIR, exist_ok=True)

# asset 리소스 체크
asset_files = [INTRO_IMG_PATH, BGM_PATH]
for af in asset_files:
    if not os.path.exists(af):
        print(f"[경고] 리소스 파일 누락: {af}")

# parody_card 폴더에 이미지가 없을 때 안내
card_images = sorted(glob.glob(os.path.join(CARD_IMG_DIR, '*.png')))
if not card_images:
    print("[경고] 'parody_card' 폴더에 카드 이미지 파일이 없습니다. 동영상 제작을 건너뜁니다.")
    sys.exit(0)

def create_intro_video(img_path, out_path, duration):
    """인트로 이미지를 사용하여 줌 효과가 적용된 비디오 클립을 생성합니다."""
    if not os.path.exists(img_path):
        print(f"[오류] 인트로 이미지 파일 없음: {img_path}")
        return None
    
    print("1. 인트로 영상 제작 중...")
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img_path,
        "-t", str(duration),
        "-vf", f"zoompan=z='min(zoom+0.001,1.05)':d={duration*25}:s={WIDTH}x{HEIGHT}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 인트로 영상 저장 완료: {out_path}")
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"[오류] 인트로 영상 제작 실패(FFmpeg 문제 가능): {e.stderr}")
        return None

def create_card_videos(card_img_paths, duration):
    """카드 이미지들을 개별 비디오 클립으로 변환합니다."""
    video_clips = []
    total_cards = len(card_img_paths)
    print(f"2. 총 {total_cards}개의 카드 이미지로 영상 제작 중...")

    for idx, img_path in enumerate(card_img_paths):
        out_path = os.path.join(SINGLE_CLIP_DIR, f'card_{idx+1:02d}_{now_str}.mp4')
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path,
            "-t", str(duration),
            "-vf", f"zoompan=z='min(zoom+0.001,1.05)':d={duration*25}:s={WIDTH}x{HEIGHT}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print(f"   - 카드 영상 ({idx+1}/{total_cards}) 저장 완료: {out_path}")
            video_clips.append(out_path)
        except subprocess.CalledProcessError as e:
            print(f"[오류] 카드 영상({idx+1}) 제작 실패(FFmpeg 문제 가능): {e.stderr}")
            continue
    return video_clips

def merge_videos(video_paths, out_path):
    """생성된 모든 비디오 클립을 하나로 합칩니다."""
    print("3. 모든 영상 클립 합치는 중...")
    list_file_path = os.path.join(BASE_DIR, "video_list.txt")
    with open(list_file_path, "w", encoding="utf-8") as f:
        for v_path in video_paths:
            f.write(f"file '{os.path.abspath(v_path)}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file_path, "-c", "copy", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 영상 합치기 완료: {out_path}")
    except subprocess.CalledProcessError as e:
        print(f"[오류] 영상 합치기 실패: {e.stderr}")
    finally:
        if os.path.exists(list_file_path):
            os.remove(list_file_path)

def add_background_music(video_path, bgm_path, out_path, total_duration):
    """영상에 배경음악을 추가합니다."""
    if not os.path.exists(bgm_path):
        print(f"[오류] 배경음악 파일 없음: {bgm_path}")
        # BGM 없이 파일 복사
        shutil.copy(video_path, out_path)
        return

    print("4. 배경음악 추가 중 (페이드인/아웃 적용)...")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", f"[1:a]volume=0.4,afade=t=in:st=0:d=1,afade=t=out:st={total_duration-1}:d=1[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 최종 영상 저장 완료: {out_path}")
    except subprocess.CalledProcessError as e:
        print(f"[오류] 배경음악 추가 실패: {e.stderr}")

def cleanup(temp_dirs, temp_files):
    """임시 파일 및 폴더를 정리합니다."""
    print("5. 임시 파일 정리 중...")
    time.sleep(1) # 파일 핸들이 해제될 때까지 잠시 대기
    for d in temp_dirs:
        if os.path.exists(d):
            for i in range(3):
                try:
                    shutil.rmtree(d)
                    print(f"   - 임시 폴더 삭제: {d}")
                    break
                except PermissionError:
                    print(f"[경고] 폴더 사용 중이거나 권한이 없어 삭제 실패: {d} (재시도 {i+1}/3)")
                    time.sleep(1)
                except Exception as e:
                    print(f"[경고] 임시 폴더 삭제 중 예외 발생: {d} ({e}) (재시도 {i+1}/3)")
                    time.sleep(1)
            else:
                print(f"[실패] 폴더 삭제 불가: {d} (수동 삭제 필요)")
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"   - 임시 파일 삭제: {f}")
            except Exception as e:
                print(f"[경고] 임시 파일 삭제 중 예외 발생: {f} ({e}) (수동 삭제 필요)")

if __name__ == "__main__":
    # 1. 인트로 영상 생성
    intro_clip = create_intro_video(INTRO_IMG_PATH, INTRO_CLIP_PATH, INTRO_DURATION)
    
    # 2. 카드 영상 생성
    card_clips = create_card_videos(card_images, CARD_DURATION)
    
    # 3. 모든 클립 목록 결합 (인트로 + 카드)
    all_clips = ([intro_clip] if intro_clip else []) + card_clips
    
    if all_clips:
        # 4. 클립 합치기
        merge_videos(all_clips, MERGED_CLIP_PATH)
        
        # 5. BGM 추가
        total_video_duration = (INTRO_DURATION if intro_clip else 0) + (len(card_clips) * CARD_DURATION)
        add_background_music(MERGED_CLIP_PATH, BGM_PATH, FINAL_VIDEO_PATH, total_video_duration)
        
        # 6. 임시 파일 정리
        cleanup(
            temp_dirs=[SINGLE_CLIP_DIR],
            temp_files=[MERGED_CLIP_PATH]
        )
        print(f"\n모든 작업 완료! 최종 영상은 다음 경로에 저장되었습니다:\n{FINAL_VIDEO_PATH}")
    else:
        print("[오류] 생성된 영상 클립이 없어 동영상 제작을 중단합니다.") 