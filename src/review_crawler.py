import argparse
import csv
import os
import time

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

RESULT_FIELDS = [
    "업소명", "작성자", "작성일", "리뷰", "태그",
    "총리뷰수", "해시태그참여수", "해시태그순위", "지도링크", "성공여부",
]


def _empty_result(place_name, status):
    return [{
        "업소명": place_name, "작성자": "", "작성일": "", "리뷰": "",
        "태그": "", "총리뷰수": "", "해시태그참여수": "", "해시태그순위": "",
        "지도링크": "", "성공여부": status,
    }]


def crawl_place_reviews(place_name, region="", max_reviews=200, chromedriver_path="chromedriver.exe"):
    """place_name(+region)으로 네이버 지도를 검색해 리뷰 목록을 반환한다."""
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
            print(f"검색 실패: {e}")
            return _empty_result(place_name, "X")

        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, "div.place_fixed_maintab a")
            review_tab = next((tab for tab in tabs if "리뷰" in tab.text), None)
            if not review_tab:
                print("리뷰탭 없음")
                return _empty_result(place_name, "X")
            driver.execute_script("arguments[0].click();", review_tab)
            time.sleep(2)
        except Exception as e:
            print(f"리뷰탭 클릭 오류: {e}")
            return _empty_result(place_name, "X")

        try:
            total_review = driver.find_element(By.CSS_SELECTOR, "div.jypaX > em").text
            hashtag_total = driver.find_element(By.CSS_SELECTOR, "div.jypaX > span").text
        except Exception:
            total_review = ""
            hashtag_total = ""

        hashtags = []
        for i in range(1, 11):
            try:
                tag = driver.find_element(By.CSS_SELECTOR, f"div.mrSZf > ul > li:nth-child({i}) span.t3JSf").text
                count = driver.find_element(By.CSS_SELECTOR, f"div.mrSZf > ul > li:nth-child({i}) span.CUoLy").text
                hashtags.append(f"{tag}({count})")
            except Exception:
                break
        hashtags_text = ", ".join(hashtags)

        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(15):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.3)

        while True:
            try:
                more_btn = driver.find_element(By.CSS_SELECTOR, "span.TeItc")
                if more_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", more_btn)
                    time.sleep(0.5)
                else:
                    break
            except Exception:
                break

        review_elems = driver.find_elements(By.CSS_SELECTOR, "li.place_apply_pui.EjjAW")
        for elem in review_elems[:max_reviews]:
            try:
                try:
                    inner_more = elem.find_element(By.CSS_SELECTOR, "a.pui__wFzIYl")
                    driver.execute_script("arguments[0].click();", inner_more)
                    time.sleep(0.3)
                except Exception:
                    pass

                html = elem.get_attribute("outerHTML")
                r = BeautifulSoup(html, "lxml")

                nickname = r.select_one("div.pui__JiVbY3 > span.pui__uslU0d")
                content = r.select_one("div.pui__vn15t2 > a:nth-child(1)")
                date = r.select_one("time")
                tags = r.select("div.pui__HLNvmI span")

                results.append({
                    "업소명": place_name,
                    "작성자": nickname.text.strip() if nickname else "",
                    "작성일": date.text.strip() if date else "",
                    "리뷰": content.text.strip() if content else "",
                    "태그": ", ".join(t.text.strip() for t in tags),
                    "총리뷰수": total_review,
                    "해시태그참여수": hashtag_total,
                    "해시태그순위": hashtags_text,
                    "지도링크": driver.current_url,
                    "성공여부": "",
                })
            except Exception as e:
                print(f"리뷰 수집 오류: {e}")

        if not results:
            status = "X"

    except Exception as e:
        print(f"전체 오류 발생: {e}")
        status = "X"
    finally:
        driver.quit()

    if not results:
        return _empty_result(place_name, status)
    return results


def run(input_csv, output_csv, name_col="업소명", region="", max_reviews=200,
        encoding="utf-8", chromedriver_path="chromedriver.exe"):
    df = pd.read_csv(input_csv, encoding=encoding)
    store_names = df[name_col].dropna().tolist()

    already_done = set()
    if os.path.exists(output_csv):
        old_df = pd.read_csv(output_csv, encoding="utf-8-sig")
        already_done = set(old_df["업소명"].unique())

    with open(output_csv, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if os.stat(output_csv).st_size == 0:
            writer.writeheader()

        for idx, name in enumerate(store_names, 1):
            if name in already_done:
                print(f"[{idx}/{len(store_names)}] 완료됨(건너뜀): {name}")
                continue

            print(f"[{idx}/{len(store_names)}] 리뷰 수집 중: {name}")
            for row in crawl_place_reviews(name, region=region, max_reviews=max_reviews,
                                            chromedriver_path=chromedriver_path):
                writer.writerow(row)

    print(f"전체 리뷰 크롤링 완료. 결과: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 지도 업소 리뷰 크롤러")
    parser.add_argument("--input", required=True, help="업소명 목록이 담긴 입력 CSV 경로")
    parser.add_argument("--output", required=True, help="결과를 저장할 CSV 경로")
    parser.add_argument("--name-col", default="업소명", help="입력 CSV에서 업소명 컬럼 이름 (기본: 업소명)")
    parser.add_argument("--region", default="", help="검색 정확도를 높이기 위한 지역명 (예: 충북, 광진구)")
    parser.add_argument("--max-reviews", type=int, default=200, help="업소당 최대 수집 리뷰 수")
    parser.add_argument("--encoding", default="utf-8", help="입력 CSV 인코딩")
    parser.add_argument("--chromedriver", default="chromedriver.exe", help="chromedriver 실행 파일 경로")
    args = parser.parse_args()

    run(args.input, args.output, name_col=args.name_col, region=args.region,
        max_reviews=args.max_reviews, encoding=args.encoding, chromedriver_path=args.chromedriver)
