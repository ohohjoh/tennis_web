from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def KATA():
    # 1. 셀레니움 드라이버 설정
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
)

    # 1. 페이지 이동
    driver.get("http://tennis.sportsdiary.co.kr/tennis/tnrequest/list.asp")
    time.sleep(3)  # 페이지 로딩 대기 (필요 시 WebDriverWait으로 대체 가능)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    base_selector = "#AppBody > div.l_apply_list > div:nth-child(2)"
    dd_elements = soup.select("div.competition_list > dl > dd")

    apply_selectors = []
    rule_selectors = []

    dd_elements = soup.select("div.competition_list > dl > dd")

    for idx, dd in enumerate(dd_elements, start=1):
        r_con = dd.select_one("span.r_con")
        if not r_con:
            continue

        links = r_con.find_all("a")
        for link_idx, a in enumerate(links, start=1):
            text = a.get_text(strip=True)

            # 신청하기
            if "신청하기" in text:
                selector = f"div.competition_list > dl > dd:nth-of-type({idx}) a.sm_btn.green_btn"
                apply_selectors.append(selector)

            # 요강보기
            elif "요강보기" in text and "href" in a.attrs:
                selector = f"div.competition_list > dl > dd:nth-of-type({idx}) a[href*='bo_table=program']"
                rule_selectors.append(selector)


    rule_result = []
    for selector in rule_selectors:

        # 1. 클릭하여 새 탭 열기
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()

        # 2. 탭 전환 (새 탭으로)
        driver.switch_to.window(driver.window_handles[-1])

        # 3. 두 개 요소 기다리기
        target_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "body > table > tbody > tr:nth-child(2) > td > table > tbody > tr > td:nth-child(4) > table > tbody > tr:nth-child(4) > td > table:nth-child(3) > tbody > tr > td > table:nth-child(2) > tbody > tr:nth-child(1) > td")
            )
        )
        target_elem0 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "body > table > tbody > tr:nth-child(2) > td > table > tbody > tr > td:nth-child(4) > table > tbody > tr:nth-child(4) > td > table:nth-child(3) > tbody > tr > td > table:nth-child(1) > tbody > tr > td > b > font")
            )
        )

        # 4. 텍스트 추출
        raw0_text = target_elem0.text.strip()
        raw_text = target_elem.text.strip()

        # 5. 대회명 처리: [] 제거, 공백 제거
        대회명 = re.sub(r"^\[.*?\]\s*", "", raw0_text).strip()

        # 6. 대회기간 처리
        match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", raw_text)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            대회기간 = f"{year}.{month}.{day}"
        else:
            대회기간 = ""

        # 7. JSON 형태로 저장
        rule_result.append({
            "대회명": 대회명,
            "대회기간": 대회기간
        })

        print(json.dumps(rule_result, ensure_ascii=False, indent=2))

        # 8. 탭 닫고 원래 탭으로 전환
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(2)

    apply_result = []
    for selector in apply_selectors:
        driver.get("http://tennis.sportsdiary.co.kr/tennis/tnrequest/list.asp")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
        
        # 4. 데이터 수집
        종류 = "복식"
        주관사 = "KATA"

        # 대회명과 그룹 추출
        span_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#frm_in > div.l_apply > div.deposit_info > span"))
        )        # 원래 span 전체 텍스트
        span_text = span_element.text.strip()

        # 대회명: 대괄호 [ ]로 감싼 부분과 그 뒤 공백 제거
        대회명 = re.sub(r"^\[.*?\]\s*", "", span_text).strip()

        match = re.search(r'\[(.*?)\]', span_text)
        그룹 = match.group(1).strip() if match else ""

        # 5. 부서 / 현원 / 정원
        option_elements = driver.find_elements(By.CSS_SELECTOR, "#levelno > option")

        for opt in option_elements:
            time.sleep(2)
            value = opt.get_attribute("value").strip()
            text = opt.text.strip()

            if not value:
                continue

            # ✅ 마지막 '/' 기준으로 정원/현원 추출
            numbers = re.findall(r"(\d+)\s*/\s*(\d+)(?![^()]*\))", text)
            if numbers:
                현원, 정원 = numbers[-1]  # 마지막 매칭만 사용
                # 부서는 숫자 제외 나머지 앞부분 추정
                부서 = re.split(r"\d+\s*/\s*\d+(?![^()]*\))", text)[0].strip()

                entry = {
                    "종류": 종류,
                    "주관사": 주관사,
                    "그룹": 그룹,
                    "대회명": 대회명,
                    "부서": 부서,
                    "현원": 현원,
                    "정원": 정원,
                    "참가신청 링크": 'http://tennis.sportsdiary.co.kr/tennis/tnrequest/list.asp'
                }

                # ✅ 여기서 대회명 일치하는 경우 대회기간 찾아서 추가
                matching = next((r for r in rule_result if r["대회명"] == 대회명), None)
                if matching:
                    entry["대회기간"] = matching["대회기간"]

                apply_result.append(entry)
            

    kata_result = apply_result
    driver.quit()
    return kata_result
    # print(json.dumps(kata_result, ensure_ascii=False, indent=2))
def KTA():

    # 1. 셀레니움 드라이버 설정
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
)

    url_main = 'https://join.kortennis.or.kr/index.do'
    url_tournaments = 'https://join.kortennis.or.kr/sportsForAll/sportsForAll.do?_code=10078'
    driver.get(url_main)
    driver.get(url_tournaments)
    # 2. #cnt03 탭 클릭
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#cnt03"))).click()
    time.sleep(2)  # 컨텐츠 로딩 대기

        # 3. tr 목록 안에 있는 h3 > a 태그 가져오기
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divisionLegList tbody tr")))

        # tr 갯수 구해서 nth-child로 selector 생성
    trs = driver.find_elements(By.CSS_SELECTOR, "#divisionLegList tbody tr")
    selector_list = []
    for i in range(1, len(trs) + 1):
        selector = f"#divisionLegList > tbody > tr:nth-child({i}) > td:nth-child(3) > div > button:nth-child(1)"
        try:
            driver.find_element(By.CSS_SELECTOR, selector)
            selector_list.append(selector)
        except:
            print(f"[스킵] {selector}")
            continue
 
    result_data = []
    for selector in selector_list:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
                
        # 공통 데이터 수집
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#group")))

        종류 = "복식"
        주관사 = "KTA"
        그룹 = driver.find_element(By.CSS_SELECTOR, "#group").text.strip()
        대회명 = driver.find_element(By.CSS_SELECTOR, "#cmptNm").text.strip()
        대회기간 = driver.find_element(By.CSS_SELECTOR, "#cmptDt").text.strip()
        장소 = driver.find_element(By.CSS_SELECTOR, "#place").text.strip()

        # 탭 전환
        tab_button = driver.find_element(By.CSS_SELECTOR, "#btnTab > div > div > div:nth-child(2) > div > li > a")
        driver.execute_script("arguments[0].click();", tab_button)
        time.sleep(1)

        # 부서별 정보 파싱
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cmptApplyEventList")))
        rows = driver.find_elements(By.CSS_SELECTOR, "#cmptApplyEventList > tr")

        for i in range(1, len(rows)+1):
            부서 = driver.find_element(By.CSS_SELECTOR, f"#cmptApplyEventList > tr:nth-child({i}) > td:nth-child(1)").text.strip()
            경기일시 = driver.find_element(By.CSS_SELECTOR, f"#cmptApplyEventList > tr:nth-child({i}) > td:nth-child(4)").text.strip()
            현정원 = driver.find_element(By.CSS_SELECTOR, f"#cmptApplyEventList > tr:nth-child({i}) > td:nth-child(6)").text.strip()
            
            if '/' in 현정원:
                현원, 정원 = [x.strip() for x in 현정원.split('/')]
            else:
                현원, 정원 = '', ''

            result_data.append({
                "종류": 종류,
                "주관사": 주관사,
                "그룹": 그룹,
                "대회명": 대회명,
                "대회기간": 대회기간,
                "장소": 장소,
                "부서": 부서,
                "경기일시": 경기일시,
                "현원": 현원,
                "정원": 정원,
                "참가신청 링크": "https://join.kortennis.or.kr/index.do",
            })
        driver.back()

    driver.quit()
    kta_result = result_data
    # 출력
    # import json
    # # print(json.dumps(kta_result, ensure_ascii=False, indent=2))
    return kta_result

    # 1. 인증
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("C:\\nimble-ally-440704-s8-cf38eae9319f.json", scope)
    client = gspread.authorize(creds)

    # 2. 스프레드시트 & 시트 열기
    sheet = client.open(sheet_name)
    source_ws = sheet.worksheet(source_title)

    try:
        target_ws = sheet.worksheet(target_title)
    except gspread.exceptions.WorksheetNotFound:
        target_ws = sheet.add_worksheet(title=target_title, rows="1000", cols="20")

    # 3. 전체 데이터 가져오기
    all_rows = source_ws.get_all_values()
    if not all_rows:
        print("⚠️ 소스 시트에 데이터 없음.")
        return

    header = all_rows[0]
    data_rows = all_rows[1:]

    # 4. 조건에 맞는 행 필터링 (현원 < 정원)
    available_rows = []
    for row in data_rows:
        try:
            current = int(row[8])  # I열 (현원)
            capacity = int(row[9]) # J열 (정원)
            if current < capacity:
                available_rows.append(row)
        except (IndexError, ValueError):
            continue  # 값이 없거나 숫자가 아닌 경우 무시

    # 5. '가능' 시트에 붙여 넣기 (헤더 + 행 추가)
    if available_rows:
        existing = target_ws.get_all_values()
        if not existing:
            target_ws.update("A1", [header])  # 헤더 없으면 추가

        start_row = len(existing) + 1
        target_ws.update(f"A{start_row}", available_rows)
        print(f"✅ {len(available_rows)}개 행이 '{target_title}' 시트에 추가됨.")
    else:
        print("ℹ️ 조건을 만족하는 행이 없음.")
def KATO():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://www.kato.kr/")
    wait = WebDriverWait(driver, 10)
    time.sleep(3)

    # 대회 버튼들 수집
    containers = driver.find_elements(By.CSS_SELECTOR, "div.gtco-services.gtco-section")
    tournaments = containers[1].find_elements(By.CSS_SELECTOR, "div.service-wrap > div.service")

    all_data = []

    for i in range(len(tournaments)):
        try:
            print(f"🔍 {i+1}번째 대회 클릭 중...")
            # 리스트 다시 수집 (StaleElementReference 해결)
            containers = driver.find_elements(By.CSS_SELECTOR, "div.gtco-services.gtco-section")
            tournaments = containers[1].find_elements(By.CSS_SELECTOR, "div.service-wrap > div.service")
            tournaments[i].click()
            time.sleep(2)

            try:
                tab = driver.find_element(By.CSS_SELECTOR, "#gameTap > li:nth-child(2) > a")
                tab.click()
                time.sleep(1)
            except Exception as e:
                print(f"❌ 참가신청 탭 클릭 실패: {e}")
                driver.back()
                time.sleep(2)
                continue

            title = driver.find_element(By.CSS_SELECTOR, "div.group-title").text.strip()
            rows = driver.find_elements(By.CSS_SELECTOR, "#tab2 > div > table > tbody > tr")

            for row in rows:
                try:
                    dept = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                    date = row.find_element(By.CSS_SELECTOR, "td.rightnone > div:nth-child(1)").text.strip()
                    location = row.find_element(By.CSS_SELECTOR, "td.rightnone > div.place").text.strip()

                    print(f"📅 원본 date: {date}")  # ✅ 날짜 원본 로그 확인

                    # ✅ 날짜 정제
                    match = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", date)
                    if match:
                        formatted_date = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
                    else:
                        formatted_date = date  # 변환 실패 시 원본 사용
                    print(f"✅ 변환된 formatted_date: {formatted_date}")  # ✅ 확인용

                    take_span = row.find_elements(By.CSS_SELECTOR, "td.leftnone > span.takeparting, td.leftnone > span.takepartingOver")
                    if take_span:
                        now, total = [x.strip() for x in take_span[0].text.strip().split('/')]
                    else:
                        now, total = '', ''
                        
                    all_data.append({
                        "종류": "복식",
                        "주관사": "KATO",
                        "대회명": title,
                        "대회기간": formatted_date,
                        "장소": location,
                        "부서": dept,
                        "경기일시": formatted_date,
                        "현원": now,
                        "정원": total,
                    })
                except Exception as e:
                    print(f"⚠️ 행 파싱 실패: {e}")
            driver.back()
            time.sleep(2)

        except Exception as e:
            print(f"❌ 대회 클릭 실패: {e}")

    driver.quit()
    with open("kato_tournaments.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 데이터 수집 완료. 결과 항목 수: {len(all_data)}")
    print(all_data)

    kato_result = all_data

    print(f"✅ 데이터 수집 완료. 결과 항목 수: {len(all_data)}")
    return kato_result



if __name__ == "__main__":
    start_time = time.time()  # 시작 시간 기록

    # 결과 수집
    kata_result = KATA()
    kta_result = KTA()
    kato_result = KATO()

    # 통합 결과
    all_results = kata_result + kta_result + kato_result

    # JSON 저장
    output_path = os.path.join(os.getcwd(), "tennis_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    end_time = time.time()  # 종료 시간 기록
    elapsed = end_time - start_time

    print(f"✅ 크롤링 결과 저장 완료: {output_path}")
    print(f"⏱️ 총 소요 시간: {elapsed:.2f}초")