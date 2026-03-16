#!/usr/bin/env python3
"""
Step 1: 抓新聞
用法: python3 fetch_news.py --config ../config/sources.json --topic "AI" --output ../output/
"""
import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from xml.etree import ElementTree as ET
import re
import email.utils


def parse_date(date_str: str) -> datetime:
    """嘗試多種日期格式解析"""
    if not date_str:
        return datetime.now(timezone.utc)
    
    # RFC 2822 (RSS standard)
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except:
        pass
    
    # ISO 8601
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    
    return datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    """移除 HTML 標籤"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def fetch_rss(feed_url: str, max_age_hours: int = 48) -> list:
    """原生 XML 解析 RSS/Atom feed"""
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    try:
        req = Request(feed_url, headers={'User-Agent': 'Mozilla/5.0 NewsBot/1.0'})
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
        
        root = ET.fromstring(data)
        
        # 偵測 feed 名稱
        feed_title = "Unknown"
        # RSS 2.0
        channel = root.find('./channel')
        if channel is not None:
            ft = channel.find('title')
            if ft is not None:
                feed_title = ft.text or "Unknown"
        # Atom
        elif root.tag.endswith('}feed') or root.tag == 'feed':
            ft = root.find('{http://www.w3.org/2005/Atom}title')
            if ft is not None:
                feed_title = ft.text or "Unknown"
        
        # RSS 2.0 items
        items = root.findall('.//item')
        # Atom entries
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            items = root.findall('.//atom:entry', ns)
            if not items:
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        for item in items:
            # 取標題
            title = None
            for tag in ['title', '{http://www.w3.org/2005/Atom}title']:
                el = item.find(tag)
                if el is not None and el.text:
                    title = el.text.strip()
                    break
            if not title:
                continue
            
            # 取連結
            link = ""
            link_el = item.find('link')
            if link_el is not None:
                link = link_el.text or link_el.get('href', '') or ""
            if not link:
                link_el = item.find('{http://www.w3.org/2005/Atom}link')
                if link_el is not None:
                    link = link_el.get('href', '')
            
            # 取摘要
            summary = ""
            for tag in ['description', 'summary', '{http://www.w3.org/2005/Atom}summary',
                        '{http://www.w3.org/2005/Atom}content']:
                el = item.find(tag)
                if el is not None and el.text:
                    summary = strip_html(el.text)
                    break
            
            # 取日期
            pub_date = ""
            for tag in ['pubDate', 'published', '{http://www.w3.org/2005/Atom}published',
                        '{http://www.w3.org/2005/Atom}updated', 'dc:date',
                        '{http://purl.org/dc/elements/1.1/}date']:
                el = item.find(tag)
                if el is not None and el.text:
                    pub_date = el.text.strip()
                    break
            
            published = parse_date(pub_date)
            if published < cutoff:
                continue
            
            articles.append({
                "title": title,
                "summary": summary[:500],
                "link": link.strip(),
                "published": published.isoformat(),
                "source": feed_title
            })
    
    except Exception as e:
        print(f"  ❌ RSS 失敗: {feed_url} → {e}", file=sys.stderr)
    
    return articles


def match_topic(article: dict, topic: str, keywords: dict) -> bool:
    """檢查文章是否符合指定主題"""
    if not topic:
        return True
    
    topic_keys = keywords.get(topic, [topic])
    text = f"{article['title']} {article['summary']}".lower()
    
    return any(kw.lower() in text for kw in topic_keys)


def run(config_path: str, topic: str, output_dir: str):
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    
    max_age = config.get("max_age_hours", 48)
    max_articles = config.get("max_articles_per_run", 10)
    keywords = config.get("topic_keywords", {})
    
    all_articles = []
    
    # 抓所有 RSS feeds
    feeds = config.get("rss_feeds", {})
    for category, urls in feeds.items():
        for url in urls:
            print(f"  📡 抓取: {url[:60]}...")
            articles = fetch_rss(url, max_age)
            all_articles.extend(articles)
            if articles:
                print(f"     ✅ {len(articles)} 篇")
            else:
                print(f"     ⚠️ 0 篇（或全部超過 {max_age}h）")
    
    # 過濾主題
    if topic:
        filtered = [a for a in all_articles if match_topic(a, topic, keywords)]
        print(f"\n🔍 主題過濾「{topic}」: {len(all_articles)} → {len(filtered)} 篇")
    else:
        filtered = all_articles
    
    # 去重
    seen = set()
    unique = []
    for a in filtered:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    
    # 按時間排序（最新的在前）
    unique.sort(key=lambda x: x["published"], reverse=True)
    
    # 取前 N 篇
    final = unique[:max_articles]
    
    # 輸出
    today = datetime.now().strftime("%Y%m%d")
    topic_slug = topic.replace(" ", "_") if topic else "all"
    out_dir = Path(output_dir) / f"{today}_{topic_slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        "topic": topic or "all",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_found": len(all_articles),
        "after_filter": len(filtered),
        "final_count": len(final),
        "articles": final
    }
    
    out_path = out_dir / "news_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n📰 結果：共 {len(final)} 篇 → {out_path}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取新聞 RSS")
    parser.add_argument("--config", required=True, help="sources.json 路徑")
    parser.add_argument("--topic", default="", help="主題過濾（對應 topic_keywords）")
    parser.add_argument("--output", default="./output", help="輸出目錄")
    args = parser.parse_args()
    
    print(f"🦞 新聞抓取 — 主題: {args.topic or '全部'}")
    print("=" * 50)
    run(args.config, args.topic, args.output)
