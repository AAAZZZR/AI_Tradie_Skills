#!/usr/bin/env bash
# 用 headless Chrome 把 HTML 海報截成 PNG。
# 用法：render.sh poster.html poster.png [寬] [高]（預設 1080x1350，FB 動態牆的 4:5）
set -euo pipefail

html="$1"
out="$2"
width="${3:-1080}"
height="${4:-1350}"
cache_dir="$HOME/.cache/ai-tradie-chrome"

find_chrome() {
  if [[ -n "${CHROME_PATH:-}" ]]; then
    echo "$CHROME_PATH"
    return
  fi
  for name in google-chrome google-chrome-stable chromium chromium-browser chrome-headless-shell; do
    if command -v "$name" >/dev/null 2>&1; then
      command -v "$name"
      return
    fi
  done
  local cached
  cached=$(find "$cache_dir" -type f -name chrome-headless-shell 2>/dev/null | head -1 || true)
  if [[ -n "$cached" ]]; then
    echo "$cached"
    return
  fi
  # 機器上沒有 Chrome：從 Chrome for Testing（storage.googleapis.com）下載 headless shell
  npx -y @puppeteer/browsers install chrome-headless-shell@stable --path "$cache_dir" >&2
  find "$cache_dir" -type f -name chrome-headless-shell | head -1
}

to_abs() {
  local path
  path="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  # Windows 的 Git Bash 要轉成 C:/... 給 Chrome 用
  if command -v cygpath >/dev/null 2>&1; then
    path=$(cygpath -m "$path")
  fi
  echo "$path"
}

chrome=$(find_chrome)
if [[ -z "$chrome" ]]; then
  echo "找不到 Chrome，也下載不到" >&2
  exit 1
fi

abs_html=$(to_abs "$html")
abs_out=$(to_abs "$out")
rm -f "$abs_out"

"$chrome" --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size="$width,$height" --force-device-scale-factor=1 \
  --virtual-time-budget=8000 \
  --screenshot="$abs_out" "file:///${abs_html#/}" >/dev/null 2>&1

if [[ ! -s "$abs_out" ]]; then
  echo "渲染失敗：$abs_out 沒有產生" >&2
  exit 1
fi
echo "$abs_out"
