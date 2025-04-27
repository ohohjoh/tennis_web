from flask import Flask, render_template, jsonify, request, redirect, url_for
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
JSON_PRO_YOUTUBE = os.path.join(BASE_DIR, "tennis_tournaments_pro_data.json")
JSON_TOURNAMENT_INFO = os.path.join(BASE_DIR, "static", "combined_tennis_tournaments_2025.json")


def generate_comments_html(comments):
    html = '''
    <ul class="list-unstyled" style="margin: 0; padding: 0;">
    '''
    for idx, comment in enumerate(comments):
        html += f'''
        <li class="p-1 small" data-comment-idx="{idx}">
          <div class="fw-bold" style="font-size: 0.85rem;">{comment["content"]}</div>
          <div class="d-flex justify-content-between align-items-center mt-1">
            <div class="small text-muted" style="font-size: 0.7rem;">
              {comment["nickname"]} ・ {comment["created_at"]}
              {'(수정됨 ' + comment["edited_at"] + ')' if comment.get("edited_at") else ''}
            </div>
            <div class="d-flex gap-1">
              <button class="btn btn-wimbledon btn-xs edit-comment-btn" data-comment-idx="{idx}" style="font-size: 0.6rem; padding: 0.2rem 0.4rem;">✏️</button>
              <button class="btn btn-wimbledon btn-xs delete-comment-btn" data-comment-idx="{idx}" style="font-size: 0.6rem; padding: 0.2rem 0.4rem;">🗑️</button>
            </div>
          </div>
        </li>
        '''
    html += '</ul>'
    return html


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
            data = json.load(f)
            return data.get("results", []), data.get("executed_at", "알 수 없음")
    print("🚫 유튜브 JSON 파일을 찾을 수 없습니다:", JSON_PRO_YOUTUBE)
    return [], "알 수 없음"

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
    youtube_data, youtube_last_modified = load_pro_youtube()

    # ✅ summary 없는 경우 기본값 추가
    for item in youtube_data:
        if "summary" not in item:
            item["summary"] = "대회 설명이 없습니다."

    return render_template(
        "tournament_pro.html",
        data=bracket_data,
        schedule=schedule_data["matches"],
        schedule_date=schedule_data["date"],
        last_modified=last_modified,
        youtube_data=youtube_data,
        youtube_last_modified=youtube_last_modified,
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

@app.route("/board")
def board():
    if not os.path.exists("tennis_posts_bamboo.json"):
        posts_data = {"posts": []}
    else:
        with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
            posts_data = json.load(f)

    posts = sorted(posts_data["posts"], key=lambda x: x["id"], reverse=True)
    return render_template("board.html", posts=posts, page_title="🌲 테나무숲", currentPath="board")

# 글 저장
@app.route("/board/create", methods=["POST"])
def create_post():
    nickname = request.form.get("nickname", "").strip() or "익명"
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()  # ✅ 비밀번호 받기

    if not title or not content:
        return "제목, 내용, 비밀번호는 필수입니다.", 400

    if not os.path.exists("tennis_posts_bamboo.json"):
        posts_data = {"posts": []}
    else:
        with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
            posts_data = json.load(f)

    new_id = max([p["id"] for p in posts_data["posts"]], default=0) + 1

    new_post = {
        "id": new_id,
        "nickname": nickname,
        "title": title,
        "content": content,
        "password": password,  # ✅ 비밀번호 저장
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "views": 0,  # ✅ 조회수 0으로 추가
        "comments": []
    }

    posts_data["posts"].insert(0, new_post)

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    return redirect("/board")

# 글 작성 API
@app.route("/board/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    password = request.form.get("password", "").strip()

    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"success": False, "error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for idx, post in enumerate(posts_data["posts"]):
        if post["id"] == post_id:
            if post.get("password", "") != password:  # ✅ 여기 수정
                return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403
            posts_data["posts"].pop(idx)
            break
    else:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})

# 글 수정 API
@app.route("/board/<int:post_id>/edit", methods=["POST"])
def edit_post(post_id):
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not title or not content or not password:
        return jsonify({"success": False, "error": "제목, 내용, 비밀번호를 입력해주세요."}), 400

    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"success": False, "error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for post in posts_data["posts"]:
        if post["id"] == post_id:
            if post["password"] != password:
                return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403
            post["title"] = title
            post["content"] = content
            post["edited_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    else:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})



# 댓글 추가
@app.route("/board/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    nickname = request.form.get("nickname", "").strip() or "익명"
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not content or not password:
            return jsonify({"success": False, "error": "댓글과 비밀번호는 필수입니다."}), 400
    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"success": False, "error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for post in posts_data["posts"]:
        if post["id"] == post_id:
            new_comment = {
                "nickname": nickname,
                "content": content,
                "password": password,  # ✅ 비밀번호 저장
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            post["comments"].append(new_comment)
            break
    else:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    # ✅ 댓글 부분을 다시 렌더링해서 보내줌
    updated_comments_html = generate_comments_html(post["comments"])
    return jsonify({"success": True, "updated_comments_html": updated_comments_html})


@app.route("/board/<int:post_id>/comment/<int:comment_idx>/delete", methods=["POST"])
def delete_comment(post_id, comment_idx):
    password = request.form.get("password", "").strip()  # ✅ 비밀번호 받기
    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"success": False, "error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for post in posts_data["posts"]:
        if post["id"] == post_id:
            if 0 <= comment_idx < len(post["comments"]):
                if post["comments"][comment_idx]["password"] != password:
                    return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403
                post["comments"].pop(comment_idx)
            else:
                return jsonify({"success": False, "error": "댓글 인덱스 오류"}), 400
            break
    else:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    updated_comments_html = generate_comments_html(post["comments"])
    return jsonify({"success": True, "updated_comments_html": updated_comments_html})   

@app.route("/board/<int:post_id>/comment/<int:comment_idx>/edit", methods=["POST"])
def edit_comment(post_id, comment_idx):
    new_content = request.form.get("content", "").strip()
    password = request.form.get("password", "").strip()

    if not new_content or not password:
        return jsonify({"success": False, "error": "수정할 내용과 비밀번호를 입력해주세요."}), 400

    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"success": False, "error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for post in posts_data["posts"]:
        if post["id"] == post_id:
            if 0 <= comment_idx < len(post["comments"]):
                if post["comments"][comment_idx]["password"] != password:
                    return jsonify({"success": False, "error": "비밀번호가 일치하지 않습니다."}), 403
                post["comments"][comment_idx]["content"] = new_content
                post["comments"][comment_idx]["edited_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            else:
                return jsonify({"success": False, "error": "댓글 인덱스 오류"}), 400
            break
    else:
        return jsonify({"success": False, "error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    # ✅ 수정 후에도 updated_comments_html로 반환해야 함
    updated_comments_html = generate_comments_html(post["comments"])
    return jsonify({"success": True, "updated_comments_html": updated_comments_html})

@app.route("/board/<int:post_id>/view", methods=["POST"])
def increase_view(post_id):
    if not os.path.exists("tennis_posts_bamboo.json"):
        return jsonify({"error": "게시글이 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "r", encoding="utf-8") as f:
        posts_data = json.load(f)

    for post in posts_data["posts"]:
        if post["id"] == post_id:
            post["views"] = post.get("views", 0) + 1
            break
    else:
        return jsonify({"error": "게시글을 찾을 수 없습니다."}), 404

    with open("tennis_posts_bamboo.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})

@app.template_filter('nl2br')
def nl2br(value):
    return value.replace('\n', '<br>\n')

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