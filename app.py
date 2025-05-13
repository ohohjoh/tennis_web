from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import os
from collections import defaultdict
from datetime import datetime
import requests
import uuid
from dotenv import load_dotenv
load_dotenv()



app = Flask(__name__)

FIREBASE_URL = "https://tennisweb-project-default-rtdb.firebaseio.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH2 = os.path.join(BASE_DIR, "tenniscourt_with_guide.json")
JSON_PATH_SHOP = os.path.join(BASE_DIR, "tennis_shop_info_cleaned.json")



def load_from_firebase(path):
    """Firebase에서 특정 경로 데이터 가져오기"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"🚫 Firebase 요청 실패 ({path}): {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Firebase 요청 에러 ({path}):", e)
        return None

@app.template_filter("country_flag")
def country_flag(code):
    try:
        return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
    except:
        return "🏳️"

def generate_comments_html(comments_dict):
    html = '<ul class="list-unstyled">'
    for cid, comment in comments_dict.items():
        html += f'''
        <li data-comment-id="{cid}">
          <div class="fw-bold">{comment["content"]}</div>
          <div class="comment-meta mt-1">{comment["nickname"]} ・ {comment["created_at"]}</div>
        </li>
        '''
    html += '</ul>'
    return html



def load_data2():
    if os.path.exists(JSON_PATH2):
        with open(JSON_PATH2, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 JSON 파일을 찾을 수 없습니다:", JSON_PATH2)
    return []

def load_shop_data():
    if os.path.exists(JSON_PATH_SHOP):
        with open(JSON_PATH_SHOP, "r", encoding="utf-8") as f:
            return json.load(f)
    print("🚫 샵 JSON 파일을 찾을 수 없습니다:", JSON_PATH_SHOP)
    return []

def load_data_with_timestamp():
    fb_data = load_from_firebase("tennis_tournaments_ama")
    if fb_data:
        return fb_data.get("data", []), fb_data.get("executed_at", "알 수 없음")
    return [], "알 수 없음"

def load_combined_tournaments():
    return load_from_firebase("combined_tennis_tournaments_2025") or []

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
    fb_data = load_from_firebase("tennis_tournaments_ama")
    if fb_data:
        data = fb_data.get("data", [])
        last_modified = fb_data.get("executed_at", "알 수 없음")
    else:
        data, last_modified = [], "알 수 없음"

    return render_template(
        "tournament.html",
        data=data,
        page_title="🎾 테니스 대회 현황",
        last_modified=last_modified,
        currentPath="tournament"
    )

@app.route("/tournament_pro")
def tournaments_pro():
    bracket_data_raw = load_from_firebase("tennis_abstract_bracket")
    youtube_data_raw = load_from_firebase("tennis_tournaments_pro_data")
    schedule_data_raw = load_from_firebase("tennis_tournaments_pro_schedules")
    top100_raw = load_from_firebase("tennis_abstract_top100players")
    combined_data = load_combined_tournaments()  # ✅ 추가

    bracket_data = bracket_data_raw.get("data", []) if bracket_data_raw else []
    last_modified = bracket_data_raw.get("executed_at", "알 수 없음") if bracket_data_raw else "알 수 없음"
    youtube_data = youtube_data_raw.get("results", []) if youtube_data_raw else []
    youtube_last_modified = youtube_data_raw.get("executed_at", "알 수 없음") if youtube_data_raw else "알 수 없음"
    schedule_data = schedule_data_raw.get("matches", []) if schedule_data_raw else []
    schedule_date = schedule_data_raw.get("date", "알 수 없음") if schedule_data_raw else "알 수 없음"

    for item in youtube_data:
        if "summary" not in item:
            item["summary"] = "대회 설명이 없습니다."

    atp_players = top100_raw.get("data", []) if top100_raw else []
    wta_players = top100_raw.get("data2", []) if top100_raw else []
    top100_last_updated = top100_raw.get("executed_at", "알 수 없음") if top100_raw else "알 수 없음"

    return render_template(
        "tournament_pro.html",
        data=bracket_data,
        schedule=schedule_data,
        schedule_date=schedule_date,
        last_modified=last_modified,
        youtube_data=youtube_data,
        youtube_last_modified=youtube_last_modified,
        atp_players=atp_players,
        wta_players=wta_players,
        top100_last_updated=top100_last_updated,
        combined_data=combined_data,  # ✅ 템플릿에 전달
        page_title="🎾 ATP 드로우 및 일정",
        currentPath="tournament_pro"
    )

@app.route("/court-guide")
def court_guide():
    fb_data = load_from_firebase("tennis_courts")
    grouped = defaultdict(list)

    if fb_data:
        for entry in fb_data:
            grouped[entry['장소명']].append(entry)

    return render_template(
        "court-guide.html",
        data=grouped,
        page_title="🗓️ 코트 예약 가이드",
        currentPath="court"
    )

@app.route("/shop-guide")
def shop_guide():
    fb_data = load_from_firebase("tennis_shops")
    grouped = defaultdict(list)

    if isinstance(fb_data, list):
        for entry in fb_data:
            grouped[entry['상호명']].append(entry)
    elif isinstance(fb_data, dict):
        for entry in fb_data.values():
            grouped[entry['상호명']].append(entry)

    return render_template(
        "shop-guide.html",
        data=grouped,
        page_title="🛍️ 샵 예약 가이드",
        currentPath="shop"
    )



@app.route("/board")
def board():
    url = f"{FIREBASE_URL}/tennis_posts_bamboo.json"
    response = requests.get(url)
    posts = []

    if response.status_code == 200:
        data = response.json()
        if data:
            posts = list(data.values())
            posts.sort(key=lambda x: x["created_at"], reverse=True)

    # ✅ Firebase config from .env
    firebase_config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "databaseURL": os.getenv("FIREBASE_DB_URL"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID"),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    }

    return render_template(
        "board.html",
        posts=posts,
        firebase_config=firebase_config,  # ✅ 템플릿에 전달
        page_title="🌲 테나무숲",
        currentPath="board"
    )

# 글 저장
@app.route("/board/create", methods=["POST"])
def create_post():
    print("📥 게시글 작성 요청 도착!")
    nickname = request.form.get("nickname", "").strip() or "익명"
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not title or not content or not password:
        return "제목, 내용, 비밀번호는 필수입니다.", 400

    post_id = str(uuid.uuid4())
    post_data = {
        "id": post_id,
        "nickname": nickname,
        "title": title,
        "content": content,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "views": 0,
        "comments": []
    }

    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}.json"
    response = requests.put(url, json=post_data)
    

    if response.status_code == 200:
        return redirect("/board")
    else:
        return f"Firebase 저장 실패: {response.text}", 500

# 글 삭제 API
@app.route("/board/<post_id>/delete", methods=["POST"])
def delete_post(post_id):
    password = request.form.get("password", "").strip()

    # Firebase에서 데이터 불러오기
    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}.json"
    res = requests.get(url)
    if res.status_code != 200 or res.json() is None:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    post = res.json()
    if post.get("password") != password:
        return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403

    # Firebase에서 삭제
    delete_url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}.json"
    delete_res = requests.delete(delete_url)

    return jsonify({"success": delete_res.status_code == 200})

# 글 수정 API
@app.route("/board/<post_id>/edit", methods=["POST"])
def edit_post(post_id):
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not title or not content or not password:
        return jsonify({"success": False, "error": "제목, 내용, 비밀번호는 필수입니다."}), 400

    # Firebase에서 게시글 불러오기
    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}.json"
    res = requests.get(url)
    if res.status_code != 200 or res.json() is None:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    post = res.json()
    if post.get("password") != password:
        return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403

    # 수정할 내용만 PATCH 요청
    update_data = {
        "title": title,
        "content": content,
        "edited_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    patch_res = requests.patch(url, json=update_data)
    if patch_res.status_code == 200:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Firebase 수정 실패"}), 500


# 댓글 추가
@app.route("/board/<post_id>/comment", methods=["POST"])
def add_comment(post_id):
    print(f"📥 댓글 작성 요청 도착! (post_id={post_id})")
    nickname = request.form.get("nickname", "").strip() or "익명"
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not content or not password:
        return jsonify({"success": False, "error": "내용과 비밀번호는 필수입니다."}), 400

    comment_id = str(uuid.uuid4())
    comment_data = {
        "nickname": nickname,
        "content": content,
        "password": password,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}/comments/{comment_id}.json"
    res = requests.put(url, json=comment_data)

    if res.status_code == 200:
            # 🔁 저장 후 댓글 목록 다시 불러오기
            comments_res = requests.get(f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}/comments.json")
            comments_dict = comments_res.json() if comments_res.status_code == 200 else {}
            updated_html = generate_comments_html(comments_dict)
            return jsonify({"success": True, "updated_comments_html": updated_html})
    else:
            return jsonify({"success": False, "error": "Firebase 저장 실패"})
@app.route("/board/<post_id>/comment/<comment_id>/delete", methods=["POST"])
def delete_comment(post_id, comment_id):
    password = request.form.get("password", "").strip()

    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}/comments/{comment_id}.json"
    res = requests.get(url)
    if res.status_code != 200 or res.json() is None:
        return jsonify({"success": False, "error": "댓글을 찾을 수 없습니다."}), 404

    comment = res.json()
    if comment.get("password") != password:
        return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403

    delete_res = requests.delete(url)
    return jsonify({"success": delete_res.status_code == 200})

@app.route("/board/<post_id>/view", methods=["POST"])
def increase_view(post_id):
    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}.json"
    res = requests.get(url)
    if res.status_code != 200 or res.json() is None:
        return jsonify({"error": "게시글을 찾을 수 없습니다."}), 404

    post = res.json()
    current_views = post.get("views", 0)
    updated_views = current_views + 1

    update_data = {"views": updated_views}
    patch_res = requests.patch(url, json=update_data)

    return jsonify({"success": patch_res.status_code == 200, "views": updated_views})


@app.route("/board/<post_id>/comment/<comment_id>/edit", methods=["POST"])
def edit_comment(post_id, comment_id):
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    url = f"{FIREBASE_URL}/tennis_posts_bamboo/{post_id}/comments/{comment_id}.json"
    res = requests.get(url)
    if res.status_code != 200 or res.json() is None:
        return jsonify({"success": False, "error": "댓글을 찾을 수 없습니다."}), 404

    comment = res.json()
    if comment.get("password") != password:
        return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403

    update_data = {
        "content": content,
        "edited_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    patch_res = requests.patch(url, json=update_data)
    return jsonify({"success": patch_res.status_code == 200})



@app.template_filter('nl2br')
def nl2br(value):
    return value.replace('\n', '<br>\n')

@app.route("/api/data")
def api_data():
    fb_data = load_from_firebase("tennis_tournaments_ama")
    if fb_data:
        return jsonify(fb_data)
    else:
        return jsonify({"data": [], "executed_at": "알 수 없음"})

@app.route("/api/bracket")
def api_bracket():
    fb_data = load_from_firebase("tennis_abstract_bracket")
    if fb_data:
        return jsonify(fb_data)
    else:
        return jsonify({"data": [], "executed_at": "알 수 없음"})

if __name__ == "__main__":
    app.run(debug=True)