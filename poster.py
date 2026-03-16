import asyncio
import json
import base64
import os
from playwright.async_api import async_playwright
from config import THREADS_USERNAME, THREADS_PASSWORD

THREADS_SESSION = os.environ.get("THREADS_SESSION", "")


async def _setup_page() -> tuple:
    """ブラウザ起動・ログイン・ホーム遷移を行いpageを返す"""
    p_instance = await async_playwright().__aenter__()
    browser = await p_instance.chromium.launch(headless=True)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    if THREADS_SESSION:
        storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
        context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
    else:
        context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

    page = await context.new_page()

    if THREADS_SESSION:
        print("保存済みセッションを使用します")
        await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
    else:
        print("Threadsにアクセス中...")
        await page.goto("https://www.threads.com/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
        username_input = await page.wait_for_selector('input[type="text"]', timeout=15000)
        await username_input.fill(THREADS_USERNAME)
        password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
        await password_input.fill(THREADS_PASSWORD)
        login_btn = None
        for sel in ['button[type="submit"]', 'div[role="button"]:has-text("Log in")', 'div[role="button"]:has-text("ログイン")']:
            try:
                login_btn = await page.wait_for_selector(sel, timeout=3000)
                if login_btn:
                    await login_btn.click()
                    break
            except Exception:
                continue
        if not login_btn:
            await password_input.press("Enter")
        await page.wait_for_timeout(8000)

    return p_instance, browser, page


async def _login_if_needed(page) -> None:
    """セッション切れでログインページに飛んでいた場合にパスワードログインする"""
    if "login" not in page.url and "accounts" not in page.url:
        return
    print(f"セッション切れを検知 (URL: {page.url})。パスワードでログイン中...")
    username_input = await page.wait_for_selector('input[type="text"]', timeout=15000)
    await username_input.fill(THREADS_USERNAME)
    password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
    await password_input.fill(THREADS_PASSWORD)
    login_btn = None
    for sel in ['button[type="submit"]', 'div[role="button"]:has-text("Log in")', 'div[role="button"]:has-text("ログイン")']:
        try:
            login_btn = await page.wait_for_selector(sel, timeout=3000)
            if login_btn:
                await login_btn.click()
                break
        except Exception:
            continue
    if not login_btn:
        await password_input.press("Enter")
    await page.wait_for_timeout(8000)
    print(f"ログイン後URL: {page.url}")


async def _open_compose(page) -> None:
    """新規スレッドモーダルを開く"""
    # 現在のURLを確認（セッション切れでログインページに飛んでいないか）
    print(f"現在のURL: {page.url}")
    await page.screenshot(path="/tmp/threads_before_compose.png")

    # 複数のセレクターを順番に試す
    # Create ボタン（+）を優先する：フルモーダルが開き「スレッドに追加」が使える
    compose_selectors = [
        '[aria-label="Create"]',
        '[aria-label="New post"]',
        '[aria-label="新しいスレッドを作成"]',
        'div[role="button"]:has-text("作成")',
        'text="今なにしてる？"',
        '[aria-label="テキストフィールドが空です。テキストを入力して新しい投稿を作成できます。"]',
        'text="What\'s new?"',
        'text="Start a thread"',
    ]

    opened = False
    for sel in compose_selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el:
                await el.click()
                print(f"投稿入力欄を開きました: {sel}")
                opened = True
                break
        except Exception:
            continue

    if not opened:
        await page.screenshot(path="/tmp/threads_compose_fail.png")
        raise Exception(f"投稿入力欄が見つかりませんでした。URL: {page.url}")

    # モーダルが開くまで待つ
    await page.wait_for_selector('[contenteditable="true"]', timeout=10000)


async def post_to_threads_async(text: str) -> str:
    """PlaywrightでThreadsにログインして単発投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        if THREADS_SESSION:
            storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
        else:
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

        page = await context.new_page()

        try:
            await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            await _login_if_needed(page)

            await _open_compose(page)

            print("テキストを入力中...")
            text_area = await page.wait_for_selector('[contenteditable="true"]', timeout=10000)
            await text_area.click()
            await page.wait_for_timeout(500)
            await page.keyboard.type(text)
            await page.wait_for_timeout(1000)

            print("投稿ボタンを押しています...")
            posted = False
            for btn_text in ["投稿", "Post"]:
                btn = page.get_by_text(btn_text, exact=True)
                count = await btn.count()
                if count > 0:
                    await btn.last.click(force=True)
                    posted = True
                    break
            if not posted:
                await text_area.press("Control+Enter")
            await page.wait_for_timeout(5000)
            print("投稿完了")
            return "posted"

        finally:
            await browser.close()


async def post_thread_to_threads_async(parts: list) -> str:
    """PlaywrightでThreadsにツリー型投稿（複数パート連結）を投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        if THREADS_SESSION:
            storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
        else:
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

        page = await context.new_page()

        try:
            await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            await _login_if_needed(page)

            await _open_compose(page)
            await page.wait_for_timeout(2000)

            print(f"ツリー型投稿開始（{len(parts)}パート）")

            for i, part in enumerate(parts):
                print(f"  パート{i+1}を入力中...")

                # i番目の contenteditable が出現するまで待機（最大10秒）
                for _ in range(20):
                    areas = await page.query_selector_all('[contenteditable="true"]')
                    if len(areas) > i:
                        break
                    await page.wait_for_timeout(500)
                else:
                    print(f"  警告: contenteditable[{i}]が現れず（スキップ）")
                    continue

                await areas[i].scroll_into_view_if_needed()
                await areas[i].click()
                await page.wait_for_timeout(300)

                # keyboard.type() でキーボードイベントを発火させ「スレッドに追加」ボタンを有効化
                await page.keyboard.type(part, delay=20)
                await page.wait_for_timeout(300)

                # InputEvent dispatch で Lexical の EditorState を更新
                await page.evaluate("""
                    (idx) => {
                        const areas = document.querySelectorAll('[contenteditable="true"]');
                        const el = areas[idx];
                        if (!el) return;
                        el.dispatchEvent(new InputEvent('input', {
                            inputType: 'insertText',
                            bubbles: true,
                            cancelable: false,
                            composed: true
                        }));
                    }
                """, i)
                await page.wait_for_timeout(500)

                actual = await areas[i].inner_text()
                print(f"    入力確認: [{actual[:30]}] ({len(actual)}文字)")

                # 最後のパート以外は「スレッドに追加」をクリック
                if i < len(parts) - 1:
                    add_selectors = [
                        'text="Add to thread"',
                        'text="スレッドに追加"',
                        '[role="button"]:has-text("Add to thread")',
                        '[role="button"]:has-text("スレッドに追加")',
                        '[aria-label="Add to thread"]',
                        '[aria-label="スレッドに追加"]',
                    ]
                    added = False
                    for sel in add_selectors:
                        try:
                            btn = await page.wait_for_selector(sel, timeout=5000)
                            if btn:
                                await btn.click()
                                print(f"    「スレッドに追加」クリック: {sel}")
                                await page.wait_for_timeout(2000)  # 新エディタ生成を待つ
                                added = True
                                break
                        except Exception:
                            continue
                    if not added:
                        print(f"    警告: 「スレッドに追加」ボタンが見つかりませんでした（パート{i+1}）")

            # 投稿ボタンをクリック
            await page.screenshot(path="/tmp/threads_before_post.png")
            print("投稿ボタンを押しています...")
            posted = False
            for btn_text in ["投稿", "Post"]:
                btn = page.get_by_role("button", name=btn_text, exact=True)
                if await btn.count() > 0:
                    await btn.last.click()
                    posted = True
                    print(f"  '{btn_text}' をクリック")
                    break
            if not posted:
                areas = await page.query_selector_all('[contenteditable="true"]')
                await areas[-1].press("Control+Enter")

            # モーダルが閉じるまで待機
            try:
                await page.wait_for_selector('text="New thread"', state="hidden", timeout=20000)
                print("  モーダルが閉じました")
            except Exception:
                await page.wait_for_timeout(10000)

            print("ツリー型投稿完了")
            return "posted"

        finally:
            await browser.close()


def post_to_threads(text: str) -> str:
    return asyncio.run(post_to_threads_async(text))


def post_thread_to_threads(parts: list) -> str:
    """セッションクッキーを使って Threads API に直接投稿（ツリー型）"""
    import uuid
    import requests

    # セッションから cookies と csrftoken を取得
    if THREADS_SESSION:
        storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
    else:
        with open(os.path.join(os.path.dirname(__file__), "session.json")) as f:
            storage = json.load(f)

    cookies = {c["name"]: c["value"] for c in storage.get("cookies", [])}
    csrftoken = cookies.get("csrftoken", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-csrftoken": csrftoken,
        "x-ig-app-id": "238260118697367",
        "x-instagram-ajax": "0",
        "x-asbd-id": "359341",
        "x-bloks-version-id": "1363ee4ad31aa321b811ce30b2aacd0f644c2fb57f440040b43e585a4befa092",
        "Referer": "https://www.threads.com/",
        "Origin": "https://www.threads.com",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }

    url = "https://www.threads.com/api/v1/media/configure_text_only_post/"
    # 全パートで共通のスレッドIDを生成
    thread_context_id = str(uuid.uuid4())
    reply_id = ""

    print(f"ツリー型投稿開始（{len(parts)}パート）thread_id={thread_context_id}")
    for i, part in enumerate(parts):
        print(f"  パート{i+1}を投稿中...")

        app_info = {
            "community_flair_id": None,
            "entry_point": "main_tab_bar",
            "excluded_inline_media_ids": "[]",
            "fediverse_composer_enabled": True,
            "is_reply_approval_enabled": False,
            "is_spoiler_media": False,
            "link_attachment_url": None,
            "ranking_info_token": None,
            "reply_control": 0,
            "self_thread_context_id": thread_context_id,
            "snippet_attachment": None,
            "special_effects_enabled_str": None,
            "tag_header": None,
            "text_with_entities": {"entities": [], "text": part},
        }
        if reply_id:
            app_info["reply_id"] = reply_id

        data = {
            "audience": "default",
            "barcelona_source_reply_id": reply_id,
            "caption": part,
            "creator_geo_gating_info": '{"whitelist_country_codes":[]}',
            "cross_share_info": "",
            "custom_accessibility_caption": "",
            "gen_ai_detection_method": "",
            "internal_features": "",
            "is_meta_only_post": "",
            "is_paid_partnership": "",
            "is_upload_type_override_allowed": "1",
            "music_params": "",
            "publish_mode": "text_post",
            "should_include_permalink": "true",
            "text_post_app_info": json.dumps(app_info, ensure_ascii=False),
        }

        res = requests.post(url, data=data, headers=headers, cookies=cookies)
        if res.status_code != 200:
            raise Exception(f"パート{i+1}の投稿失敗: HTTP {res.status_code} {res.text[:200]}")

        pk = res.json().get("media", {}).get("pk", "")
        if not pk:
            raise Exception(f"パート{i+1}: レスポンスに pk がありません: {res.text[:200]}")

        print(f"    → 投稿完了 pk={pk}")
        reply_id = pk  # 次のパートは常に直前のパートへの返信

    print("ツリー型投稿完了")
    return "posted"


if __name__ == "__main__":
    test_text = "テスト投稿です #テスト"
    post_id = post_to_threads(test_text)
    print(f"結果: {post_id}")
