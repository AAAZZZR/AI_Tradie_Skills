---
name: news-video-pipeline
description: >
  自動新聞短影片工作流。當使用者說「抓新聞」、「今日新聞」、「跑新聞影片」、
  「fetch news」、「generate video script」、「新聞分鏡」、「做影片」時觸發。
  流程：抓新聞 → AI 生成分鏡腳本 → 圖片生成 → TTS 配音 → FFmpeg 合成 → 上傳。
version: 2.0.0
metadata: {"openclaw": {"emoji": "🎬", "requires": {"bins": ["python3", "ffmpeg"]}, "primaryEnv": ""}}
---

# News Video Pipeline

自動抓取新聞 → 生成分鏡 → 配音 → 合成影片的端到端工作流。

## 架構

```
使用者指定主題
    │
    ▼
[Step 1] 抓新聞 ──────── fetch_news.py (本 skill)
    │
    ▼
[Step 2] 生成分鏡+文案 ─ Agent 直接生成 (本 skill)
    │                    ↘ 可呼叫外部 sub-skill: 文案生成
    ▼
[Step 3] 生成圖片 ────── 呼叫外部 sub-skill: 圖片生成模型
    │
    ▼
[Step 4] TTS 配音 ────── edge-tts (本 skill)
    │
    ▼
[Step 5] FFmpeg 合成 ─── generate_video.py (本 skill)
    │
    ▼
[Step 6] 上傳 ─────────── FB_Manager skill / 其他平台 skill
```

## Sub-Skill 依賴

本 skill 在特定步驟會呼叫外部 skill：

| 步驟 | 外部 Skill | 用途 | 狀態 |
|------|-----------|------|------|
| Step 3 | **圖片生成 skill** (TBD) | 根據 image_prompt 生成分鏡圖片 | ⬜ 待接入 |
| Step 6 | **FB_Manager** | Facebook 粉專發文/影片上傳 | ✅ 已就緒 |
| Step 2 | **文案生成 skill** (TBD) | 可選：更精緻的多語言文案 | ⬜ 待接入 |

當圖片生成 skill 未就緒時，fallback 使用 Pillow 文字卡片。

## RSS 來源

設定檔：`{baseDir}/config/sources.json`

目前來源：
- Hacker News（官方 RSS）
- DEV.to
- Lobsters
- OpenAI Blog
- Google AI Blog
- NVIDIA Blog
- HuggingFace Blog

可隨時新增/移除，修改 `sources.json` 即可。

## Step 1 — 抓新聞

```bash
python3 {baseDir}/scripts/fetch_news.py \
  --config {baseDir}/config/sources.json \
  --topic "AI" \
  --output {baseDir}/output/
```

- 零依賴（純 Python stdlib）
- 支援主題過濾（對應 `topic_keywords`）
- 輸出 `news_raw.json`

### 抓完後流程

1. 列出所有文章標題
2. Agent 根據標題主觀判斷價值，推薦精選
3. 使用者確認選擇後進入 Step 2

## Step 2 — AI 生成分鏡腳本

Agent 直接生成分鏡 JSON，不需呼叫外部 API。

### 分鏡 JSON 結構

```json
{
  "source": { "title": "...", "link": "..." },
  "en": {
    "title": "影片標題",
    "description": "影片描述",
    "hashtags": ["#tag1", "#tag2"],
    "slides": [
      {
        "id": 1,
        "duration_sec": 7,
        "headline": "畫面大標",
        "body_text": "副標",
        "narration": "旁白文案（配音用）",
        "image_prompt": "圖片生成 prompt（給 AI 圖片模型）",
        "background": "#1a1a2e",
        "text_color": "#FFFFFF"
      }
    ]
  },
  "zh": { ... }
}
```

### 分鏡規則

- 7 張 slides
- 第一張：震撼開場（問題或驚人事實）
- 最後一張：CTA
- 旁白語速：每秒約 4 個中文字（中文）/ 3 個單詞（英文）
- 每張 slide 包含 `image_prompt`，供圖片生成 skill 使用
- 中英文各一個完整版本

## Step 3 — 生成圖片

### 有圖片生成 skill 時

將每張 slide 的 `image_prompt` 傳給圖片生成 sub-skill，取回圖片存為：
```
output/video_XX/images/image_01.png
output/video_XX/images/image_02.png
...
```

### Fallback（無圖片 skill 時）

使用 Pillow 生成純色底 + 文字卡片，由 `generate_video.py` 內建處理。

## Step 4 — TTS 配音

使用 `edge-tts`（微軟免費 TTS，零 API key）。

| 語言 | Voice |
|------|-------|
| 中文 | zh-TW-HsiaoChenNeural |
| 英文 | en-US-GuyNeural |

由 `generate_video.py` 自動處理。

## Step 5 — FFmpeg 合成

```bash
python3 {baseDir}/scripts/generate_video.py \
  --storyboard {baseDir}/output/storyboard_01.json \
  --lang zh \
  --ratio 16x9 \
  --output {baseDir}/output/video_01_zh/
```

一條龍執行：讀取分鏡 → 生成音頻 → 生成圖片(fallback) → ffmpeg 合成。

支援比例：
- `16x9` — YouTube / Facebook
- `9x16` — TikTok / Instagram Reels

輸出：
```
output/video_XX/
├── audio/        ← mp3 旁白
├── images/       ← 分鏡圖片
├── clips/        ← 每張 slide 的片段
└── final_16x9_zh.mp4  ← 最終影片
```

## Step 6 — 上傳

### Facebook
使用 `FB_Manager` skill 上傳影片到粉專。

### 其他平台（待建置）
- YouTube：需 OAuth token
- TikTok：需開發者帳號
- Instagram Reels：需公開 URL host 影片

## 完整執行範例

```
使用者：「幫我做一支 AI 新聞影片」

Agent：
1. python3 fetch_news.py --topic "AI"
2. 列出精選新聞，使用者挑選
3. 生成分鏡 JSON（中英文 + image_prompt）
4. [呼叫圖片 skill] 生成分鏡圖片
5. python3 generate_video.py --storyboard ... --lang zh
6. 傳影片給使用者預覽
7. 確認後上傳 Facebook
```
