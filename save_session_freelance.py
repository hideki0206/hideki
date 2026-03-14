"""
@hideki0206のThreadsセッションをローカルで保存するスクリプト。
初回のみ実行してください。

使い方:
  python save_session_freelance.py

保存されたbase64文字列をGitHub Secret「THREADS_SESSION_2」に登録してください。
"""

import asyncio
import json
import base64
from playwright.async_api import async_playwright
from config_freelance import THREADS_USERNAME, THREADS_PASSWORD


async def save_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("Threadsのログインページを開きます（@hideki0206）...")
        await page.goto("https://www.threads.com/login", wait_until="domcontentloaded")

        print("ログイン情報を入力中...")
        await page.wait_for_selector('input[type="text"]', timeout=15000)
        await page.fill('input[type="text"]', THREADS_USERNAME)
        await page.fill('input[type="password"]', THREADS_PASSWORD)

        for sel in ['button[type="submit"]', 'div[role="button"]:has-text("Log in")', 'div[role="button"]:has-text("ログイン")']:
            try:
                btn = await page.wait_for_selector(sel, timeout=3000)
                if btn:
                    await btn.click()
                    break
            except Exception:
                continue

        print("\n⚠️  チャレンジページが表示された場合は、ブラウザ上で手動で認証してください。")
        print("ログインが完了したらEnterキーを押してください...")
        input()

        storage = await context.storage_state()
        storage_json = json.dumps(storage)
        storage_b64 = base64.b64encode(storage_json.encode()).decode()

        with open("session_freelance.json", "w") as f:
            f.write(storage_json)

        print(f"\n✅ セッション保存完了: session_freelance.json")
        print(f"\n以下をGitHub Secret「THREADS_SESSION_2」に登録してください：\n")
        print(storage_b64)

        await browser.close()


asyncio.run(save_session())
