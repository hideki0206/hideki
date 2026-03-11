import anthropic
import json
import re
from config import ANTHROPIC_API_KEY, MY_ACCOUNT


def analyze_and_generate(scraped_data: dict) -> list[dict]:
    """スクレイピングデータを分析して投稿文を3本生成"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 自分の投稿
    my_posts = scraped_data.get(MY_ACCOUNT.lstrip("@"), [])
    my_texts = "\n".join([f"- {p['text']}" for p in my_posts[:15]])

    # 競合の投稿
    competitor_texts = ""
    for account, posts in scraped_data.items():
        if account != MY_ACCOUNT.lstrip("@"):
            texts = "\n".join([f"  - {p['text']}" for p in posts[:10]])
            competitor_texts += f"\n【{account}】\n{texts}\n"

    prompt = f"""あなたはSNSマーケティングの専門家です。

【自分（{MY_ACCOUNT}）の過去投稿スタイル】
{my_texts}

【競合アカウントの投稿（トレンド分析用）】
{competitor_texts}

上記を分析して、以下の条件でThreads投稿文を3本作成してください：

条件：
- 自分のトーン・スタイルを維持する
- 競合のトレンドテーマを取り入れる
- 朝・昼・夜それぞれに適した内容にする
- 各投稿は500文字以内
- エンゲージメントを高める内容（質問・共感・有益情報）

以下のJSON形式で返してください：
{{
  "morning": {{
    "text": "朝の投稿文",
    "theme": "テーマ"
  }},
  "noon": {{
    "text": "昼の投稿文",
    "theme": "テーマ"
  }},
  "evening": {{
    "text": "夜の投稿文",
    "theme": "テーマ"
  }}
}}
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        posts = []
        for time_slot, content in data.items():
            posts.append({
                "time_slot": time_slot,
                "text": content["text"],
                "theme": content.get("theme", ""),
            })
        return posts

    return []


def save_generated_posts(posts: list[dict], filepath: str = "generated_posts.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"生成完了: {filepath}")


if __name__ == "__main__":
    with open("scraped_posts.json", encoding="utf-8") as f:
        data = json.load(f)
    posts = analyze_and_generate(data)
    save_generated_posts(posts)
    for p in posts:
        print(f"\n【{p['time_slot']}】{p['theme']}")
        print(p['text'])
