# ATP_from_blog_crawler

import requests
import re
import json
from bs4 import BeautifulSoup
import os
import traceback
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import feedparser

# 🔑 환경변수 로드
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# 📋 로그 설정
base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "ATP_from_blog_git_log_txt.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 📄 에러 로그 저장
def save_error_to_json(error_trace, source="Unknown"):
    error_info = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "error": error_trace
    }
    output_path = os.path.join(log_dir, "ATP_from_blog_git_Errors.json")

    try:
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        else:
            existing = []

        existing.append(error_info)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logging.error(f"❌ 에러 저장 완료: {source}")
    except Exception as e:
        logging.error(f"❗ 에러 저장 실패: {e}")

# 📂 결과 저장
def save_results_to_json(data, filename, add_executed_at=False):
    try:
        output_path = os.path.join(base_dir, filename)

        if add_executed_at:
            result = {
                "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": data
            }
        else:
            result = data

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logging.info(f"✅ 결과 저장 완료: {output_path}")
    except Exception:
        logging.error("❌ 결과 저장 실패")
        save_error_to_json(traceback.format_exc(), source="Result Saving")
        exit(1)
        
# HTML 파싱 관련 함수들

def extract_match_html(js_var_name, html):
    pattern = rf"var {js_var_name}\s*=\s*'(.*?)';"
    match = re.search(pattern, html, re.DOTALL)
    return match.group(1) if match else ""

def normalize_player_name(player_str):
    seed_match = re.match(r"\((\d+|WC|Q|LL|Alt|PR)\)", player_str)
    seed = seed_match.group(1) if seed_match else None
    player_str = player_str[len(seed_match.group(0)):] if seed_match else player_str
    country_match = re.search(r"\(([A-Z]{3})\)$", player_str)
    country = country_match.group(1) if country_match else None
    name = player_str[:country_match.start()].strip() if country_match else player_str.strip()
    return {"seed": seed, "name": name, "country": country}

def parse_matches(html_block):
    soup = BeautifulSoup(html_block, "html.parser")
    matches = []
    for raw_line in soup.decode_contents().split("<br/>"):
        raw_line = raw_line.strip()
        if not raw_line or raw_line.startswith("&nbsp;"): continue
        clean_line = BeautifulSoup(raw_line, "html.parser").text.strip()
        match = re.match(r"(?P<round>[A-Z0-9]+):\s+(?P<player1>.+?)\s+(?:d\.|vs)\s+(?P<player2>.+?)\s*(?P<score>\[\d.*?\])?$", clean_line)
        if match:
            p1 = match.group("player1").strip()
            p2 = match.group("player2").strip()
            score = match.group("score").strip("[]") if match.group("score") else None
            score_in_p2 = re.match(r"(.+?)\s+(\d{1,2}[-\d\(\)\sRET]*)$", p2)
            if score_in_p2:
                p2 = score_in_p2.group(1)
                score = score or score_in_p2.group(2)
            matches.append({"round": match.group("round"), "player1": normalize_player_name(p1), "player2": normalize_player_name(p2), "score": score})
    return matches

def fetch_current_tournaments():
    url = "https://www.tennisabstract.com/"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", id="current-events")
    if not table: return []
    categories = ["WTA", "ATP", "Challenger"]
    tournament_data = []
    for col_idx, td in enumerate(table.find_all("td")):
        tour_type = categories[col_idx]
        current_b = None
        for elem in td.children:
            if elem.name == "b":
                current_b = elem.text.strip()
            elif elem.name == "a" and "Results and Forecasts" in elem.text:
                tournament_data.append({"tournament": current_b, "tour": tour_type, "url": elem["href"]})
    return tournament_data

def convert_to_bracket_format(data):
    ISO3_TO_ISO2 = {
        "ESP": "ES", "AUS": "AU", "GBR": "GB", "GRE": "GR", "FRA": "FR", "RUS": "RU",
        "USA": "US", "DEN": "DK", "NOR": "NO", "SRB": "RS", "ARG": "AR", "ITA": "IT",
        "SUI": "CH", "NED": "NL", "BEL": "BE", "HUN": "HU", "GER": "DE", "COL": "CO",
        "CAN": "CA", "BIH": "BA", "CRO": "HR", "KAZ": "KZ", "TPE": "TW", "CHN": "CN",
        "JPN": "JP", "RSA": "ZA"
    }

    def flag(c):
        return ''.join([chr(ord(x) + 127397) for x in ISO3_TO_ISO2.get(c, '')])

    bracket_data = []
    for tournament in data:
        round_dict = defaultdict(list)
        for match in tournament.get("completed", []):
            p1, p2 = match["player1"], match["player2"]
            round_dict[match["round"]].append({
                "player1": f"{flag(p1['country'])} {p1['name']}",
                "player2": f"{flag(p2['country'])} {p2['name']}",
                "score": match.get("score"),
                "winner": match.get("winner", None),
                "source": "completed"
            })
        for match in tournament.get("upcoming", []):
            p1, p2 = match["player1"], match["player2"]
            round_dict[match["round"]].append({
                "player1": f"{flag(p1['country'])} {p1['name']}",
                "player2": f"{flag(p2['country'])} {p2['name']}",
                "score": None,
                "winner": None,
                "source": "upcoming"
            })
        bracket_data.append({
            "tournament": tournament["tournament"],
            "url": tournament["url"],
            "bracket": dict(round_dict)
        })
    return bracket_data

def extract_date_from_html(soup):
    tz_link = soup.select_one("div#tzLink a")
    if tz_link:
        date_match = re.search(r"(\d{2})\.(\d{2})\.", tz_link.text)
        if date_match:
            day, month = date_match.groups()
            today = datetime.utcnow() + timedelta(hours=9)
            return f"{today.year}-{month}-{day}"
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d")

def fetch_all_atp_schedule_from_dom():
    today = datetime.utcnow() + timedelta(hours=9)  # 한국시간
    url = f"https://www.tennisexplorer.com/matches/?year={today.year}&month={today.month}&day={today.day}&type=atp-single"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    time.sleep(2)
    for _ in range(3):
        try:
            time.sleep(2)
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            logging.warning(f"🔁 요청 재시도 중... {e}")
    else:
        logging.error("❌ 요청 실패: tennisexplorer.com")
        save_error_to_json("Connection failed 3 times", source="tennisexplorer.com")
        return
    
    soup = BeautifulSoup(res.text, "html.parser")

    matches = []
    current_tournament = ""
    rows = soup.select("table.result tr")
    i = 0

    while i < len(rows):
        row = rows[i]
        classes = row.get("class", [])

        # ✅ 대회명 (한 줄로 colspan=2)
        if row.find("td", colspan="2"):
            td = row.find("td", colspan="2")
            a = td.find("a")
            if a:
                current_tournament = a.text.strip()
            i += 1
            continue

        # ✅ 매치 정보 (2행 구성)
        if "fRow" in classes or row.find("td", class_="first time"):
            try:
                time_td = row.select_one("td.first.time")
                player1_td = row.select_one("td.t-name a")
                time_utc_str = time_td.text.strip() if time_td else ""
                player1 = player1_td.text.strip() if player1_td else ""

                row2 = rows[i + 1] if i + 1 < len(rows) else None
                player2_td = row2.select_one("td.t-name a") if row2 else None
                player2 = player2_td.text.strip() if player2_td else ""

                # 시간 정규식 매칭
                match = re.match(r"(\d{1,2}):(\d{2})", time_utc_str)
                if match:
                    hour, minute = map(int, match.groups())
                    match_datetime_eu = datetime(today.year, today.month, today.day, hour, minute, tzinfo=ZoneInfo("Europe/Berlin"))
                    match_datetime_utc = match_datetime_eu.astimezone(ZoneInfo("UTC"))
                    match_datetime_kst = match_datetime_utc.astimezone(ZoneInfo("Asia/Seoul"))

                    matches.append({
                        "date_kst": match_datetime_kst.strftime("%Y-%m-%d"),
                        "time_kst": match_datetime_kst.strftime("%H:%M"),
                        "date_utc": match_datetime_utc.strftime("%Y-%m-%d"),
                        "time_utc": match_datetime_utc.strftime("%H:%M"),
                        "players": f"{player1} - {player2}",
                        "tournament": current_tournament
                    })

                i += 2
            except Exception as e:
                print("⚠️ 오류 발생:", e)
                i += 1
        else:
            i += 1

    # ✅ 저장
    result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "matches": matches
    }

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "tennis_explorer_schedule.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(matches)} matches saved to tennis_explorer_schedule.json")

def normalize(text):
    """소문자, 숫자만 남기고 나머지는 제거"""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def filter_today_matches_by_abstract_partial(today_data, bracket_data, output_filename="tennis_tournaments_pro_schedules.json"):
    matched_matches = []

    for match in today_data.get("matches", []):
        today_tournament_raw = match.get("tournament", "")

        # 🔥 challenger 필터 추가
        if "challenger" in today_tournament_raw.lower():
            continue  # 이 경기 무시하고 건너뜀

        today_tournament = normalize(today_tournament_raw)

        for bracket in bracket_data:
            bracket_tournament_raw = bracket.get("tournament", "")
            bracket_tournament = normalize(bracket_tournament_raw)

            if today_tournament and (today_tournament in bracket_tournament or bracket_tournament in today_tournament):
                matched_matches.append(match)
                break

    # ✅ date_kst를 matches에서 꺼냄
    date_kst = today_data["matches"][0].get("date_kst") if today_data.get("matches") else None

    output_path = os.path.join(base_dir, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"date": date_kst, "matches": matched_matches}, f, ensure_ascii=False, indent=2)

    print(f"✅ 매칭된 경기 저장 완료: {output_path}")
    return matched_matches

def fetch_youtube_videos(query, max_results=12):
    params = {
        "key": API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "relevance"
    }
    res = requests.get(SEARCH_URL, params=params)
    if res.status_code == 200:
        return res.json().get("items", [])
    else:
        print(f"❌ {query} 검색 실패: {res.status_code}")
        return []

def fetch_and_save_youtube_results_from_bracket(bracket_json_path="tennis_abstract_bracket.json", output_filename="tennis_tournaments_pro_data.json"):
    try:
        with open(bracket_json_path, "r", encoding="utf-8") as f:
            bracket_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일 없음: {bracket_json_path}")
        return

    tournaments = [item["tournament"] for item in bracket_data.get("data", [])]

    all_results = []
    for name in tournaments:
        print(f"🔍 {name} 관련 영상 검색 중...")
        items = fetch_youtube_videos(f"{name} tennis")
        videos = [{
            "tournament": name,
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "videoId": item["id"]["videoId"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "publishedAt": item["snippet"]["publishedAt"]
        } for item in items]
        all_results.append({
            "tournament": name,
            "videos": videos
        })

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump({
            "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": all_results
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 유튜브 검색 결과 저장 완료: {output_filename}")

# ✅ Google Translate API (v2) 직접 호출 방식
def translate_text(text, target="ko"):
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target,
        "format": "text",
        "key": API_KEY
    }
    response = requests.post(url, data=params)
    result = response.json()

    if "data" in result:
        return result["data"]["translations"][0]["translatedText"]
    else:
        print(f"❌ 번역 실패: {text} / 에러: {result}")
        return text

# ✅ 뉴스 RSS에서 기사 가져오기
def fetch_articles_for_tournament(tournament_name, max_results=10, days_limit=2):
    query = f"{tournament_name} tennis"
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    articles = []
    cutoff_date = datetime.utcnow() - timedelta(days=days_limit)

    for entry in feed.entries[:20]:
        try:
            published = datetime(*entry.published_parsed[:6])
        except:
            continue

        if published < cutoff_date:
            continue

        title_en = entry.title.strip()
        title_ko = translate_text(title_en)

        articles.append({
            "title_en": title_en,
            "title_ko": title_ko,
            "link": entry.link,
            "published": published.isoformat(),
            "source": entry.get("source", {}).get("title", "unknown")
        })

        if len(articles) >= max_results:
            break

    return articles

# ✅ JSON 파일 업데이트
def add_articles_to_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data.get("results", []):
        tournament_name = item.get("tournament")
        print(f"🔍 {tournament_name} 뉴스 수집 중...")
        item["articles"] = fetch_articles_for_tournament(tournament_name)

    data["executed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ 모든 기사 저장 완료!")

def add_summary_to_youtube_json(youtube_filename="tennis_tournaments_pro_data.json", combined_filename="static/combined_tennis_tournaments_2025.json"):
    youtube_path = os.path.join(base_dir, youtube_filename)
    combined_path = os.path.join(base_dir, combined_filename)

    # 🔄 파일 불러오기
    try:
        with open(youtube_path, "r", encoding="utf-8") as f:
            youtube_data = json.load(f)
        with open(combined_path, "r", encoding="utf-8") as f:
            combined_data = json.load(f)
    except Exception:
        logging.error("❌ summary 처리용 파일 열기 실패")
        save_error_to_json(traceback.format_exc(), source="add_summary_to_youtube_json")
        return

    def clean_name(name):
        return name.replace("ATP", "").replace("WTA", "").strip().lower()

    def extract_tour(name):
        if "WTA" in name.upper():
            return "WTA"
        elif "ATP" in name.upper():
            return "ATP"
        return None  # 아무것도 없으면 None 반환

    def generate_summary(t):
        return f"{t['Tournament']}는 {t['Period']} 동안 {t['Country']} {t['City']}에서 열리는 {t['Surface']} 코트 {t['Tour']} 대회입니다."

    for item in youtube_data.get("results", []):
        raw_name = item.get("tournament", "")
        tour_type = extract_tour(raw_name)
        base_name = clean_name(raw_name)

        matched = None

        # 🎯 해당 투어에 해당하는 데이터만 필터링
        tour_filtered = [t for t in combined_data if t.get("Tour", "").upper() == tour_type]

        # 1차: Tournament 이름 기준
        for t in tour_filtered:
            tour_name = clean_name(t["Tournament"])
            if (base_name == tour_name or base_name in tour_name or tour_name in base_name) and t.get("Tour", "").upper() == tour_type:
                matched = t
                break

        # 2차: City 기준
        if not matched:
            for t in tour_filtered:
                city = t.get("City", "").lower()
                if city and (city in base_name or base_name in city):
                    matched = t
                    break

        # 결과 저장
        item["summary"] = generate_summary(matched) if matched else f"❌ {raw_name}에 대한 대회 정보를 찾을 수 없습니다."

    # 🔄 저장
    with open(youtube_path, "w", encoding="utf-8") as f:
        json.dump(youtube_data, f, ensure_ascii=False, indent=2)

    logging.info("✅ summary 정보가 성공적으로 추가되었습니다.")


if __name__ == "__main__":
    print("🎾 테니스 크롤링 시작")

    # 1. 대회 정보 수집
    tournaments = fetch_current_tournaments()
    result = []

    for t in tournaments:
        try:
            print(f"🔍 {t['tournament']} 크롤링 중...")
            res = requests.get(t["url"], timeout=10)
            html = res.text
            upcoming = parse_matches(extract_match_html("upcomingSingles", html))
            completed = parse_matches(extract_match_html("completedSingles", html))
            result.append({
                "tournament": t["tournament"],
                "url": t["url"],
                "upcoming": upcoming,
                "completed": completed
            })
        except Exception:
            save_error_to_json(traceback.format_exc(), source=t["tournament"])

    # 2. ATP/WTA 분리 및 저장
    atp_only = [r for r in result if "ATP" in r["tournament"]]
    wta_only = [r for r in result if "WTA" in r["tournament"]]
    atp_wta_both = atp_only + wta_only
    save_results_to_json(atp_wta_both, "tennis_abstract_ATPandWTA.json")

    # 3. 브래킷 변환 및 저장
    bracket_formatted = convert_to_bracket_format(atp_wta_both)
    save_results_to_json(bracket_formatted, "tennis_abstract_bracket.json", add_executed_at=True)

    # 4. 오늘 경기 일정 수집 및 매칭
    fetch_all_atp_schedule_from_dom()
    today_path = os.path.join(base_dir, "tennis_explorer_schedule.json") 
    if os.path.exists(today_path):
        with open(today_path, "r", encoding="utf-8") as f:
            today_data = json.load(f)
        filter_today_matches_by_abstract_partial(today_data, bracket_formatted)

    # 5. 유튜브 검색 결과 저장
    fetch_and_save_youtube_results_from_bracket()

    # 6. summary 필드 추가
    add_summary_to_youtube_json()

    # 7. 기사 및 번역기사 관련 결과 저장
    add_articles_to_json("tennis_tournaments_pro_data.json")
    
    print("✅ 전체 작업 완료")

