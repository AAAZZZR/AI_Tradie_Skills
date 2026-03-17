#!/usr/bin/env python3
"""
一條龍影片生成：讀取 storyboard JSON → 生成圖片(nano-banana-pro) → 生成音頻(edge-tts) → ffmpeg 合成
用法: python3 generate_video.py --storyboard ../output/storyboard_01.json --lang zh --output ../output/video_01/
"""
import asyncio
import json
import os
import subprocess
import sys
import argparse
from pathlib import Path


# ── 設定 ──────────────────────────────────────────────

VOICE_MAP = {
    "zh": "zh-TW-HsiaoChenNeural",
    "en": "en-US-GuyNeural",
}

NANO_BANANA_SCRIPT = "/app/skills/nano-banana-pro/scripts/generate_image.py"

ASPECT_RATIO_MAP = {
    "16x9": "16:9",
    "9x16": "9:16",
}


# ── 圖片生成（nano-banana-pro）────────────────────────

def generate_images_ai(slides, img_dir, ratio="16x9"):
    """使用 nano-banana-pro (Gemini) 生成分鏡圖片"""
    img_dir.mkdir(parents=True, exist_ok=True)
    aspect = ASPECT_RATIO_MAP.get(ratio, "16:9")
    
    for slide in slides:
        prompt = slide.get("image_prompt", "")
        if not prompt:
            # fallback: 用 headline + body_text 組合
            prompt = f"{slide.get('headline', '')}. {slide.get('body_text', '')}. Dark cinematic style, digital illustration"
        
        filename = f"image_{slide['id']:02d}.png"
        out_path = img_dir / filename
        
        cmd = [
            "uv", "run", NANO_BANANA_SCRIPT,
            "--prompt", prompt,
            "--filename", str(out_path),
            "--resolution", "1K",
            "--aspect-ratio", aspect
        ]
        
        print(f"  🖼️ Slide {slide['id']}: 生成中...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and out_path.exists():
                print(f"     ✅ {filename}")
            else:
                print(f"     ❌ 失敗: {result.stderr[:200] if result.stderr else 'unknown error'}")
                # fallback to pillow
                print(f"     ⚠️ 使用 Pillow fallback")
                generate_image_fallback(slide, img_dir, ratio)
        except subprocess.TimeoutExpired:
            print(f"     ❌ 超時，使用 Pillow fallback")
            generate_image_fallback(slide, img_dir, ratio)


# ── Pillow Fallback ──────────────────────────────────

def generate_image_fallback(slide, img_dir, ratio="16x9"):
    """Pillow 文字卡片 fallback"""
    from PIL import Image, ImageDraw, ImageFont
    
    SIZES = {"16x9": (1920, 1080), "9x16": (1080, 1920)}
    FONT_PATHS = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    w, h = SIZES.get(ratio, (1920, 1080))
    bg_hex = slide.get("background", "#1a1a2e").lstrip("#")
    bg = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
    tc_hex = slide.get("text_color", "#FFFFFF").lstrip("#")
    text_color = tuple(int(tc_hex[i:i+2], 16) for i in (0, 2, 4))
    
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    
    # 找字型
    font = ImageFont.load_default()
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size=int(h * 0.065))
                break
            except:
                continue
    
    headline = slide.get("headline", "")
    bbox = draw.textbbox((0, 0), headline, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, h * 0.35), headline, font=font, fill=text_color)
    
    out_path = img_dir / f"image_{slide['id']:02d}.png"
    img.save(out_path, "PNG")


# ── TTS ───────────────────────────────────────────────

async def generate_audio(slides, lang, audio_dir):
    """使用 edge-tts 生成旁白音頻"""
    import edge_tts
    
    voice = VOICE_MAP.get(lang, VOICE_MAP["en"])
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    for slide in slides:
        narration = slide.get("narration", "")
        if not narration:
            continue
        
        out_path = audio_dir / f"audio_{slide['id']:02d}.mp3"
        communicate = edge_tts.Communicate(narration, voice, rate="+5%")
        await communicate.save(str(out_path))
        print(f"  🎙️ Slide {slide['id']}: {out_path.name}")
    
    return True


# ── FFmpeg 合成 ──────────────────────────────────────

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except:
        return 5.0


def make_clip(image_path, audio_path, clip_path):
    duration = get_audio_duration(audio_path)
    fade_out_start = max(0, duration - 0.5)
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration + 0.3:.2f}",
        "-shortest",
        "-vf", f"fade=t=in:st=0:d=0.3,fade=t=out:st={fade_out_start:.2f}:d=0.5",
        str(clip_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return duration


def concat_clips(clips, output_path):
    list_file = str(output_path).replace(".mp4", "_list.txt")
    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(list_file)


# ── 主流程 ───────────────────────────────────────────

def run(storyboard_path, lang, output_dir, ratio="16x9"):
    with open(storyboard_path, encoding="utf-8") as f:
        data = json.load(f)
    
    sb = data.get(lang, data.get("en"))
    slides = sb["slides"]
    title = sb.get("title", "untitled")
    
    out = Path(output_dir)
    audio_dir = out / "audio"
    img_dir = out / "images"
    clip_dir = out / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🎬 生成影片：{title}")
    print(f"   語言: {lang} | 比例: {ratio} | Slides: {len(slides)}")
    print("=" * 50)
    
    # Step 1: AI 圖片生成
    print(f"\n🖼️ 生成圖片 (nano-banana-pro, {ratio})...")
    generate_images_ai(slides, img_dir, ratio)
    
    # Step 2: TTS 配音
    print("\n🎙️ 生成配音 (edge-tts)...")
    asyncio.run(generate_audio(slides, lang, audio_dir))
    
    # Step 3: 合成每張 clip
    print("\n🎞️ 合成片段 (ffmpeg)...")
    clips = []
    total_dur = 0
    for slide in slides:
        sid = slide["id"]
        img_path = img_dir / f"image_{sid:02d}.png"
        audio_path = audio_dir / f"audio_{sid:02d}.mp3"
        clip_path = clip_dir / f"clip_{sid:02d}.mp4"
        
        if not img_path.exists() or not audio_path.exists():
            print(f"  ⚠️ 跳過 Slide {sid}")
            continue
        
        dur = make_clip(img_path, audio_path, clip_path)
        clips.append(str(clip_path))
        total_dur += dur
        print(f"  🎬 clip_{sid:02d}.mp4 ({dur:.1f}s)")
    
    # Step 4: 串接
    print("\n📦 串接最終影片...")
    final_path = out / f"final_{ratio}_{lang}.mp4"
    concat_clips(clips, final_path)
    
    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    print(f"\n✅ 完成！")
    print(f"   檔案: {final_path}")
    print(f"   時長: {total_dur:.1f}s")
    print(f"   大小: {size_mb:.1f} MB")
    
    return str(final_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--lang", default="zh", choices=["zh", "en"])
    parser.add_argument("--ratio", default="16x9", choices=["16x9", "9x16"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    run(args.storyboard, args.lang, args.output, args.ratio)
