# 🗺️ Naver Place(네이버 플레이스) Crawling Module

This repository contains the data collection and crawling modules for a framework that automatically recommends new candidate businesses for Korea’s Good Price Store program.

Previously, separate crawling scripts had to be written repeatedly for each region and collection period. These scripts have been consolidated into reusable modules that accept parameters such as region names and column names.

## 🧩 Components

| File                        | Description                                                                  |
| --------------------------- | ---------------------------------------------------------------------------- |
| `src/menu_crawler.py`       | Crawls business menu items and prices                                        |
| `src/review_crawler.py`     | Crawls business reviews, including author, date, content, tags, and hashtags |
| `src/place_info_crawler.py` | Crawls business addresses and phone numbers                                  |
| `src/geocode_kakao.py`      | Converts addresses into geographic coordinates using the Kakao Local API     |

All crawlers use Selenium and follow the same general workflow:

1. Search `https://map.naver.com/v5/search/{business_name} {region_name}`
2. Open the first search result
3. Navigate to the required tab, such as Menu, Reviews, or Home
4. Collect the relevant information

## ⚙️ Installation

```bash
pip install -r requirements.txt
```

Download a version of [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) that matches your installed Chrome version.

Place the driver in the project root or another directory, and specify its location using the `--chromedriver` argument.

## 🚀 Usage Examples

```bash
# Crawl menu items and prices
python src/menu_crawler.py --input data/sample_stores.csv --output menu_result.csv --region Seoul Gwangjin-gu

# Crawl reviews, up to 100 reviews per business
python src/review_crawler.py --input data/sample_stores.csv --output review_result.csv --region Seoul Gwangjin-gu --max-reviews 100

# Crawl addresses and phone numbers
python src/place_info_crawler.py --input data/sample_stores.csv --output info_result.csv --region Seoul Gwangjin-gu

# Geocoding using the Kakao Local API
export KAKAO_API_KEY="your_api_key"
python src/geocode_kakao.py --input data/sample_stores.csv --output geo_result.csv --region Seoul Gwangjin-gu
```

If the output CSV file already exists, each script skips businesses that have already been processed and resumes collecting data from the remaining entries.

This makes it possible to restart the crawler after an interruption without collecting the same data again.

## 📁 Repository Structure

```text
naver_crawling_code/
├── README.md
├── requirements.txt
├── .gitignore
├── src/                        # Crawling scripts tracked by Git
│   ├── menu_crawler.py         # Crawls business menu items and prices
│   ├── review_crawler.py       # Crawls business reviews
│   ├── place_info_crawler.py   # Crawls business addresses and phone numbers
│   └── geocode_kakao.py        # Geocoding using the Kakao Local API
├── data/
│   └── sample_stores.csv       # Anonymized sample data tracked by Git
└── archive_data/               # Local archive excluded from Git via .gitignore
    ├── chungcheongbuk-do/      # Final datasets and EDA notebooks from the Chungbuk HUB project
    └── seoul-gwangjin-gu/      # Final datasets and EDA notebooks from the Seoul Gwangjin-gu project
```

The `archive_data/` directory is used as a local archive for final outputs from the two regional projects that may be useful for future reference.

It contains selected datasets, including menu data, reviews, business information, sentiment analysis results, recommendation lists, and EDA notebooks used to inspect the results.

Because these files may contain personal information, such as phone numbers, the directory is excluded from Git and is not uploaded to the repository.

## ⚠️ Notes and Limitations

* The crawlers were developed based on the Naver Place interface available in 2025. They may stop working if Naver changes its page structure or markup.
* The code depends on DOM class names used by Naver Maps, such as `meDTN` and `LDgIH`. If a selector no longer works, it must be updated to match the latest page markup.
* Sensitive information, including Kakao API keys, must never be hard-coded into the source code. Use environment variables instead.
* Actual crawling results may contain personal information, such as phone numbers, and are therefore excluded from Git through `.gitignore`.
