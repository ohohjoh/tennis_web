import logging
import traceback
import json
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "crawler_log.txt"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"  # ✅ 인코딩 명시!
)

def save_error_to_json(error_msg, source="KATA"):
    error_log = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "error": error_msg
    }
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "errors.json"), "a", encoding="utf-8") as f:
        json.dump(error_log, f, ensure_ascii=False)
        f.write("\n")

# === 메인 KATA 함수 ===
def KATA():

    logging.info("KATA 크롤링 시작")
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument('--ignore-certificate-errors')  # ← 이 줄 추가
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(r'C:\\chromedriver.exe')
        driver = webdriver.Chrome(service = service)

        driver.get("http://tennis.sportsdiary.co.kr/tennis/tnrequest/list.asp")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.competition_list > dl > dd"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        dd_elements = soup.select("div.competition_list > dl > dd")

        apply_selectors = []
        rule_selectors = []

        for idx, dd in enumerate(dd_elements, start=1):
            r_con = dd.select_one("span.r_con")
            if not r_con:
                continue
            links = r_con.find_all("a")
            for a in links:
                text = a.get_text(strip=True)
                if "신청하기" in text:
                    apply_selectors.append(
                        f"div.competition_list > dl > dd:nth-of-type({idx}) a.sm_btn.green_btn")
                elif "요강보기" in text and "href" in a.attrs:
                    rule_selectors.append(
                        f"div.competition_list > dl > dd:nth-of-type({idx}) a[href*='bo_table=program']")

        rule_result = []
        for selector in rule_selectors:
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
                driver.switch_to.window(driver.window_handles[-1])

                target_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body > table > tbody > tr:nth-child(2) > td > table > tbody > tr > td:nth-child(4) > table > tbody > tr:nth-child(4) > td > table:nth-child(3) > tbody > tr > td > table:nth-child(2) > tbody > tr:nth-child(1) > td"))
                )
                target_elem0 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body > table > tbody > tr:nth-child(2) > td > table > tbody > tr > td:nth-child(4) > table > tbody > tr:nth-child(4) > td > table:nth-child(3) > tbody > tr > td > table:nth-child(1) > tbody > tr > td > b > font"))
                )

                raw0_text = target_elem0.text.strip()
                raw_text = target_elem.text.strip()

                대회명 = re.sub(r"^\[.*?\]\s*", "", raw0_text).strip()
                match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", raw_text)
                if match:
                    year = match.group(1)
                    month = match.group(2).zfill(2)
                    day = match.group(3).zfill(2)
                    대회기간 = f"{year}.{month}.{day}"
                else:
                    대회기간 = ""

                rule_result.append({
                    "대회명": 대회명,
                    "대회기간": 대회기간
                })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

            except Exception as e:
                err_msg = traceback.format_exc()
                logging.warning(f"[요강 파싱 오류] {err_msg}")
                save_error_to_json(err_msg, source="KATA - 요강탭")

        apply_result = []
        for selector in apply_selectors:
            try:
                driver.get("http://tennis.sportsdiary.co.kr/tennis/tnrequest/list.asp")
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()

                종류 = "복식"
                주관사 = "KATA"
                span_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#frm_in > div.l_apply > div.deposit_info > span"))
                )
                span_text = span_element.text.strip()
                대회명 = re.sub(r"^\[.*?\]\s*", "", span_text).strip()
                match = re.search(r'\[(.*?)\]', span_text)
                그룹 = match.group(1).strip() if match else ""

                option_elements = driver.find_elements(By.CSS_SELECTOR, "#levelno > option")

                for opt in option_elements:
                    time.sleep(1)
                    value = opt.get_attribute("value").strip()
                    text = opt.text.strip()
                    if not value:
                        continue
                    numbers = re.findall(r"(\d+)\s*/\s*(\d+)(?![^()]*\))", text)
                    if numbers:
                        현원, 정원 = numbers[-1]
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
                        matching = next((r for r in rule_result if r["대회명"] == 대회명), None)
                        if matching:
                            entry["대회기간"] = matching["대회기간"]
                        apply_result.append(entry)
            except Exception as e:
                err_msg = traceback.format_exc()
                logging.warning(f"[신청탭 파싱 오류] {err_msg}")
                save_error_to_json(err_msg, source="KATA - 신청탭")

        logging.info(f"KATA 크롤링 완료 / 총 항목 수: {len(apply_result)}")
        return apply_result

    except Exception as e:
        err_msg = traceback.format_exc()
        logging.error(f"KATA 전체 오류: {err_msg}")
        save_error_to_json(err_msg, source="KATA")
        return []

    finally:
        if driver:
            driver.quit()


def KTA():
    logging.info("KTA 크롤링 시작")
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(r'C:\\chromedriver.exe')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url_main = 'https://join.kortennis.or.kr/index.do'
        url_tournaments = 'https://join.kortennis.or.kr/sportsForAll/sportsForAll.do?_code=10078'
        driver.get(url_main)
        driver.get(url_tournaments)

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#cnt03"))).click()
        time.sleep(2)

        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divisionLegList tbody tr")))
        trs = driver.find_elements(By.CSS_SELECTOR, "#divisionLegList tbody tr")
        selector_list = []

        for i in range(1, len(trs) + 1):
            selector = f"#divisionLegList > tbody > tr:nth-child({i}) > td:nth-child(3) > div > button:nth-child(1)"
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                selector_list.append(selector)
            except:
                logging.warning(f"[스킵] {selector}")
                continue

        result_data = []
        for selector in selector_list:
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#group")))

                종류 = "복식"
                주관사 = "KTA"
                그룹 = driver.find_element(By.CSS_SELECTOR, "#group").text.strip()
                대회명 = driver.find_element(By.CSS_SELECTOR, "#cmptNm").text.strip()
                대회기간 = driver.find_element(By.CSS_SELECTOR, "#cmptDt").text.strip()
                장소 = driver.find_element(By.CSS_SELECTOR, "#place").text.strip()

                tab_button = driver.find_element(By.CSS_SELECTOR, "#btnTab > div > div > div:nth-child(2) > div > li > a")
                driver.execute_script("arguments[0].click();", tab_button)
                time.sleep(1)

                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cmptApplyEventList")))
                rows = driver.find_elements(By.CSS_SELECTOR, "#cmptApplyEventList > tr")

                for i in range(1, len(rows)+1):
                    try:
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
                    except Exception as e:
                        err_msg = traceback.format_exc()
                        logging.warning(f"[KTA 부서별 항목 파싱 오류] {err_msg}")
                        save_error_to_json(err_msg, source="KTA - 부서 파싱")
                driver.back()

            except Exception as e:
                err_msg = traceback.format_exc()
                logging.warning(f"[KTA 개별 대회 진입 오류] {err_msg}")
                save_error_to_json(err_msg, source="KTA - 개별 대회")

        logging.info(f"KTA 크롤링 완료 / 총 항목 수: {len(result_data)}")
        return result_data

    except Exception as e:
        err_msg = traceback.format_exc()
        logging.error(f"KTA 전체 오류: {err_msg}")
        save_error_to_json(err_msg, source="KTA")
        return []

    finally:
        if driver:
            driver.quit()

    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument('--ignore-certificate-errors')  # ← 이 줄 추가
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(r'C:\\chromedriver.exe')
    driver = webdriver.Chrome(service = service)

    driver.get("https://www.kato.kr/")
    time.sleep(2)

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
def KATO():
    logging.info("KATO 크롤링 시작")
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(r'C:\\chromedriver.exe')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get("https://www.kato.kr/")
        time.sleep(2)

        containers = driver.find_elements(By.CSS_SELECTOR, "div.gtco-services.gtco-section")
        tournaments = containers[1].find_elements(By.CSS_SELECTOR, "div.service-wrap > div.service")
        all_data = []

        for i in range(len(tournaments)):
            try:
                logging.info(f"{i+1}번째 대회 클릭 시도")
                containers = driver.find_elements(By.CSS_SELECTOR, "div.gtco-services.gtco-section")
                tournaments = containers[1].find_elements(By.CSS_SELECTOR, "div.service-wrap > div.service")
                tournaments[i].click()
                time.sleep(2)

                try:
                    tab = driver.find_element(By.CSS_SELECTOR, "#gameTap > li:nth-child(2) > a")
                    tab.click()
                    time.sleep(1)
                except Exception as e:
                    err_msg = traceback.format_exc()
                    logging.warning(f"[참가신청 탭 클릭 실패] {err_msg}")
                    save_error_to_json(err_msg, source="KATO - 참가신청 탭")
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

                        match = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", date)
                        formatted_date = f"{match.group(1)}.{match.group(2)}.{match.group(3)}" if match else date

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
                            "참가신청 링크": "https://www.kato.kr/"
                        })

                    except Exception as e:
                        err_msg = traceback.format_exc()
                        logging.warning(f"[KATO 행 파싱 오류] {err_msg}")
                        save_error_to_json(err_msg, source="KATO - row")

                driver.back()
                time.sleep(2)

            except Exception as e:
                err_msg = traceback.format_exc()
                logging.warning(f"[KATO 대회 클릭 오류] {err_msg}")
                save_error_to_json(err_msg, source="KATO - 대회 클릭")

        logging.info(f"KATO 크롤링 완료 / 총 항목 수: {len(all_data)}")
        return all_data

    except Exception as e:
        err_msg = traceback.format_exc()
        logging.error(f"KATO 전체 오류: {err_msg}")
        save_error_to_json(err_msg, source="KATO")
        return []

    finally:
        if driver:
            driver.quit()



if __name__ == "__main__":
    logging.info("=== 크롤링 작업 시작 ===")
    start_time = time.time()

    all_results = []

    for source, func in [("KATA", KATA), ("KTA", KTA), ("KATO", KATO)]:
        try:
            logging.info(f"{source} 시작")
            result = func()
            logging.info(f"{source} 완료 / 수집 항목 수: {len(result)}")
            all_results.extend(result)
        except Exception as e:
            err_msg = traceback.format_exc()
            save_error_to_json(err_msg, source=source)
            logging.error(f"{source} 중 치명적 오류 발생")

    output_path = os.path.join(os.getcwd(), "tennis_results.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ 결과 저장 완료: {output_path}")
    except Exception as e:
        save_error_to_json(traceback.format_exc(), source="Result Saving")

    elapsed = time.time() - start_time
    logging.info(f"⏱️ 전체 소요 시간: {elapsed:.2f}초")
    logging.info("=== 크롤링 작업 종료 ===")