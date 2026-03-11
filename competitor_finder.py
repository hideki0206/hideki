import anthropic
import json
import os
import re
from config import ANTHROPIC_API_KEY, MY_ACCOUNT


def find_competitors(my_posts: list[dict], existing_competitors: list[str]) -> list[str]:
    """自分の投稿を分析して競合アカウントを提案"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sample_texts = "\n".join([p["text"] for p in my_posts[:10]])

    prompt = f"""以下はThreadsアカウント {MY_ACCOUNT} の投稿サンプルです：

{sample_texts}

このアカウントのジャンル・テーマを分析し、
競合・参考になりそうなThreadsアカウントのユーザー名を10個提案してください。

既存の競合リスト（除外）: {existing_competitors}

以下のJSON形式で返してください：
{{
  "genre": "ジャンルの説明",
  "competitors": ["@username1", "@username2", ...]
}}
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        print(f"ジャンル: {data.get('genre', '')}")
        return data.get("competitors", [])

    return []


if __name__ == "__main__":
    # テスト用
    sample_posts = [{"text": "サロン集客のコツを紹介します", "account": "hideki0206"}]
    competitors = find_competitors(sample_posts, ["@salon.marketing"])
    print("提案された競合:", competitors)
