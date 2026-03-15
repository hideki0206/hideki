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

    reference_texts = "\n\n---\n".join(REFERENCE_POSTS)

    prompt = f"""あなたはフリーランス・ビジネス系SNSアカウントの投稿ライターです。

━━━━━━━━━━━━━━━━━━
⛔ 絶対にNGなテーマ（これを書いたら失格）
━━━━━━━━━━━━━━━━━━
× 幸せの本質・感謝・心が軽くなる
× 自己肯定感・メンタル・癒し・傷・痛み
× 「満たされている人」「穏やかな人」「愛されている人」などの感情系ほど〜構文
× 人生哲学・精神論・スピリチュアル系
× 「今日もお疲れさまでした」などの共感・労いの言葉
━━━━━━━━━━━━━━━━━━

【参考にすべき過去投稿（このスタイルと構成のみ使うこと）】
{reference_texts}

【トレンド（参考程度）】
{competitor_texts}

━━━━━━━━━━━━━━━━━━
✅ ターゲット読者
「フリーランスで稼ぎたい」「働き方を変えたい」「収入を増やしたい」と考えている行動派の人
━━━━━━━━━━━━━━━━━━

以下3本を作成してください。

---
【朝の投稿】フォーマット：ビジネス系の対比リスト
- ・『〜』より『〜』 の形式で6〜8項目
- テーマ：集客・売上・働き方・フリーランス・ビジネス設計・時間とお金
- 最後に1〜2行の締め（ビジネスの気づき）
- 文字数：150〜250文字

【昼の投稿】フォーマット：実体験ベースの気づき
- 「〜したら、〇〇が変わった」「〜をやめたら稼げた」などの行動→結果の構文
- 月収・時間・件数など具体的な数字を入れる
- 文字数：100〜200文字

【夜の投稿】フォーマット：プロフィール誘導（必ずこの構成で書くこと）
- 「僕が手に入れた〇〇」というタイトル
- 具体的な生活・仕事スタイルのリスト（数字・地名・固有名詞を入れてリアルに）
- 「〜より、〜を選んだ。」という1文
- "〜"は〜。という形式の一言
- 末尾に必ず以下のCTAをそのまま入れること：
  「僕の〇〇に
興味ある人は僕のプロフィールを見てね。
裏側を公開してるから☺️」
- 文字数：200〜350文字

---
以下の形式で出力してください：

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
