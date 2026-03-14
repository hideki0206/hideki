import asyncio
import json
import re
import base64
import os
from playwright.async_api import async_playwright

THREADS_SESSION = os.environ.get("THREADS_SESSION", "")


def get_browser_context(playwright, headless=True):
    """セッション付きブラウザコンテキストを返す"""
    browser = playwright.chromium.launch(headless=headless)
    kwargs = dict(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    if THREADS_SESSION:
        kwargs["storage_state"] = json.loads(base64.b64decode(THREADS_SESSION).decode())
    return browser, browser.new_context(**kwargs)


async def scrape_threads_account(username: str, limit: int = 20) -> list[dict]:
    """Threadsアカウントの投稿をスクレイピング"""
    username = username.lstrip("@")
    url = f"https://www.threads.com/@{username}"
    posts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # スクロールして投稿を読み込む
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # 投稿テキストを取得
            post_elements = await page.query_selector_all('[data-pressable-container="true"]')

            for el in post_elements[:limit]:
                try:
                    text_el = await el.query_selector("span")
                    if text_el:
                        text = await text_el.inner_text()
                        if text and len(text) > 10:
                            posts.append({
                                "account": username,
                                "text": text.strip(),
                            })
                except Exception:
                    continue

        except Exception as e:
            print(f"Error scraping {username}: {e}")
        finally:
            await browser.close()

    return posts


async def scrape_by_keyword(keyword: str, limit: int = 15) -> list[dict]:
    """キーワード検索で反応の良い投稿をスクレイピング（Topタブ）"""
    from urllib.parse import quote
    url = f"https://www.threads.com/search?q={quote(keyword)}&serp_type=default"
    posts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        kwargs = dict(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        if THREADS_SESSION:
            kwargs["storage_state"] = json.loads(base64.b64decode(THREADS_SESSION).decode())
        context = await browser.new_context(**kwargs)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # 「Top」タブをクリック（反応の良い投稿を表示）
            for label in ["Top", "トップ", "人気"]:
                try:
                    tab = await page.wait_for_selector(f'[role="tab"]:has-text("{label}")', timeout=3000)
                    if tab:
                        await tab.click()
                        await page.wait_for_timeout(2000)
                        print(f"  [{keyword}] Topタブに切り替え")
                        break
                except Exception:
                    continue

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            post_elements = await page.query_selector_all('[data-pressable-container="true"]')

            for el in post_elements[:limit]:
                try:
                    text_el = await el.query_selector("span")
                    if text_el:
                        text = await text_el.inner_text()
                        if text and len(text) > 20:
                            posts.append({"keyword": keyword, "text": text.strip()})
                except Exception:
                    continue

        except Exception as e:
            print(f"Error searching {keyword}: {e}")
        finally:
            await browser.close()

    return posts


async def scrape_all_accounts(accounts: list[str], limit: int = 20) -> dict:
    """複数アカウントをスクレイピング"""
    results = {}
    for account in accounts:
        print(f"Scraping {account}...")
        posts = await scrape_threads_account(account, limit)
        results[account] = posts
        print(f"  → {len(posts)}件取得")
        await asyncio.sleep(3)  # レート制限対策
    return results


def save_results(results: dict, filepath: str = "scraped_posts.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"保存完了: {filepath}")


if __name__ == "__main__":
    from config import ALL_ACCOUNTS, SCRAPE_POST_LIMIT

    async def main():
        results = await scrape_all_accounts(ALL_ACCOUNTS, SCRAPE_POST_LIMIT)
        save_results(results)

    asyncio.run(main())
