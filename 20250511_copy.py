import json
import re
import time
import requests

KAKAO_API_KEY = "221f6a3b087520a072581787983ffccd"
headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}

# ✅ 주소 정제 함수
def clean_road_address(raw):
    match = re.match(r"^(.*?\d+)(\s|$)", raw)
    return match.group(1).strip() if match else raw.strip()

# ✅ 카카오 API 요청
def get_address_info(road_address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    params = {"query": road_address}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()

        # ✅ 디버그 출력
        print(f"🔍 [QUERY] {road_address}")
        print(f"📦 [RESPONSE] {json.dumps(result, ensure_ascii=False)}")

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

    except Exception as e:
        print(f"❌ [ERROR] 주소 요청 실패: {road_address}")
        print(f"   상태코드: {response.status_code if 'response' in locals() else 'N/A'}")
        print(f"   예외: {e}")
        return {
            "지번주소": "",
            "x": "",
            "y": ""
        }

# ✅ JSON 불러오기
with open("tennis_shop_info_cleaned.json", "r", encoding="utf-8") as f:
    shop_data = json.load(f)

# ✅ 처리 반복
for idx, shop in enumerate(shop_data, 1):
    raw_address = shop.get("주소", "")
    cleaned_address = clean_road_address(raw_address)
    result = get_address_info(cleaned_address)

    shop["정제주소"] = cleaned_address
    shop["지번주소"] = result["지번주소"]
    shop["x"] = result["x"]
    shop["y"] = result["y"]
    shop["주소2"] = shop["상호명"] if shop["상호명"] in raw_address else ""

    print(f"✅ [{idx}/{len(shop_data)}] 처리 완료: {shop['상호명']} ({'성공' if result['x'] else '실패'})")
    time.sleep(0.5)

# ✅ 결과 저장
with open("tennis_shops_with_coords_refined.json", "w", encoding="utf-8") as f:
    json.dump(shop_data, f, ensure_ascii=False, indent=2)

print("🎉 전체 완료!")
