import anthropic
import json
import re
from config import ANTHROPIC_API_KEY, MY_ACCOUNT, REFERENCE_POSTS


def analyze_and_generate(scraped_data: dict) -> list[dict]:
    """スクレイピングデータを分析して投稿文を3本生成"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 自分の投稿
    my_posts = scraped_data.get(MY_ACCOUNT.lstrip("@"), [])
    my_texts = "\n".join([f"- {p['text']}" for p in my_posts[:15]])

    # 競合・キーワード検索の投稿
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

    reference_texts = "\n\n---\n".join(REFERENCE_POSTS[:6])  # 上位6本を使用

    prompt = f"""あなたはSNSマーケティングの専門家です。

【過去に反応が良かった投稿（このスタイルを最優先で参考にすること）】
{reference_texts}

【競合アカウントの投稿（トレンド分析用）】
{competitor_texts}

上記を分析して、以下の条件でThreadsのツリー型投稿（6パート構成）を朝・昼・夜の3セット作成してください：

■ 共通の文体ルール（全投稿に適用）：
- 「過去に反応が良かった投稿」のトーン・構成・言葉遣いを忠実に再現する
- 語りかける口語体：「〜だよね...」「〜してみてね↓」「〜だよ」
- 読者の悩みに共感してから解決策を提示する流れ
- 具体的な数字や事例を入れる（リピート率80%、月50万など）
- 競合のトレンドテーマを取り入れる

■ 全枠共通：ツリー型投稿（6パート構成）
- PART1：タイトル・フックのみ（例：「リピート率90%超えのサロンがやってる接客」）
- PART2：問題提起と共感（「実は〜です。〜だよね...。まずは解説を見てね↓」）
- PART3：【タイトル】(2/4) ノウハウ前半（箇条書き or 番号リスト）+ 「↓」で次へ誘導
- PART4：【タイトル】(3/4) ノウハウ後半 + 具体的なアドバイス
- PART5：CTA（「〜してみてください。応援しています。」）
- PART6：プロフ誘導（「ちなみに、〜したい人は僕のプロフをチェックしてね！☺️」）

以下の形式で出力してください（この形式を厳守してください）：

===MORNING===
THEME: テーマ
PART1:
（タイトルのみ）
PART2:
（問題提起・共感）
PART3:
（ノウハウ前半）
PART4:
（ノウハウ後半）
PART5:
（CTA・応援）
PART6:
（プロフ誘導）

===NOON===
THEME: テーマ
PART1:
（タイトルのみ）
PART2:
（問題提起・共感）
PART3:
（ノウハウ前半）
PART4:
（ノウハウ後半）
PART5:
（CTA・応援）
PART6:
（プロフ誘導）

===EVENING===
THEME: テーマ
PART1:
（タイトルのみ）
PART2:
（問題提起・共感）
PART3:
（ノウハウ前半）
PART4:
（ノウハウ後半）
PART5:
（CTA・応援）
PART6:
（プロフ誘導）
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()

    posts = []

    def parse_thread_parts(parts_text: str) -> list:
        parts = []
        for i in range(1, 7):
            end = rf'(?=PART{i+1}:|\Z)'
            part_match = re.search(rf'PART{i}:\s*(.*?){end}', parts_text, re.DOTALL)
            if part_match:
                parts.append(part_match.group(1).strip())
        return parts

    for slot in ("morning", "noon", "evening"):
        match = re.search(
            rf'==={slot.upper()}===\s*THEME:\s*(.+?)\s*(PART1:.*?)(?====|\Z)',
            text, re.DOTALL
        )
        if match:
            posts.append({
                "time_slot": slot,
                "theme": match.group(1).strip(),
                "is_thread": True,
                "thread_parts": parse_thread_parts(match.group(2)),
            })
        else:
            print(f"{slot} のパースに失敗")

    return posts


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
