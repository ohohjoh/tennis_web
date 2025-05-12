import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FIREBASE_URL = "https://tennisweb-project-default-rtdb.firebaseio.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_UPLOAD = {
    "tennis_courts": os.path.join(BASE_DIR, "tenniscourt_with_guide.json"),
    "tennis_shops": os.path.join(BASE_DIR, "tennis_shop_info_cleaned.json"),
}

def upload_json_to_firebase(path_key, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        url = f"{FIREBASE_URL}/{path_key}.json"
        res = requests.put(url, json=data)
        if res.status_code == 200:
            print(f"✅ 업로드 성공: {path_key}")
        else:
            print(f"❌ 업로드 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 파일 업로드 중 오류 발생 ({path_key}): {e}")

def main():
    for key, filepath in FILES_TO_UPLOAD.items():
        if os.path.exists(filepath):
            upload_json_to_firebase(key, filepath)
        else:
            print(f"🚫 파일 없음: {filepath}")

if __name__ == "__main__":
    main()
