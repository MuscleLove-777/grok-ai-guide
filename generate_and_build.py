#!/usr/bin/env python3
"""GitHub Actions用一括実行スクリプト

キーワード選定 → 記事生成 → SEO最適化 → サイトビルド を一括実行する。
JSON-LD構造化データ（BlogPosting / FAQPage / BreadcrumbList）対応。
リトライ機能付き。
"""
import sys
import os
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

# blog_engineへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def repair_json(text: str) -> dict:
    """壊れたJSONを修復して辞書に変換する"""
    # コードブロック除去
    if "```" in text:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

    # { } の範囲を抽出
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 壊れたcontent中の改行やクォートを修復
    # content フィールドの値を正規表現で抽出して修復
    try:
        # title, meta_description, tags, slug, faq を先に抽出
        title_m = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        meta_m = re.search(r'"meta_description"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        slug_m = re.search(r'"slug"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        tags_m = re.search(r'"tags"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        faq_m = re.search(r'"faq"\s*:\s*\[(.*)\]\s*\}?\s*$', text, re.DOTALL)

        # content は "content": "..." のパターンで最長マッチ
        content_m = re.search(
            r'"content"\s*:\s*"(.*?)"\s*,\s*"meta_description"', text, re.DOTALL
        )

        if title_m and content_m and meta_m and slug_m and tags_m:
            tags_str = tags_m.group(1).strip()
            tags = [t.strip().strip('"') for t in tags_str.split(",") if t.strip()]

            result = {
                "title": title_m.group(1),
                "content": content_m.group(1),
                "meta_description": meta_m.group(1),
                "tags": tags,
                "slug": slug_m.group(1),
            }

            if faq_m:
                try:
                    faq_text = "[" + faq_m.group(1) + "]"
                    result["faq"] = json.loads(faq_text)
                except Exception:
                    result["faq"] = []

            return result
    except Exception as e:
        logger.warning("JSON修復に失敗: %s", e)

    raise ValueError("JSONの修復に失敗しました")


def generate_article_with_retry(config, keyword, category, prompts):
    """リトライ機能付き記事生成"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    articles_dir = Path(config.BASE_DIR) / "output" / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    if prompts and hasattr(prompts, "build_article_prompt"):
        prompt = prompts.build_article_prompt(keyword, category, config)
    else:
        prompt = f"キーワード「{keyword}」に関する記事をJSON形式で生成してください。"

    # JSON出力のスキーマ定義
    article_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "meta_description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "slug": {"type": "string"},
            "faq": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                    },
                    "required": ["question", "answer"],
                },
            },
        },
        "required": ["title", "content", "meta_description", "tags", "slug"],
    }

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("記事生成 試行 %d/%d", attempt, MAX_RETRIES)
        try:
            gen_config = types.GenerateContentConfig(
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=article_schema,
            )
            response = client.models.generate_content(
                model=config.GEMINI_MODEL, contents=prompt, config=gen_config,
            )
            response_text = response.text
            logger.info("APIレスポンス受信（%d文字）", len(response_text))

            logger.info("レスポンス先頭300文字: %s", response_text[:300])

            try:
                article = json.loads(response_text)
            except json.JSONDecodeError as je:
                logger.warning("標準パース失敗 (%s)、修復を試行", je)
                article = repair_json(response_text)

            # リストの場合は最初の要素
            if isinstance(article, list):
                article = article[0]

            # 必須フィールドチェック
            required = ["title", "content", "meta_description", "tags", "slug"]
            missing = [f for f in required if f not in article]
            if missing:
                raise ValueError(f"必須フィールドが不足: {missing}")

            if not isinstance(article["tags"], list):
                article["tags"] = [article["tags"]]

            article["slug"] = re.sub(
                r"[^a-z0-9-]", "", article["slug"].lower().replace(" ", "-")
            )

            # 保存
            article["keyword"] = keyword
            article["category"] = category
            article["generated_at"] = datetime.now().isoformat()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = article.get("slug", "untitled")
            filename = f"{timestamp}_{slug}.json"
            file_path = articles_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2)

            article["file_path"] = str(file_path)
            logger.info("記事生成成功: %s", article["title"])
            return article

        except Exception as e:
            logger.warning("試行 %d 失敗: %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(5)
            else:
                raise


def run(config, prompts=None):
    """メイン処理: キーワード選定 → 記事生成 → SEO最適化 → サイトビルド"""
    logger.info("=== %s 自動生成開始 ===", config.BLOG_NAME)
    start_time = datetime.now()

    # ステップ1: キーワード選定
    logger.info("ステップ1: キーワード選定")
    try:
        from google import genai

        if not config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY が設定されていません")
            sys.exit(1)

        client = genai.Client(api_key=config.GEMINI_API_KEY)

        if prompts and hasattr(prompts, "build_keyword_prompt"):
            prompt = prompts.build_keyword_prompt(config)
        else:
            categories_text = "\n".join(f"- {cat}" for cat in config.TARGET_CATEGORIES)
            prompt = (
                f"{config.BLOG_NAME}用のキーワードを選定してください。\n\n"
                "以下のカテゴリから1つ選び、そのカテゴリで今注目されている"
                "トピック・キーワードを1つ提案してください。\n\n"
                f"カテゴリ一覧:\n{categories_text}\n\n"
                "以下の形式でJSON形式のみで回答してください（説明不要）:\n"
                '{"category": "カテゴリ名", "keyword": "キーワード"}'
            )

        from google.genai import types
        kw_schema = {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "keyword": {"type": "string"},
            },
            "required": ["category", "keyword"],
        }
        kw_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=kw_schema,
        )
        response = client.models.generate_content(
            model=config.GEMINI_MODEL, contents=prompt, config=kw_config,
        )
        response_text = response.text.strip()
        logger.info("API応答: %s", response_text[:500])

        data = json.loads(response_text)
        # リストで返ってきた場合は最初の要素を使用
        if isinstance(data, list):
            data = data[0]
        category = data["category"]
        keyword = data["keyword"]
        logger.info("選定結果 - カテゴリ: %s, キーワード: %s", category, keyword)

    except Exception as e:
        logger.error("キーワード選定に失敗: %s", e)
        sys.exit(1)

    # ステップ2: 記事生成（リトライ機能付き）
    logger.info("ステップ2: 記事生成（リトライ付き）")
    try:
        from seo_optimizer import GrokSEOOptimizer

        article = generate_article_with_retry(config, keyword, category, prompts)
        logger.info("記事生成完了: %s", article.get("title", "不明"))

        optimizer = GrokSEOOptimizer(config)
        seo_result = optimizer.check_seo_score(article)
        article["seo_score"] = seo_result.get("total_score", 0)
        logger.info("SEOスコア: %d/100", article["seo_score"])

        # JSON-LD構造化データを記事に追加
        jsonld_scripts = optimizer.generate_all_jsonld(article)
        article["jsonld"] = jsonld_scripts
        logger.info("JSON-LD構造化データ: %d件生成", len(jsonld_scripts))

    except Exception as e:
        logger.error("記事生成に失敗: %s", e)
        sys.exit(1)

    # ステップ2.5: アフィリエイトリンク挿入
    logger.info("ステップ2.5: アフィリエイトリンク挿入")
    try:
        from blog_engine.affiliate import AffiliateManager
        affiliate_mgr = AffiliateManager(config)
        article = affiliate_mgr.insert_affiliate_links(article)
        logger.info("アフィリエイトリンク: %d件挿入", article.get("affiliate_count", 0))
    except Exception as aff_err:
        logger.warning("アフィリエイトリンク挿入をスキップ: %s", aff_err)

    # ステップ2.7: 記事JSONを再保存（SEOスコア・JSON-LD追加後）
    try:
        file_path = article.get("file_path")
        if file_path:
            save_data = {k: v for k, v in article.items() if k != "file_path"}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            logger.info("記事を再保存しました: %s", file_path)
    except Exception as save_err:
        logger.warning("記事の再保存をスキップ: %s", save_err)

    # ステップ3: サイトビルド
    logger.info("ステップ3: サイトビルド")
    try:
        from site_generator import GrokSiteGenerator
        site_gen = GrokSiteGenerator(config)
        site_gen.build_site()
        logger.info("サイトビルド完了")
    except Exception as e:
        logger.error("サイトビルドに失敗: %s", e)
        sys.exit(1)

    # 完了
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=== 自動生成完了（%.1f秒） ===", duration)
    logger.info("  カテゴリ: %s", category)
    logger.info("  キーワード: %s", keyword)
    logger.info("  タイトル: %s", article.get("title", "不明"))
    logger.info("  SEOスコア: %d/100", article.get("seo_score", 0))


if __name__ == "__main__":
    # 直接実行時
    sys.path.insert(0, os.path.dirname(__file__))
    import config
    import prompts
    run(config, prompts)
