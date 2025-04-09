from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

# 현재 app.py 기준 경로로 json 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "tennis_results.json")

def load_data():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 JSON 파일을 찾을 수 없습니다:", JSON_PATH)
    return []

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", data=data)

@app.route("/api/data")
def api_data():
    return jsonify(load_data())

if __name__ == "__main__":
    app.run(debug=True)