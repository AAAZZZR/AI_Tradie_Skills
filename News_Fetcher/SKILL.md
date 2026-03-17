---
name: news-fetcher
description: >
  抓取新聞並消化成結構化文章。當使用者說「抓新聞」、「今日新聞」、「fetch news」、
  「有什麼新聞」、「最新消息」時觸發。
  抓取 RSS → Agent 篩選有價值的文章 → 消化成段落式文章（含條列重點）。
  輸出可直接作為 Video_Generator 或其他 skill 的語料輸入。
version: 1.0.0
metadata: {"openclaw": {"emoji": "📰", "requires": {"bins": ["python3"]}}}
---

# News Fetcher

抓取新聞 + 自動消化成結構化語料。

## 流程

```
使用者指定主題
    │
    ▼
[Step 1] 抓取 RSS ──── fetch_news.py
    │
    ▼
[Step 2] Agent 篩選 ── 根據標題主觀判斷價值，推薦精選
    │
    ▼
[Step 3] 消化文章 ──── Agent 將選定文章轉為結構化語料
    │
    ▼
輸出 structured_article.json → 可餵給 Video_Generator 或其他 skill
```

## Step 1 — 抓取 RSS

```bash
python3 {baseDir}/scripts/fetch_news.py \
  --config {baseDir}/config/sources.json \
  --topic "AI" \
  --output {baseDir}/output/
```

- 零依賴（純 Python stdlib）
- 支援主題過濾（對應 `topic_keywords`）
- 輸出 `news_raw.json`

## Step 2 — Agent 篩選

抓完後：
1. 列出所有文章標題
2. Agent 根據標題主觀判斷價值（話題性、深度、觀眾興趣）
3. 推薦精選 3-5 篇，使用者確認

## Step 3 — 消化成結構化語料

Agent 將選定的文章消化成以下格式：

### 輸出格式

```json
{
  "source": {
    "title": "原文標題",
    "link": "https://...",
    "source": "來源",
    "published": "ISO 8601"
  },
  "digest": {
    "title": "消化後的標題（吸引人、15字以內）",
    "summary": "一句話摘要（30字以內）",
    "sections": [
      {
        "heading": "段落標題",
        "paragraph": "這段在說什麼的自然語言描述，2-3句話。",
        "bullet_points": [
          "重點一：具體的事實或數據",
          "重點二：為什麼這很重要",
          "重點三：影響或後續發展"
        ]
      }
    ],
    "takeaway": "一句話結論 / CTA",
    "tags": ["AI", "security", "agents"]
  }
}
```

### 消化規則

- 3-5 個 sections
- 每個 section 有 heading + paragraph + 2-4 個 bullet_points
- paragraph 用自然口語，不要學術腔
- bullet_points 是精煉的重點，方便之後直接變分鏡文案
- 第一個 section 必須是「為什麼這很重要」（hook）
- 最後一個 section 是「so what / 你該怎麼辦」
- takeaway 是一句有力的結尾

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

可隨時新增/移除。

## 與其他 Skill 的關係

輸出的 `structured_article.json` 可以作為：
- **Video_Generator** 的輸入 → 生成影片
- **FB_Manager** 的輸入 → 生成 FB 貼文
- 任何需要結構化語料的 skill
