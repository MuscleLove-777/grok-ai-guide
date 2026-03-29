"""Grok AI完全攻略ガイド - ブログ固有設定"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

BLOG_NAME = "Grok AI完全攻略ガイド"
BLOG_DESCRIPTION = "イーロン・マスクのxAI Grokの使い方・最新モデル・X連携を毎日更新。Grok 4.20の実力を徹底解説。"
BLOG_URL = "https://musclelove-777.github.io/grok-ai-guide"
BLOG_TAGLINE = "xAI Grokを最大限活用するための日本語情報サイト"
BLOG_LANGUAGE = "ja"

GITHUB_REPO = "MuscleLove-777/grok-ai-guide"
GITHUB_BRANCH = "gh-pages"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

OUTPUT_DIR = BASE_DIR / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
SITE_DIR = OUTPUT_DIR / "site"
TOPICS_DIR = OUTPUT_DIR / "topics"

TARGET_CATEGORIES = [
    "Grok 使い方",
    "Grok 料金・プラン",
    "Grok vs ChatGPT",
    "Grok 最新ニュース",
    "Grok × X連携",
    "Grok API",
    "AI チャット比較",
    "Grok 活用事例",
]

THEME = {
    "primary": "#000000",
    "accent": "#1DA1F2",
    "gradient_start": "#000000",
    "gradient_end": "#1DA1F2",
    "dark_bg": "#000000",
    "dark_surface": "#16181c",
    "light_bg": "#f7f9f9",
    "light_surface": "#ffffff",
}

MAX_ARTICLE_LENGTH = 4000
ARTICLES_PER_DAY = 3
SCHEDULE_HOURS = [7, 12, 19]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

ENABLE_SEO_OPTIMIZATION = True
MIN_SEO_SCORE = 75
MIN_KEYWORD_DENSITY = 1.0
MAX_KEYWORD_DENSITY = 3.0
META_DESCRIPTION_LENGTH = 120
ENABLE_INTERNAL_LINKS = True

AFFILIATE_LINKS = {
    "X Premium": [
        {"service": "X Premium+", "url": "https://x.com/i/premium_sign_up", "description": "X Premium+に登録してGrokを使う"},
    ],
    "xAI API": [
        {"service": "xAI API", "url": "https://console.x.ai", "description": "xAI APIコンソール"},
    ],
    "SuperGrok": [
        {"service": "SuperGrok", "url": "https://x.com/i/grok", "description": "SuperGrokを試す"},
    ],
    "オンライン講座": [
        {"service": "Udemy", "url": "https://www.udemy.com", "description": "UdemyでAI講座を探す"},
    ],
    "書籍": [
        {"service": "Amazon", "url": "https://www.amazon.co.jp", "description": "AmazonでAI関連書籍を探す"},
        {"service": "楽天ブックス", "url": "https://www.rakuten.co.jp", "description": "楽天でAI関連書籍を探す"},
    ],
}
AFFILIATE_TAG = "musclelove07-22"

ADSENSE_CLIENT_ID = os.environ.get("ADSENSE_CLIENT_ID", "")
ADSENSE_ENABLED = bool(ADSENSE_CLIENT_ID)
DASHBOARD_PORT = 8099
