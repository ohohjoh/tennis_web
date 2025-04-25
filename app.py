from flask import Flask, render_template, jsonify, request
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
JSON_PATH = os.path.join(BASE_DIR, "tennis_tournaments_ama.json")
JSON_PATH2 = os.path.join(BASE_DIR, "tenniscourt_with_guide.json")
JSON_BRACKET = os.path.join(BASE_DIR, "tennis_abstract_bracket.json")
JSON_PRO_SCHEDULE = os.path.join(BASE_DIR, "tennis_tournaments_pro_schedules.json")
JSON_PRO_YOUTUBE = os.path.join(BASE_DIR, "tennis_tournaments_pro_youtube.json")
JSON_TOURNAMENT_INFO = os.path.join(BASE_DIR, "static", "combined_tennis_tournaments_2025.json")


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
            data = json.load(f)
            return data.get("data", []), data.get("executed_at", "알 수 없음")
    print("🚫 브래킷 JSON 파일을 찾을 수 없습니다:", JSON_BRACKET)
    return [], "알 수 없음"

def load_pro_schedule():
    if os.path.exists(JSON_PRO_SCHEDULE):
        with open(JSON_PRO_SCHEDULE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 프로 스케줄 JSON 파일을 찾을 수 없습니다:", JSON_PRO_SCHEDULE)
    return {"date": "알 수 없음", "matches": []}

def load_pro_youtube():
    if os.path.exists(JSON_PRO_YOUTUBE):
        with open(JSON_PRO_YOUTUBE, "r", encoding="utf-8") as f:
            return json.load(f).get("results", [])
    print("🚫 유튜브 JSON 파일을 찾을 수 없습니다:", JSON_PRO_YOUTUBE)
    return []

def load_combined_tournaments():
    print("📁 load_combined_tournaments() 호출됨")
    if os.path.exists(JSON_TOURNAMENT_INFO):
        print("✅ 파일 존재:", JSON_TOURNAMENT_INFO)
        with open(JSON_TOURNAMENT_INFO, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 통합 대회 정보 JSON을 찾을 수 없습니다:", JSON_TOURNAMENT_INFO)
    return []

@app.route("/")
def index():
    data, last_modified = load_data_with_timestamp()
    return render_template(
        "index.html",
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
    bracket_data, last_modified = load_abstract_bracket()
    schedule_data = load_pro_schedule()
    youtube_data = load_pro_youtube()
    tournament_info = load_combined_tournaments()


    return render_template(
        "tournament_pro.html",
        data=bracket_data,
        schedule=schedule_data["matches"],
        schedule_date=schedule_data["date"],
        last_modified=last_modified,
        youtube_data=youtube_data,
        tournament_info=tournament_info,
        page_title="🎾 ATP 드로우 및 일정",
        currentPath="tournament_pro"
    )
    

@app.route("/court-guide")
def court_guide():
    raw_data = load_data2()
    grouped = defaultdict(list)
    for entry in raw_data:
        grouped[entry['장소명']].append(entry)

    return render_template("court-guide.html", data=grouped, page_title="🗓️ 코트 예약 가이드", currentPath="court")

@app.route("/board", methods=["GET", "POST"])
def board():
    if request.method == "POST":
        try:
            data = request.get_json()
            content = data.get("content", "").strip()
            if not content:
                return jsonify({"error": "내용이 비어 있습니다"}), 400

            posts = []
            if os.path.exists("posts.json"):
                with open("posts.json", "r", encoding="utf-8") as f:
                    posts = json.load(f)

            posts.insert(0, content)

            with open("posts.json", "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False, indent=2)

            return jsonify({"content": content})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        try:
            with open("posts.json", "r", encoding="utf-8") as f:
                posts = json.load(f)
        except FileNotFoundError:
            posts = []
        return render_template("board.html", posts=posts, page_title="🌲테나무숲")

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