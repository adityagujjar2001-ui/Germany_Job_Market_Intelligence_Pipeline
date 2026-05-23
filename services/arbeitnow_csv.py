import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://arbeitnow.com/api/job-board-api"
DEFAULT_LIMIT = 100
MAX_PAGES = 100
REQUEST_TIMEOUT = 30
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOCATION_FILTER = "Berlin"
SEARCH_QUERY = "IT"
API_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
IT_JOB_KEYWORDS = (
    r"IT|Python|Java|C\+\+|JavaScript|React|Node|DevOps|Cloud|AWS|Azure|Go|Rust|Kotlin|"
    r"Scala|Django|Flask|Spring|Angular|Vue|Docker|Kubernetes|Microservices|API|Backend|Frontend|Fullstack|"
    r"Software Engineer|Developer|Programmer|Data Scientist|Machine Learning Engineer|AI Engineer|Cloud Engineer|"
    r"DevOps Engineer|SRE|Site Reliability Engineer|System Administrator|Network Engineer|Security Engineer|Cybersecurity|"
    r"Information Security|Penetration Tester|Ethical Hacker|Security Analyst|Data Engineer|Big Data Engineer|"
    r"ETL Developer|Database Administrator|DBA|Business Intelligence Developer|BI Developer|Data Analyst|"
    r"Data Architect|Data Warehouse Engineer|Data Visualization|Tableau|Power BI|QlikView|Looker|Snowflake|"
    r"Redshift|BigQuery|Hadoop|Spark|Kafka|Scala|R|SAS|MATLAB|TensorFlow|PyTorch|Keras|Scikit-learn|XGBoost|"
    r"LightGBM|CatBoost"
)


def _result(success: bool, count: int = 0, message: str = "", file: str | None = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"success": success, "count": count, "message": message}
    if file:
        data["file"] = file
    return data


def fetch_paginated_jobs(page: int) -> tuple[List[Dict[str, Any]], int]:
    """Fetch a single ArbeitNow page."""
    params = {"page": page, "limit": DEFAULT_LIMIT, "search": SEARCH_QUERY, "location": LOCATION_FILTER}

    try:
        response = requests.get(BASE_URL, headers=API_HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json().get("data", []), response.status_code
        logger.warning("API returned status %s on page %s", response.status_code, page)
        return [], response.status_code
    except requests.exceptions.Timeout:
        logger.warning("Timeout while fetching page %s", page)
        return [], 408
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error on page %s: %s", page, exc)
        return [], 500


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Keep IT jobs in Berlin and remove duplicates."""
    if "title" in df.columns:
        df = df[df["title"].str.contains(IT_JOB_KEYWORDS, case=False, na=False, regex=True)]
        logger.info("Jobs after title filter: %s", len(df))
    if "location" in df.columns:
        df = df[df["location"].str.contains(LOCATION_FILTER, case=False, na=False)]
        logger.info("Jobs after location filter: %s", len(df))
    if "url" in df.columns:
        df = df.drop_duplicates(subset=["title", "url"], keep="first")
        logger.info("Jobs after deduplication: %s", len(df))
    return df


def save_jobs_to_csv(df: pd.DataFrame) -> str:
    """Save jobs dataframe to a timestamped CSV file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = DATA_DIR / f"arbeitnow_jobs_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
    df.to_csv(filename, index=False, encoding="utf-8")
    logger.info("Saved %s jobs to %s", len(df), filename)
    return str(filename)


def fetch_arbeitnow_jobs() -> Dict[str, Any]:
    """Fetch all Berlin IT jobs from ArbeitNow with pagination."""
    try:
        logger.info("Starting ArbeitNow API fetch for IT jobs in Berlin")
        all_jobs = []

        for page in range(1, MAX_PAGES + 1):
            logger.info("Fetching page %s...", page)
            jobs, _ = fetch_paginated_jobs(page)
            if not jobs:
                logger.info("No jobs on page %s. Pagination complete.", page)
                break
            all_jobs.extend(jobs)
            logger.info("Page %s: %s jobs fetched. Total: %s", page, len(jobs), len(all_jobs))
        else:
            page = MAX_PAGES + 1

        if not all_jobs:
            logger.warning("No IT jobs found in Berlin")
            return _result(False, message="No IT jobs in Berlin returned from API")

        df = pd.DataFrame(all_jobs)
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        df = filter_dataframe(df)

        if df.empty:
            logger.warning("No jobs remaining after filtering")
            return _result(False, message="No jobs matched the IT and Berlin filters")

        df["source"] = "ArbeitNow"
        filename = save_jobs_to_csv(df)
        pages_fetched = page - 1
        message = f"Fetched {len(df)} IT jobs in Berlin from {pages_fetched} pages"
        logger.info("✓ Successfully fetched %s IT jobs from Berlin (%s pages)", len(df), pages_fetched)
        return _result(True, len(df), message, filename)
    except requests.exceptions.Timeout:
        logger.error("Request timeout while fetching from ArbeitNow API")
        return _result(False, message="Request timeout while fetching from ArbeitNow API")
    except requests.exceptions.RequestException as exc:
        logger.error("Network error while fetching from ArbeitNow API: %s", exc)
        return _result(False, message=f"Network error: {exc}")
    except Exception as exc:
        logger.error("Unexpected error fetching ArbeitNow jobs: %s", exc)
        return _result(False, message=f"Error: {exc}")


if __name__ == "__main__":
    print(fetch_arbeitnow_jobs())
