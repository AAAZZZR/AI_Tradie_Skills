---
name: video-generator
description: >
  將結構化語料生成短影片。當使用者說「做影片」、「生成影片」、「出片」、
  「generate video」、「跑影片」時觸發。
  輸入語料 → 生成分鏡 → HTML 海報截圖 → TTS 配音 → FFmpeg 合成。
  支援深色/淺色主題，中英文雙語。
version: 1.0.0
metadata: {"openclaw": {"emoji": "🎬", "requires": {"bins": ["python3", "ffmpeg", "playwright"]}}}
---

# Video Generator

將結構化語料（來自 News_Fetcher 或任何來源）生成短影片。

## 架構

```
結構化語料 JSON（或使用者直接給內容）
    │
    ▼
[Step 1] 生成分鏡 ──── Agent 根據語料生成分鏡 JSON
    │
    ▼
[Step 2] HTML 海報 ──── 模板 + Playwright 截圖
    │
    ▼
[Step 3] TTS 配音 ──── edge-tts（免費）
    │
    ▼
[Step 4] FFmpeg 合成 ── 圖片 + 音頻 → 影片
    │
    ▼
輸出 final.mp4
```

## 輸入格式

接受 News_Fetcher 的 `structured_article.json`，或任何包含以下結構的內容：

```json
{
  "digest": {
    "title": "標題",
    "summary": "摘要",
    "sections": [
      {
        "heading": "段落標題",
        "paragraph": "描述",
        "bullet_points": ["重點一", "重點二"]
      }
    ],
    "takeaway": "結論",
    "tags": ["tag1", "tag2"]
  }
}
```

也可以直接給純文字，Agent 會自行結構化後生成分鏡。

## Step 1 — 生成分鏡

Agent 根據語料生成分鏡 JSON，中英文各一版：

```json
{
  "en": {
    "title": "Video Title",
    "slides": [
      {
        "id": 1,
        "duration_sec": 7,
        "headline": "Slide Title",
        "body_text": "Subtitle or key point",
        "bullet_points": ["Point 1", "Point 2"],
        "narration": "Voiceover script",
        "theme": "dark",
        "accent_color": "#6366f1"
      }
    ]
  },
  "zh": { ... }
}
```

### 分鏡規則

- 5-7 張 slides
- 第一張：hook（問題或驚人事實）
- 最後一張：CTA / takeaway
- 每張有 headline + body_text + bullet_points（條列重點）
- narration 是配音稿，語速：中文每秒 4 字 / 英文每秒 3 詞
- theme: `"dark"` 或 `"light"`
- 英文影片配英文海報，中文配中文海報

## Step 2 — HTML 海報生成

使用 HTML 模板 + Playwright 截圖生成海報圖片。

### 模板主題

| 主題 | 檔案 | 風格 |
|------|------|------|
| dark | `{baseDir}/templates/dark.html` | 深色漸層背景、亮色文字、科技感 |
| light | `{baseDir}/templates/light.html` | 淺色背景、深色文字、清爽專業 |

### 海報結構

```
┌──────────────────────────────────────┐
│ [標籤] AI SECURITY                   │
│                                      │
│ 大標題                               │
│ 副標題                               │
│                                      │
│ • 重點一                             │
│ • 重點二                             │
│ • 重點三                             │
│                                      │
│ 來源 · 日期              01 / 07     │
└──────────────────────────────────────┘
```

### 生成方式

```python
# 讀取模板 → 替換內容 → Playwright 截圖
page.goto(template_html)
page.screenshot(path="slide_01.png")
```

## Step 3 — TTS 配音

使用 edge-tts（微軟免費 TTS）。

| 語言 | Voice |
|------|-------|
| 中文 | zh-TW-HsiaoChenNeural |
| 英文 | en-US-GuyNeural |

## Step 4 — FFmpeg 合成

```bash
python3 {baseDir}/scripts/generate_video.py \
  --storyboard storyboard.json \
  --lang zh \
  --ratio 16x9 \
  --theme dark \
  --output ./output/
```

支援比例：
- `16x9` — YouTube / Facebook
- `9x16` — TikTok / Instagram Reels

## 主題切換

在分鏡 JSON 中設定 `theme` 欄位：
- 整部影片統一主題：在頂層設定
- 每張 slide 不同：在 slide 層級設定

## 與其他 Skill 的關係

| 上游 | 用途 |
|------|------|
| **News_Fetcher** | 提供結構化新聞語料 |
| 使用者直接輸入 | 任何主題的內容 |

| 下游 | 用途 |
|------|------|
| **FB_Manager** | 上傳影片到 Facebook |
| YouTube / TikTok | 待建置 |

## 注意事項

- HTML 模板生成圖片零 API 費用
- edge-tts 免費
- 整個 pipeline 唯一的費用是 OpenClaw 的 LLM token（生成分鏡文案）
