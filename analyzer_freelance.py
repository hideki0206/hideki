import anthropic
import json
import re
from config_freelance import ANTHROPIC_API_KEY, MY_ACCOUNT, REFERENCE_POSTS


def analyze_and_generate(scraped_data: dict) -> list[dict]:
    """スクレイピングデータを分析して投稿文を3本生成（フリーランス向け）"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 自分の投稿
    my_posts = scraped_data.get(MY_ACCOUNT.lstrip("@"), [])
    my_texts = "\n".join([f"- {p['text']}" for p in my_posts[:15]])

    # キーワード検索の投稿
    competitor_texts = ""
    for account, posts in scraped_data.items():
        if account == MY_ACCOUNT.lstrip("@"):
            continue
        if account == "__keyword_search__":
            texts = "\n".join([f"  - [{p.get('keyword','')}] {p['text']}" for p in posts[:15]])
            competitor_texts += f"\n【キーワード検索（反応の良い投稿）】\n{texts}\n"
        else:
            texts = "\n".join([f"  - {p['text']}" for p in posts[:10]])
            competitor_texts += f"\n【{account}】\n{texts}\n"

    reference_texts = "\n\n---\n".join(REFERENCE_POSTS[:6])

    prompt = f"""あなたはSNSマーケティングの専門家です。

【過去に反応が良かった投稿（このスタイルを最優先で参考にすること）】
{reference_texts}

【トレンド分析（キーワード検索で人気の投稿）】
{competitor_texts}

上記を分析して、以下の条件でThreads投稿文を3本作成してください：

条件：
- 「過去に反応が良かった投稿」のトーン・構成・言葉遣いを忠実に再現する
- ①②③ や ・ を使ったリスト形式が多い（このフォーマットを守ること）
- 逆説的な気づき・深い洞察を短く表現する（「〜ほど〜」「〜より〜」の対比構造）
- テーマ：人生哲学・幸せ・豊かさ・マインドセット・ビジネス観・生き方
- フリーランスや副業に限定せず、もっと広い「生き方・あり方」の話
- 短くテンポよく（100〜250文字）
- 朝・昼・夜それぞれに適した内容にする

以下の形式で出力してください（この形式を厳守してください）：

===MORNING===
THEME: テーマ
TEXT:
朝の投稿文

===NOON===
THEME: テーマ
TEXT:
昼の投稿文

===EVENING===
THEME: テーマ
TEXT:
夜の投稿文
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()

    posts = []
    for slot in ("morning", "noon", "evening"):
        pattern = rf'==={slot.upper()}===\s*THEME:\s*(.+?)\s*TEXT:\s*(.*?)(?====|\Z)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            theme = match.group(1).strip()
            post_text = match.group(2).strip()
            posts.append({
                "time_slot": slot,
                "text": post_text,
                "theme": theme,
            })
        else:
            print(f"{slot} のパースに失敗")

    return posts


def save_generated_posts(posts: list[dict], filepath: str = "generated_posts_freelance.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"生成完了: {filepath}")


if __name__ == "__main__":
    with open("scraped_posts_freelance.json", encoding="utf-8") as f:
        data = json.load(f)
    posts = analyze_and_generate(data)
    save_generated_posts(posts)
    for p in posts:
        print(f"\n【{p['time_slot']}】{p['theme']}")
        print(p['text'])
