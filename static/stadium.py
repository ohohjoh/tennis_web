import os
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import time
import urllib.parse
import re

# 이미지 저장 경로
IMAGE_DIR = os.path.join(os.getcwd(), 'images', 'stadium')
os.makedirs(IMAGE_DIR, exist_ok=True)

# 대회명 → 실제 스타디움명 매핑
STADIUM_MAP = {
    "Australian Open": "Rod Laver Arena",
    "Wimbledon": "Centre Court Wimbledon",
    "US Open": "Arthur Ashe Stadium",
    "Roland Garros": "Court Philippe Chatrier",
    "BNP Paribas Open": "Indian Wells Tennis Garden",
    "Mutua Madrid Open": "Caja Mágica",
    "Internazionali BNL d'Italia": "Foro Italico",
    "Nitto ATP Finals": "Pala Alpitour Turin"
}

# ✅ tournament_real_name과 동일한 파일명 생성 함수
def make_real_tournament_filename(t):
    name = t.get("Tournament", "").strip().lower()
    name = re.sub(r'\s+', '_', name)              # 공백 -> 언더스코어
    name = re.sub(r'[^\w\-]', '', name)           # 알파벳/숫자/언더스코어만 남김
    return name + ".png"

# ✅ 구글 이미지 검색 → 첫 이미지 URL 추출
def search_google_image(query):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote_plus(query)}"
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    img_tags = soup.find_all("img")
    for img_tag in img_tags:
        src = img_tag.get("src")
        if src and src.startswith("http"):
            return src
    return None

# ✅ JSON 로드
with open('combined_tennis_tournaments_2025.json', 'r', encoding='utf-8') as f:
    tournaments = json.load(f)

# ✅ 실행 루프
for t in tournaments:
    tournament_name = t.get("Tournament", "").strip()
    city = t.get("City", "").strip()
    country = t.get("Country", "").strip()

    if not tournament_name:
        continue

    filename = make_real_tournament_filename(t)
    save_path = os.path.join(IMAGE_DIR, filename)

    if os.path.exists(save_path):
        print(f"✅ 이미 존재: {filename}")
        continue

    stadium_name = STADIUM_MAP.get(tournament_name, tournament_name)
    query = f"{stadium_name} {city} {country} tennis stadium"
    print(f"🔍 Google 검색 중: {query}")

    img_url = search_google_image(query)

    if img_url:
        try:
            img_data = requests.get(img_url).content
            img = Image.open(BytesIO(img_data)).convert("RGB")
            img.save(save_path, format='PNG')
            print(f"📸 저장됨: {filename}")
        except Exception as e:
            print(f"⚠️ 저장 실패 ({tournament_name}): {e}")
    else:
        print(f"❌ 이미지 못 찾음: {tournament_name}")
    
    time.sleep(2)  # Google 차단 방지
