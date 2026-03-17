import anthropic
import json
import random
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

    morning_formats = [
        "【フォーマットA】対比リスト：・『〜』より『〜』の形式で6〜8項目。テーマ：集客・売上・働き方・フリーランス・ビジネス設計。最後に1〜2行の締め。",
        "【フォーマットB】箇条書き逆説：「〜するな、〜しろ」「〜を捨てろ、〜を持て」の命令形で6〜8項目。テーマ：フリーランスの稼ぎ方・ビジネス思考。締めは1行の気づき。",
        "【フォーマットC】数字入りリスト：「フリーランスで月100万超えた人がやっていること」などタイトル付きで①〜⑥の番号リスト。各項目に短い補足を入れる。",
        "【フォーマットD】問いかけ型：冒頭に「〜で悩んでいませんか？」などの問い→原因を2〜3行→解決の視点を3〜4項目で提示。締めに行動を促す1行。",
    ]
    noon_formats = [
        "【フォーマットA】単価・件数の実体験：月収・稼働時間の具体的な変化を「Before→After」で描写。やったことをシンプルに1〜2点。",
        "【フォーマットB】失敗から学んだ話：最初にやらかした失敗→気づきのきっかけ→変えたこと→結果の順で。数字を入れてリアルに。",
        "【フォーマットC】意外な気づき：「〜だと思ってたら、実は〜だった」という逆説構文。フリーランスのお金・集客・時間に関する気づき。",
        "【フォーマットD】クライアントとの実話：特定のクライアントや案件のエピソード→そこから得た教訓。人との関係・信頼・価格交渉など。",
    ]
    evening_formats = [
        "【フォーマットA】手に入れた時間：「僕が手に入れた〇〇（時間・暮らし・働き方）」タイトル＋箇条書きリスト（地名・数字・固有名詞）＋「〜より〜を選んだ。」＋一言＋プロフィールCTA。",
        "【フォーマットB】1日のスケジュール公開：「僕の平日（or 週3日勤務）のリアルな1日」として時間軸で見せる。朝〜夜の流れを具体的に。締めにプロフィールCTA。",
        "【フォーマットC】稼ぎ方の変遷：「会社員時代→フリーランス1年目→今」の変化を3段階で。数字・感情・環境を交えてリアルに。プロフィールCTAで締める。",
        "【フォーマットD】理想の暮らしを手に入れるまで：「3年前の自分に言いたいこと」「フリーランスになって変わった5つのこと」など回顧録スタイル。プロフィールCTAで締める。",
    ]
    chosen_morning = random.choice(morning_formats)
    chosen_noon = random.choice(noon_formats)
    chosen_evening = random.choice(evening_formats)

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
【朝の投稿】{chosen_morning}
テーマ：集客・売上・働き方・フリーランス・ビジネス設計・時間とお金
文字数：150〜250文字

【昼の投稿】{chosen_noon}
テーマ：単価・働き方・集客・フリーランスの実体験
文字数：100〜200文字

【夜の投稿】{chosen_evening}
夜の投稿には必ず末尾に以下のCTAをそのまま入れること：
「僕の〇〇に
興味ある人は僕のプロフィールを見てね。
裏側を公開してるから☺️」
文字数：200〜350文字

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


def regenerate_single_post(slot: str, revision_note: str) -> dict:
    """1投稿だけ修正指示をもとに再生成"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    slot_label = {"morning": "朝", "noon": "昼", "evening": "夜"}.get(slot, slot)
    reference_texts = "\n\n---\n".join(REFERENCE_POSTS)

    prompt = f"""あなたはフリーランス・ビジネス系SNSアカウントの投稿ライターです。

━━━━━━━━━━━━━━━━━━
⛔ 絶対にNGなテーマ
━━━━━━━━━━━━━━━━━━
× 幸せの本質・感謝・心が軽くなる
× 自己肯定感・メンタル・癒し・傷・痛み
× 「満たされている人」「穏やかな人」などの感情系ほど〜構文
× 人生哲学・精神論・スピリチュアル系
× 「今日もお疲れさまでした」などの共感・労いの言葉
━━━━━━━━━━━━━━━━━━

【参考にすべき過去投稿】
{reference_texts}

━━━━━━━━━━━━━━━━━━
【修正指示】
対象：{slot_label}の投稿
修正内容：{revision_note}
━━━━━━━━━━━━━━━━━━

上記の修正指示をもとに、{slot_label}の投稿を1本だけ作り直してください。

{"【朝の投稿】・『〜』より『〜』の形式で6〜8項目。テーマ：集客・売上・働き方・フリーランス・ビジネス設計。最後に1〜2行の締め。文字数150〜250文字。" if slot == "morning" else ""}
{"【昼の投稿】「〜したら、〇〇が変わった」など行動→結果の構文。具体的な数字を入れる。文字数100〜200文字。" if slot == "noon" else ""}
{"【夜の投稿】「僕が手に入れた〇〇」タイトル＋具体的なリスト＋「〜より〜を選んだ。」＋一言＋末尾に「僕の〇〇に／興味ある人は僕のプロフィールを見てね。／裏側を公開してるから☺️」（／は改行）。文字数200〜350文字。" if slot == "evening" else ""}

以下の形式で出力してください：

THEME: テーマ
TEXT:
投稿文
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()

    theme_match = re.search(r'THEME:\s*(.+)', text)
    text_match = re.search(r'TEXT:\s*(.*)', text, re.DOTALL)

    theme = theme_match.group(1).strip() if theme_match else slot
    post_text = text_match.group(1).strip() if text_match else text

    return {"time_slot": slot, "theme": theme, "text": post_text}


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
