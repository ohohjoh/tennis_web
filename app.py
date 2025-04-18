from flask import Flask, render_template, jsonify
import json
import os
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)

@app.template_filter("country_flag")
def country_flag(code):
    try:
        return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
    except:
        return "🏳️"

# 현재 app.py 기준 경로로 json 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "tennis_tournaments_results.json")
JSON_PATH2 = os.path.join(BASE_DIR, "tenniscourt_with_guide.json")
JSON_BRACKET = os.path.join(BASE_DIR, "tennis_abstract_bracket.json")

def load_data_with_timestamp():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("data", []), data.get("executed_at", "알 수 없음")
    print("🚫 JSON 파일을 찾을 수 없습니다:", JSON_PATH)
    return [], "알 수 없음"

def load_data2():
    if os.path.exists(JSON_PATH2):
        with open(JSON_PATH2, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 JSON 파일을 찾을 수 없습니다:", JSON_PATH2)
    return []

def load_abstract_bracket():
    if os.path.exists(JSON_BRACKET):
        with open(JSON_BRACKET, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 브래킷 JSON 파일을 찾을 수 없습니다:", JSON_BRACKET)
    return []

@app.route("/")
def index():
    data, last_modified = load_data_with_timestamp()
    return render_template(
        "tournament.html",
        data=data,
        page_title="🎾 테니스 대회 현황",
        last_modified=last_modified
    )

@app.route("/tournament")
def tournament():
    data, last_modified = load_data_with_timestamp()
    return render_template(
        "tournament.html",
        data=data,
        page_title="🎾 테니스 대회 현황",
        last_modified=last_modified
    )

@app.route("/tournament_pro")
def tournaments_pro():
    data = load_abstract_bracket()
    return render_template(
        "tournament_pro.html",
        data=data,
        page_title="🎾 ATP 드로우 시각화"
    )

@app.route("/court-guide")
def court_guide():
    raw_data = load_data2()
    grouped = defaultdict(list)
    for entry in raw_data:
        grouped[entry['장소명']].append(entry)

    return render_template("court-guide.html", data=grouped, page_title="🗓️ 코트 예약 가이드")

@app.route("/board")
def board():
    try:
        with open("posts.json", "r", encoding="utf-8") as f:
            posts = json.load(f)
    except FileNotFoundError:
        posts = []
    return render_template("board.html", posts=posts, page_title="💬익명 게시판")

@app.route("/api/data")
def api_data():
    data, executed_at = load_data_with_timestamp()
    return jsonify({"data": data, "executed_at": executed_at})

@app.route("/api/bracket")
def api_bracket():
    data = load_abstract_bracket()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
