import argparse
import os
import time

import pandas as pd
import requests

API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def geocode_kakao(query, api_key):
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query}
    response = requests.get(API_URL, headers=headers, params=params, timeout=10)

    if response.status_code == 200:
        documents = response.json().get("documents", [])
        if documents:
            doc = documents[0]
            return {
                "입력값": query,
                "정식명칭": doc.get("place_name", ""),
                "도로명주소": doc.get("road_address_name", ""),
                "지번주소": doc.get("address_name", ""),
                "경도": doc.get("x", ""),
                "위도": doc.get("y", ""),
            }

    return {"입력값": query, "정식명칭": None, "도로명주소": None, "지번주소": None, "경도": None, "위도": None}


def run(input_csv, output_csv, name_col="업소명", region="", encoding="cp949", api_key=None):
    api_key = api_key or os.environ.get("KAKAO_API_KEY")
    if not api_key:
        raise SystemExit("카카오 API 키가 필요합니다. --api-key 또는 환경변수 KAKAO_API_KEY 를 설정하세요.")

    df = pd.read_csv(input_csv, encoding=encoding)
    unique_places = df[name_col].dropna().unique()
    queries = [f"{name} {region}".strip() for name in unique_places]

    results = []
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {query}")
        results.append(geocode_kakao(query, api_key))
        time.sleep(0.3)

    pd.DataFrame(results).to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="카카오 로컬 API 지오코딩")
    parser.add_argument("--input", required=True, help="업소명 목록이 담긴 입력 CSV 경로")
    parser.add_argument("--output", required=True, help="결과를 저장할 CSV 경로")
    parser.add_argument("--name-col", default="업소명", help="입력 CSV에서 업소명 컬럼 이름 (기본: 업소명)")
    parser.add_argument("--region", default="", help="검색 정확도를 높이기 위한 지역명 (예: 충북, 광진구)")
    parser.add_argument("--encoding", default="cp949", help="입력 CSV 인코딩 (기본: cp949)")
    parser.add_argument("--api-key", default=None, help="카카오 REST API 키 (미지정 시 KAKAO_API_KEY 환경변수 사용)")
    args = parser.parse_args()

    run(args.input, args.output, name_col=args.name_col, region=args.region,
        encoding=args.encoding, api_key=args.api_key)
