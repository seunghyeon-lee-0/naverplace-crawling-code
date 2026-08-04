import argparse
import csv
import os
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def crawl_place_info(place_name, region="", include_home_tab=True, include_phone=True,
                      chromedriver_path="chromedriver.exe"):
    """place_name(+region)으로 네이버 지도를 검색해 주소/전화번호를 반환한다."""
    result = {"업소명": place_name, "주소": "", "전화번호": "", "성공여부": "X"}

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        query = f"{place_name} {region}".strip()
        driver.get(f"https://map.naver.com/v5/search/{query}")
        time.sleep(2.5)

        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe")))
        driver.switch_to.frame(iframe)

        first_result = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#_pcmap_list_scroll_container > ul > li:nth-child(1) a"))
        )
        driver.execute_script("arguments[0].click();", first_result)
        time.sleep(1.5)

        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))

        if include_home_tab:
            try:
                tabs = driver.find_elements(By.CSS_SELECTOR, "div.place_fixed_maintab a")
                home_tab = next((tab for tab in tabs if "홈" in tab.text), None)
                if home_tab:
                    driver.execute_script("arguments[0].click();", home_tab)
                    time.sleep(1.5)
            except Exception as e:
                print(f"홈 탭 클릭 실패: {e}")

        try:
            addr_span = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.LDgIH")))
            result["주소"] = addr_span.text.strip()
        except Exception as e:
            print(f"주소 수집 실패: {e}")

        if include_phone:
            try:
                tel_span = driver.find_element(By.CSS_SELECTOR, "span.xlx7Q")
                result["전화번호"] = tel_span.text.strip()
            except Exception as e:
                print(f"전화번호 수집 실패: {e}")

        if result["주소"] or result["전화번호"]:
            result["성공여부"] = "O"

    except Exception as e:
        print(f"{place_name} 정보 크롤링 실패: {e}")
    finally:
        driver.quit()

    return result


def run(input_csv, output_csv, name_col="업소명", region="", include_home_tab=True,
        include_phone=True, encoding="cp949", chromedriver_path="chromedriver.exe"):
    df = pd.read_csv(input_csv, encoding=encoding)
    store_names = df[name_col].dropna().unique().tolist()

    already_done = set()
    if os.path.exists(output_csv):
        old_df = pd.read_csv(output_csv, encoding="utf-8-sig")
        already_done = set(old_df["업소명"].unique())

    with open(output_csv, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["업소명", "주소", "전화번호", "성공여부"])
        if os.stat(output_csv).st_size == 0:
            writer.writeheader()

        for idx, name in enumerate(store_names, 1):
            if name in already_done:
                print(f"[{idx}/{len(store_names)}] 완료됨(건너뜀): {name}")
                continue

            print(f"[{idx}/{len(store_names)}] 업소 정보 수집 중: {name}")
            result = crawl_place_info(name, region=region, include_home_tab=include_home_tab,
                                       include_phone=include_phone, chromedriver_path=chromedriver_path)
            writer.writerow(result)

    print(f"전체 업소 정보 크롤링 완료. 결과: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 지도 업소 주소/전화번호 크롤러")
    parser.add_argument("--input", required=True, help="업소명 목록이 담긴 입력 CSV 경로")
    parser.add_argument("--output", required=True, help="결과를 저장할 CSV 경로")
    parser.add_argument("--name-col", default="업소명", help="입력 CSV에서 업소명 컬럼 이름 (기본: 업소명)")
    parser.add_argument("--region", default="", help="검색 정확도를 높이기 위한 지역명 (예: 충북, 광진구)")
    parser.add_argument("--no-home-tab", action="store_true", help="홈 탭 클릭 없이 바로 주소 수집")
    parser.add_argument("--no-phone", action="store_true", help="전화번호는 수집하지 않음")
    parser.add_argument("--encoding", default="cp949", help="입력 CSV 인코딩 (기본: cp949)")
    parser.add_argument("--chromedriver", default="chromedriver.exe", help="chromedriver 실행 파일 경로")
    args = parser.parse_args()

    run(args.input, args.output, name_col=args.name_col, region=args.region,
        include_home_tab=not args.no_home_tab, include_phone=not args.no_phone,
        encoding=args.encoding, chromedriver_path=args.chromedriver)
