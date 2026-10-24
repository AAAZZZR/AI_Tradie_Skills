#!/usr/bin/env bash
# AI Tradie 粉專的 Graph API 小工具。
# 雲端環境裡粉專權杖存成 network secret：proxy 會替送往 graph.facebook.com 的請求加上
# "Authorization: Bearer <token>"，這支程式碰不到 token。本機測試時改用環境變數 FB_TOKEN。
set -euo pipefail

PAGE_ID="985495464653087"
API="https://graph.facebook.com/v21.0"

auth=()
if [[ -n "${FB_TOKEN:-}" ]]; then
  auth=(-H "Authorization: Bearer ${FB_TOKEN}")
fi

call() {
  curl -sS --fail-with-body "${auth[@]}" "$@"
  echo
}

usage() {
  cat >&2 <<'EOF'
用法：
  fb.sh recent [N]                    最近 N 篇貼文（預設 15）：id、時間、內文、連結
  fb.sh stats <post_id>               一篇貼文的讚、留言、分享、觀看、點擊
  fb.sh page                          粉專名稱與粉絲數
  fb.sh post <caption.txt> <image> [ISO 時間]   發圖文（caption 檔的內容就是貼文內文；給時間就排程）
  fb.sh scheduled                     列出已排程、還沒發出的貼文
  fb.sh post-text <caption.txt>       發純文字
  fb.sh post-video <caption.txt> <video.mp4> [標題]   發影片
  fb.sh video <video_id>              一支影片的處理狀態與連結
EOF
}

case "${1:-}" in
  recent)
    call -G "$API/$PAGE_ID/posts" \
      --data-urlencode "fields=id,created_time,message,permalink_url" \
      --data-urlencode "limit=${2:-15}"
    ;;
  stats)
    [[ -n "${2:-}" ]] || { usage; exit 1; }
    call -G "$API/$2" \
      --data-urlencode "fields=created_time,reactions.summary(total_count).limit(0),comments.summary(true).limit(0),shares"
    call -G "$API/$2/insights" \
      --data-urlencode "metric=post_media_view,post_total_media_view_unique,post_clicks"
    ;;
  page)
    call -G "$API/$PAGE_ID" --data-urlencode "fields=name,fan_count,followers_count"
    ;;
  post)
    [[ -f "${2:-}" && -f "${3:-}" ]] || { usage; exit 1; }
    sched=()
    if [[ -n "${4:-}" ]]; then
      # 排程：FB 要求至少 10 分鐘後、75 天內；時間用 ISO 8601（例如 2026-10-25T19:30:00+10:00）
      sched=(-F "published=false" -F "scheduled_publish_time=$(date -d "$4" +%s)")
    fi
    call -X POST "$API/$PAGE_ID/photos" -F "message=<$2" -F "source=@$3" "${sched[@]}"
    ;;
  scheduled)
    call -G "$API/$PAGE_ID/scheduled_posts" --data-urlencode "fields=id,scheduled_publish_time,message"
    ;;
  post-text)
    [[ -f "${2:-}" ]] || { usage; exit 1; }
    call -X POST "$API/$PAGE_ID/feed" --data-urlencode "message@$2"
    ;;
  post-video)
    # 影片要傳到 graph-video.facebook.com，不是 graph.facebook.com
    [[ -f "${2:-}" && -f "${3:-}" ]] || { usage; exit 1; }
    call -X POST "https://graph-video.facebook.com/v21.0/$PAGE_ID/videos" \
      -F "description=<$2" -F "title=${4:-}" -F "source=@$3"
    ;;
  video)
    [[ -n "${2:-}" ]] || { usage; exit 1; }
    call -G "$API/$2" --data-urlencode "fields=id,title,permalink_url,published,status,created_time"
    ;;
  *)
    usage
    exit 1
    ;;
esac
