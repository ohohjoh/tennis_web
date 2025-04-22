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

if __name__ == "__main__":
    print("🎾 테니스 크롤링 시작")
    tournaments = fetch_current_tournaments()
    result = []

    for t in tournaments:
        try:
            print(f"🔍 {t['tournament']} 크롤링 중...")
            res = requests.get(t["url"], timeout=10)
            html = res.text
            upcoming = parse_matches(extract_match_html("upcomingSingles", html))
            completed = parse_matches(extract_match_html("completedSingles", html))
            result.append({"tournament": t["tournament"], "url": t["url"], "upcoming": upcoming, "completed": completed})
        except Exception:
            save_error_to_json(traceback.format_exc(), source=t["tournament"])

    atp_only = [r for r in result if "ATP" in r["tournament"]]
    wta_only = [r for r in result if "WTA" in r["tournament"]]
    atp_wta_both = atp_only + wta_only
    save_results_to_json(atp_wta_both, "tennis_abstract_ATPandWTA.json")

    bracket_formatted = convert_to_bracket_format(atp_wta_both)
    save_results_to_json(bracket_formatted, "tennis_abstract_bracket.json", add_executed_at=True)

    fetch_all_atp_schedule_from_dom()


    today_path = os.path.join(base_dir, "tennis_explorer_schedule.json") 
    if os.path.exists(today_path):
        with open(today_path, "r", encoding="utf-8") as f:
            today_data = json.load(f)
        filter_today_matches_by_abstract_partial(today_data, bracket_formatted)

    print("✅ 전체 작업 완료")
