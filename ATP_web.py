from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json

def fetch_flashscore_tennis_html() -> str:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1280x800")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.flashscore.com/tennis/")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "event__match"))
        )
    except Exception as e:
        print("⚠️ 로딩 대기 중 오류:", e)

    html = driver.page_source
    driver.quit()
    return html

def parse_flashscore_matches(html: str):
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    current_tournament = ""

    # header와 match가 섞여있으므로 모두 순회
    for elem in soup.select("div.event__match, div.event__header"):
        if "event__header" in elem.get("class", []):
            current_tournament = elem.get_text(strip=True)
        elif "event__match" in elem.get("class", []):
            try:
                time_elem = elem.select_one("div.event__time")
                player1 = elem.select_one("div.event__participant--home").get_text(strip=True)
                player2 = elem.select_one("div.event__participant--away").get_text(strip=True)
                status_class = elem.get("class", [])

                match_info = {
                    "tournament": current_tournament,
                    "time": time_elem.get_text(strip=True) if time_elem else "",
                    "player1": player1,
                    "player2": player2,
                    "status": "Live" if "event__match--live" in status_class else "Scheduled"
                }
                matches.append(match_info)
            except Exception:
                continue

    return matches


def save_matches_to_json(matches, filename="flashscore_tennis_matches.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    html = fetch_flashscore_tennis_html()
    matches = parse_flashscore_matches(html)
    save_matches_to_json(matches)
    print(f"✅ {len(matches)}개의 경기 정보를 flashscore_tennis_matches.json에 저장했습니다. (with tournament)")
