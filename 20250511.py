import requests
import json
import time

# ✅ 카카오 REST API 키 설정
KAKAO_API_KEY = "5e421ef1b11912b75499e2b2c22ab565"
headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}

# ✅ 주소 검색 함수
def get_address_info(road_address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    params = {"query": road_address}
    response = requests.get(url, headers=headers, params=params)
    result = response.json()

    if result.get("documents"):
        doc = result["documents"][0]
        address_info = doc.get("address", {})
        return {
            "지번주소": address_info.get("address_name", ""),
            "x": doc.get("x", ""),
            "y": doc.get("y", "")
        }
    else:
        return {
            "지번주소": "",
            "x": "",
            "y": ""
        }

# ✅ 원본 JSON 불러오기
with open("tennis_shop_info_cleaned.json", "r", encoding="utf-8") as f:
    shop_data = json.load(f)

# ✅ 처리 반복
for shop in shop_data:
    road_address = shop.get("주소", "")
    result = get_address_info(road_address)
    shop["지번주소"] = result["지번주소"]
    shop["x"] = result["x"]
    shop["y"] = result["y"]

    # 주소2 간단 추출: 상호명이 주소에 포함될 경우
    if shop["상호명"] in road_address:
        shop["주소2"] = shop["상호명"]
    else:
        shop["주소2"] = ""

    print(f'✅ 처리 완료: {shop["상호명"]}')
    time.sleep(0.5)  # API 호출 제한 (초당 10회 이하)

# ✅ 결과 저장
with open("tennis_shops_with_coords.json", "w", encoding="utf-8") as f:
    json.dump(shop_data, f, ensure_ascii=False, indent=2)

print("🎉 전체 주소 변환 및 좌표 추가 완료!")
