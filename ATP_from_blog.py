import requests
import re
import json
from bs4 import BeautifulSoup
import os
import traceback
import logging
from collections import defaultdict

# 🎯 HTML에서 upcoming, completed match 문자열 추출
def extract_match_html(js_var_name, html):
    pattern = rf"var {js_var_name}\s*=\s*'(.*?)';"
    match = re.search(pattern, html, re.DOTALL)
    return match.group(1) if match else ""

# 👤 플레이어 문자열을 구조화
def normalize_player_name(player_str):
    seed_match = re.match(r"\((\d+|WC|Q|LL|Alt|PR)\)", player_str)
    seed = seed_match.group(1) if seed_match else None
    player_str = player_str[len(seed_match.group(0)):] if seed_match else player_str

    # 국가 추출
    country_match = re.search(r"\(([A-Z]{3})\)$", player_str)
    country = country_match.group(1) if country_match else None
    name = player_str[:country_match.start()].strip() if country_match else player_str.strip()

    return {
        "seed": seed,
        "name": name,
        "country": country
    }

# 🎾 HTML 안에서 match 한 줄씩 파싱
def parse_matches(html_block):
    soup = BeautifulSoup(html_block, "html.parser")
    matches = []

    for raw_line in soup.decode_contents().split("<br/>"):
        raw_line = raw_line.strip()
        if not raw_line or raw_line.startswith("&nbsp;"):
            continue

        # 🎯 HTML 태그 전부 제거한 텍스트로 정리
        clean_line = BeautifulSoup(raw_line, "html.parser").text.strip()

        # 🧠 정규식 파싱
        match = re.match(
            r"(?P<round>[A-Z0-9]+):\s+(?P<player1>.+?)\s+(?:d\.|vs)\s+(?P<player2>.+?)\s*(?P<score>\[\d.*?\])?$",
            clean_line
        )

        if match:
            p1 = match.group("player1").strip()
            p2 = match.group("player2").strip()
            score = match.group("score").strip("[]") if match.group("score") else None

            # 점수 문자열이 player2에 포함된 경우 분리 시도
            score_in_p2 = re.match(r"(.+?)\s+(\d{1,2}[-\d\(\)\sRET]*)$", p2)
            if score_in_p2:
                p2 = score_in_p2.group(1)
                score = score or score_in_p2.group(2)

            matches.append({
                "round": match.group("round"),
                "player1": normalize_player_name(p1),
                "player2": normalize_player_name(p2),
                "score": score
            })

    return matches

def fetch_current_tournaments():
    url = "https://www.tennisabstract.com/"
    res = requests.get(url)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", id="current-events")
    if not table:
        return []

    categories = ["WTA", "ATP", "Challenger"]
    tournament_data = []

    for col_idx, td in enumerate(table.find_all("td")):
        tour_type = categories[col_idx]

        current_b = None
        for elem in td.children:
            if elem.name == "b":
                current_b = elem.text.strip()
            elif elem.name == "a" and "Results and Forecasts" in elem.text:
                tournament_data.append({
                    "tournament": current_b,
                    "tour": tour_type,
                    "url": elem["href"]
                })

    return tournament_data
# 📄 에러 로그 저장
def save_error_to_json(error_trace, source="Unknown"):
    error_info = {
        "source": source,
        "error": error_trace
    }
    with open("error_log.json", "w", encoding="utf-8") as f:
        json.dump(error_info, f, ensure_ascii=False, indent=2)

# 📂 결과 저장
def save_results_to_json(data, filename="tennis_abstract_ATP.json"):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(base_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ 결과 저장 완료: {output_path}")
    except Exception:
        logging.error("❌ 결과 저장 실패")
        save_error_to_json(traceback.format_exc(), source="Result Saving")


def convert_to_bracket_format(data):
    from collections import defaultdict

    ISO3_TO_ISO2 = {
        "ESP": "ES", "AUS": "AU", "GBR": "GB", "GRE": "GR", "FRA": "FR", "RUS": "RU", "USA": "US",
        "DEN": "DK", "NOR": "NO", "SRB": "RS", "ARG": "AR", "ITA": "IT", "SUI": "CH", "NED": "NL",
        "BEL": "BE", "HUN": "HU", "GER": "DE", "COL": "CO", "CAN": "CA", "BIH": "BA", "CRO": "HR",
        "KAZ": "KZ", "TPE": "TW", "CHN": "CN", "JPN": "JP", "RSA": "ZA"
    }

    def country_to_flag(country_code_3):
        iso2 = ISO3_TO_ISO2.get(country_code_3, "")
        return ''.join([chr(ord(c) + 127397) for c in iso2]) if len(iso2) == 2 else ""

    bracket_data = []

    for tournament in data:
        round_dict = defaultdict(list)

        # 🎯 Completed 경기
        for match in tournament.get("completed", []):
            p1 = match["player1"]
            p2 = match["player2"]
            entry = {
                "player1": f"{country_to_flag(p1['country'])} {p1['name']}",
                "player2": f"{country_to_flag(p2['country'])} {p2['name']}",
                "score": match.get("score", ""),
                "winner": match.get("winner"),
                "source": "completed"
            }
            round_dict[match["round"]].append(entry)

        # 🎯 Upcoming 경기
        for match in tournament.get("upcoming", []):
            p1 = match["player1"]
            p2 = match["player2"]
            entry = {
                "player1": f"{country_to_flag(p1['country'])} {p1['name']}",
                "player2": f"{country_to_flag(p2['country'])} {p2['name']}",
                "score": match.get("score", ""),
                "winner": match.get("winner"),
                "source": "upcoming"
            }
            round_dict[match["round"]].append(entry)

        bracket_data.append({
            "tournament": tournament["tournament"],
            "url": tournament["url"],
            "bracket": dict(round_dict)
        })

    return bracket_data

# 🚀 메인 실행
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("🚀 대회 목록 가져오는 중...")
    tournaments = fetch_current_tournaments()
    result = []

    for t in tournaments:
        logging.info(f"🔎 크롤링 중: {t['tournament']}")
        try:
            res = requests.get(t["url"], timeout=10)
            html = res.text
            upcoming_html = extract_match_html("upcomingSingles", html)
            completed_html = extract_match_html("completedSingles", html)
            upcoming_matches = parse_matches(upcoming_html)
            completed_matches = parse_matches(completed_html)
            result.append({
                "tournament": t["tournament"],
                "url": t["url"],
                "upcoming": upcoming_matches,
                "completed": completed_matches
            })
        except Exception:
            logging.error(f"⚠️ {t['tournament']} 에서 오류 발생")
            save_error_to_json(traceback.format_exc(), source=t['tournament'])

    # 🎯 ATP만 필터링
    atp_results = [r for r in result if "ATP" in r["tournament"]]

    # 💾 저장
    save_results_to_json(atp_results, "tennis_abstract_ATP_only.json")
    save_results_to_json(convert_to_bracket_format(atp_results), "tennis_abstract_bracket.json")