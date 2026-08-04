import argparse
import csv
import os
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def crawl_place_menu(place_name, region="", chromedriver_path="chromedriver.exe"):
    """place_name(+region)으로 네이버 지도를 검색해 메뉴명/가격 목록을 반환한다."""
    results = []
    status = ""

    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        query = f"{place_name} {region}".strip()
        driver.get(f"https://map.naver.com/v5/search/{query}")
        time.sleep(2.5)

        try:
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe")))
            driver.switch_to.frame(iframe)
            first_result = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#_pcmap_list_scroll_container > ul > li:nth-child(1) a"))
            )
            driver.execute_script("arguments[0].click();", first_result)
            time.sleep(1.5)

            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))
        except Exception as e:
            print(f"검색 결과 클릭 실패: {e}")
            return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": "", "성공여부": "X"}]

        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, "div.place_fixed_maintab a")
            menu_tab = next((tab for tab in tabs if "메뉴" in tab.text), None)
            if not menu_tab:
                print("메뉴 탭 없음")
                return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": driver.current_url, "성공여부": "X"}]
            driver.execute_script("arguments[0].click();", menu_tab)
            time.sleep(2)
        except Exception as e:
            print(f"메뉴 탭 클릭 오류: {e}")
            return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": driver.current_url, "성공여부": "X"}]

        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(15):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.4)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul li a div.meDTN")))
        except Exception as e:
            print(f"메뉴 항목 로딩 대기 실패: {e}")
            return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": driver.current_url, "성공여부": "X"}]

        menu_items = driver.find_elements(By.CSS_SELECTOR, "ul li a div.meDTN")
        prices = driver.find_elements(By.CSS_SELECTOR, "ul li a div.GXS1X em")

        if not menu_items:
            print("메뉴 항목 없음")
            return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": driver.current_url, "성공여부": "X"}]

        for i, item in enumerate(menu_items):
            try:
                spans = item.find_elements(By.TAG_NAME, "span")
                menu_name = ""
                for span in spans:
                    if span.text.strip() and not span.find_elements(By.TAG_NAME, "svg") and span.text.strip() != "대표":
                        menu_name = span.text.strip()
                        break

                price = prices[i].text.strip() if i < len(prices) else ""
                if menu_name:
                    results.append({
                        "업소명": place_name,
                        "메뉴명": menu_name,
                        "가격": price,
                        "지도링크": driver.current_url,
                        "성공여부": "",
                    })
            except Exception as e:
                print(f"메뉴 항목 파싱 실패: {e}")

    except Exception as e:
        print(f"{place_name} 메뉴 크롤링 실패: {e}")
        status = "X"
        results = [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": driver.current_url, "성공여부": status}]
    finally:
        time.sleep(1)
        driver.quit()

    if not results:
        return [{"업소명": place_name, "메뉴명": "", "가격": "", "지도링크": "", "성공여부": status or "X"}]
    return results


def run(input_csv, output_csv, name_col="업소명", region="", encoding="cp949", chromedriver_path="chromedriver.exe"):
    df = pd.read_csv(input_csv, encoding=encoding)
    store_names = df[name_col].dropna().tolist()

    already_done = set()
    if os.path.exists(output_csv):
        old_df = pd.read_csv(output_csv, encoding="utf-8-sig")
        already_done = set(old_df["업소명"].unique())

    with open(output_csv, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["업소명", "메뉴명", "가격", "지도링크", "성공여부"])
        if os.stat(output_csv).st_size == 0:
            writer.writeheader()

        for idx, name in enumerate(store_names, 1):
            if name in already_done:
                print(f"[{idx}/{len(store_names)}] 완료됨(건너뜀): {name}")
                continue

            print(f"[{idx}/{len(store_names)}] 메뉴 수집 중: {name}")
            for row in crawl_place_menu(name, region=region, chromedriver_path=chromedriver_path):
                writer.writerow(row)

    print(f"전체 메뉴 크롤링 완료. 결과: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 지도 업소 메뉴 크롤러")
    parser.add_argument("--input", required=True, help="업소명 목록이 담긴 입력 CSV 경로")
    parser.add_argument("--output", required=True, help="결과를 저장할 CSV 경로")
    parser.add_argument("--name-col", default="업소명", help="입력 CSV에서 업소명 컬럼 이름 (기본: 업소명)")
    parser.add_argument("--region", default="", help="검색 정확도를 높이기 위한 지역명 (예: 충북, 광진구)")
    parser.add_argument("--encoding", default="cp949", help="입력 CSV 인코딩 (기본: cp949)")
    parser.add_argument("--chromedriver", default="chromedriver.exe", help="chromedriver 실행 파일 경로")
    args = parser.parse_args()

    run(args.input, args.output, name_col=args.name_col, region=args.region,
        encoding=args.encoding, chromedriver_path=args.chromedriver)
