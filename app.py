
import os
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "temporary-secret")
DB_PATH = os.environ.get("DB_PATH", "learning_ai.db")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

HTML = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学習型AI</title>
<h1>学習型AI</h1>

<h2>AIに教える</h2>
<form method="post" action="/teach">
<textarea name="fact" required placeholder="教えたいことを書く"></textarea>
<button>教えて保存</button>
</form>

<h2>AIに質問する</h2>
<form method="post" action="/ask">
<textarea name="question" required placeholder="質問を書く"></textarea>
<button>質問する</button>
</form>

{% if answer %}
<h2>AIの回答</h2>
<p style="white-space:pre-wrap">{{ answer }}</p>
{% endif %}

<h2>覚えた知識</h2>
{% for fact in facts %}
<p>{{ fact[1] }}</p>
{% endfor %}
"""

def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL
        )
    """)
    return con

@app.route("/")
def home():
    with connect() as con:
        facts = con.execute(
            "SELECT id, fact FROM facts ORDER BY id DESC"
        ).fetchall()

    return render_template_string(
        HTML,
        facts=facts,
        answer=session.pop("answer", "")
    )

@app.route("/teach", methods=["POST"])
def teach():
    fact = request.form.get("fact", "").strip()

    if fact:
        with connect() as con:
            con.execute(
                "INSERT INTO facts(fact) VALUES(?)",
                (fact,)
            )

    session["answer"] = "教えてくれた内容を保存した。"
    return redirect(url_for("home"))

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()

    with connect() as con:
        facts = con.execute(
            "SELECT fact FROM facts ORDER BY id"
        ).fetchall()

    knowledge = "\n".join(
        "- " + fact[0] for fact in facts
    )

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        answer = "AI接続の設定がまだ終わっていない。"
    else:
        try:
            client = OpenAI(api_key=api_key)

            response = client.responses.create(
                model=MODEL,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "あなたは人間から学ぶAIだ。"
                            "先生から教わった知識と一般知識を区別する。"
                            "知らないことは知らないと答える。"
                            "曖昧さや矛盾があれば先生に質問する。"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            "先生から教わった知識:\n"
                            + knowledge
                            + "\n\n質問:\n"
                            + question
                        )
                    }
                ]
            )

            answer = response.output_text

        except Exception:
            answer = "AIとの接続でエラーが発生した。"

    session["answer"] = answer
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
