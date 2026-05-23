import random
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://www.stepstone.de/jobs/in-berlin?action=facet_selected%3bdisciplines%3bIT&di=IT"
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"

for directory in (DATA_DIR, RAW_HTML_DIR):
    directory.mkdir(parents=True, exist_ok=True)

ua = UserAgent()
HEADERS = {"User-Agent": ua.random}
REMOTE_PATTERN = re.compile(
    r"home[- ]?office|homeoffice|home office|remote|teilweise home-office|hybrid|telearbeit|"
    r"vollst[äa]ndig remote|vollst[äa]ndig homeoffice",
    re.I,
)
SKILL_CLASS_PATTERN = re.compile(r"skill|tag|badge|requirement", re.I)
DATE_PATTERN = re.compile(r"vor|ago|gestern|today", re.I)
TRANSLATION_CACHE = {}


def build_timestamped_path(prefix: str = "stepstone_jobs"):
    return DATA_DIR / f"{prefix}_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"


def random_delay():
    """Add random delay to avoid detection."""
    time.sleep(random.uniform(2, 5))


def sanitize_text(text):
    return text.strip() if text and isinstance(text, str) else None


def extract_remote(card):
    """Detect remote or work-from-home text in a job card."""
    if not card:
        return False
    text = card.get_text(separator=" ", strip=True)
    return bool((text and REMOTE_PATTERN.search(text)) or card.find(string=REMOTE_PATTERN))


def extract_date_posted(date_text):
    """Extract job posted date."""
    return date_text.strip() if date_text else None


def extract_skills(card):
    """Extract short skill/tag/badge text from a job card."""
    skills = [
        elem.get_text(strip=True)
        for elem in card.find_all(["span", "div"], {"class": SKILL_CLASS_PATTERN})
        if elem.get_text(strip=True) and len(elem.get_text(strip=True)) < 50
    ]
    return ", ".join(skills) if skills else None


def translate_text(text, target_lang="en"):
    """Translate text from German to English using Google Translate."""
    if not text or not text.strip():
        return text

    cache_key = (text, target_lang)
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]

    translated = text
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": target_lang, "dt": "t", "q": text},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data and isinstance(data[0], list):
            translated = "".join(item[0] for item in data[0] if item and item[0]) or text
    except Exception:
        translated = text

    TRANSLATION_CACHE[cache_key] = translated
    return translated


def build_page_url(page_number):
    """Build URL for the given page number."""
    return BASE_URL if page_number == 1 else f"{BASE_URL}{'&' if '?' in BASE_URL else '?'}page={page_number}"


def _element_text(card, selector, default=None):
    element = card.select_one(selector)
    return sanitize_text(element.get_text(strip=True) if element else default)


def _stepstone_url(href):
    return href if href and href.startswith("http") else f"https://www.stepstone.de{href}" if href else None


def _parse_job_card(card):
    title = translate_text(_element_text(card, "h2"))
    company = translate_text(_element_text(card, '[data-at="job-item-company-name"]'))
    location = translate_text(_element_text(card, '[data-at="job-item-location"]', "Berlin"))
    date_elem = card.find("span", string=DATE_PATTERN)
    date_posted = translate_text(sanitize_text(date_elem.get_text(strip=True) if date_elem else None))
    skills = translate_text(extract_skills(card))
    link = card.find("a", {"data-testid": "job-item-title"})
    job_url = _stepstone_url(link.get("href") if link else None)

    if not (title and job_url):
        return None

    return {
        "title": title,
        "company": company,
        "location": location,
        "remote": extract_remote(card),
        "skills": skills,
        "date_posted": date_posted,
        "url": job_url,
        "source": "StepStone",
    }


def _save_raw_html(html, page_number):
    raw_html_path = RAW_HTML_DIR / f"stepstone_page_{page_number}.html"
    raw_html_path.write_text(html, encoding="utf-8")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def scrape_page(page, url, page_number):
    """Scrape a single page from StepStone."""
    print(f"Scraping page {page_number}: {url}")

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)
        html = page.content()
        _save_raw_html(html, page_number)

        jobs = []
        for card in BeautifulSoup(html, "lxml").select("article[data-testid='job-item']"):
            try:
                job = _parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as exc:
                print(f"Error parsing card: {exc}")

        print(f"Found {len(jobs)} jobs on page {page_number}")
        return jobs
    except Exception as exc:
        print(f"Error scraping page {page_number}: {exc}")
        raise


def _save_jobs(jobs):
    if not jobs:
        print("No jobs scraped from StepStone")
        return

    output_csv = build_timestamped_path("stepstone_jobs")
    try:
        pd.DataFrame(jobs).to_csv(output_csv, index=False, encoding="utf-8")
        print(f"Saved {len(jobs)} jobs to {output_csv}")
    except PermissionError:
        fallback_path = build_timestamped_path("stepstone_jobs_fallback")
        print(f"Permission denied writing {output_csv}; saving fallback file to {fallback_path}")
        pd.DataFrame(jobs).to_csv(fallback_path, index=False, encoding="utf-8")
        print(f"Saved {len(jobs)} jobs to fallback file {fallback_path}")


def scrape_stepstone_jobs(max_pages=50):
    """Main scraping function for StepStone."""
    print(f"Starting StepStone scraping... (max {max_pages} pages)")
    all_jobs = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=ua.random, viewport={"width": 1280, "height": 720})
            page = context.new_page()

            for page_number in range(1, max_pages + 1):
                try:
                    jobs = scrape_page(page, build_page_url(page_number), page_number)
                    if not jobs:
                        print(f"No jobs found on page {page_number}, stopping pagination")
                        break
                    all_jobs.extend(jobs)
                    random_delay()
                except Exception as exc:
                    print(f"Failed page {page_number}: {exc}")
                    if page_number == 1:
                        break
            browser.close()
    except Exception as exc:
        print(f"Error in browser setup: {exc}")

    _save_jobs(all_jobs)
    return all_jobs


if __name__ == "__main__":
    scrape_stepstone_jobs()
