import time
import random
import pandas as pd
import re
import requests
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://www.stepstone.de/jobs/in-berlin?action=facet_selected%3bdisciplines%3bIT&di=IT"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"

# Ensure data and raw html directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)

ua = UserAgent()

HEADERS = {
    "User-Agent": ua.random
}


def build_timestamped_path(prefix: str = "stepstone_jobs"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return DATA_DIR / f"{prefix}_{timestamp}.csv"


def random_delay():
    """Add random delay to avoid detection"""
    time.sleep(random.uniform(2, 5))


def extract_salary(salary_text):
    """Extract salary range from text"""
    if not salary_text:
        return None
    
    # Remove currency symbols and find numbers
    patterns = [
        r'€\s?\d+[.,]?\d*',
        r'\d+[.,]?\d*\s?€',
        r'\d+\s?€\s?mtl',
        r'\d+\s?€\s?pro Jahr',
        r'\d+[.,]?\d*\s?(?:k|K)',
    ]

    for pattern in patterns:
        match = re.search(pattern, salary_text, re.I)
        if match:
            return match.group(0)

    return None


def extract_date_posted(date_text):
    """Extract job posted date"""
    if not date_text:
        return None
    return date_text.strip()


def extract_skills(card):
    """Extract skills from job listing"""
    skills = []
    
    # Look for skill tags/badges in the card
    skill_elems = card.find_all(["span", "div"], {"class": re.compile(r"skill|tag|badge|requirement", re.I)})
    
    for elem in skill_elems:
        skill_text = elem.get_text(strip=True)
        if skill_text and len(skill_text) < 50:  # Filter out long texts
            skills.append(skill_text)
    
    return ", ".join(skills) if skills else None


translation_cache = {}


def translate_text(text, target_lang="en"):
    """Translate text from German to English using Google Translate."""
    if not text or not text.strip():
        return text

    cache_key = (text, target_lang)
    if cache_key in translation_cache:
        return translation_cache[cache_key]

    translated = text
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": target_lang,
                "dt": "t",
                "q": text,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and data and isinstance(data[0], list):
            translated = "".join([item[0] for item in data[0] if item and item[0]]) or text

    except Exception:
        translated = text

    translation_cache[cache_key] = translated
    return translated


def sanitize_text(text):
    return text.strip() if text and isinstance(text, str) else None


def build_page_url(page_number):
    """Build URL for the given page number"""
    if page_number == 1:
        return BASE_URL
    separator = "&" if "?" in BASE_URL else "?"
    return f"{BASE_URL}{separator}page={page_number}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def scrape_page(page, url, page_number):
    """Scrape a single page from StepStone"""
    print(f"Scraping page {page_number}: {url}")

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        html = page.content()

        # Save raw html
        raw_html_path = RAW_HTML_DIR / f"stepstone_page_{page_number}.html"
        with open(raw_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        # Find job cards - updated selector to match actual HTML structure
        cards = soup.select("article[data-testid='job-item']")

        for card in cards:
            try:
                # Extract job title
                title = card.select_one("h2")
                job_title = sanitize_text(title.get_text(strip=True) if title else None)

                # Extract company name - updated selector to match data-at attribute
                company = card.select_one('[data-at="job-item-company-name"]')
                company_name = sanitize_text(company.get_text(strip=True) if company else None)

                # Extract location
                location = card.select_one('[data-at="job-item-location"]')
                job_location = sanitize_text(location.get_text(strip=True) if location else "Berlin")

                # Extract salary - look for any span with salary-related text
                #salary_elem = card.find("span", string=re.compile(r"€|\d+[.,]\d+", re.I))
                salary_elem = (
                card.find("div", {"data-testid": "salary"}) or
                card.find("span", {"data-testid": "salary-info"}) or
                card.find(string=re.compile(r"€|EUR|per year|pro Jahr", re.I))
                )
                salary = extract_salary(salary_elem.get_text(strip=True) if salary_elem else None)
                
                # Extract date posted
                date_elem = card.find("span", string=re.compile(r"vor|ago|gestern|today", re.I))
                date_posted = sanitize_text(date_elem.get_text(strip=True) if date_elem else None)

                # Extract skills from job description or tags
                skills = extract_skills(card)

                # Translate extracted text to English
                job_title = translate_text(job_title)
                company_name = translate_text(company_name)
                job_location = translate_text(job_location)
                salary = translate_text(salary)
                date_posted = translate_text(date_posted)
                skills = translate_text(skills)

                # Extract job URL
                link = card.find("a", {"data-testid": "job-item-title"})
                job_url = None
                if link and link.get("href"):
                    href = link["href"]
                    job_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"

                # Only add if we have at least title and URL
                if job_title and job_url:
                    jobs.append({
                        "title": job_title,
                        "company": company_name,
                        "location": job_location,
                        "salary": salary,
                        "skills": skills,
                        "date_posted": date_posted,
                        "url": job_url,
                        "source": "StepStone"
                    })

            except Exception as e:
                print(f"Error parsing card: {e}")
                continue

        print(f"Found {len(jobs)} jobs on page {page_number}")
        return jobs

    except Exception as e:
        print(f"Error scraping page {page_number}: {e}")
        raise


def scrape_stepstone_jobs(max_pages=10):
    """Main scraping function for StepStone"""
    print(f"Starting StepStone scraping... (max {max_pages} pages)")
    
    all_jobs = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=ua.random,
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()

            for page_number in range(1, max_pages + 1):
                try:
                    url = build_page_url(page_number)
                    jobs = scrape_page(page, url, page_number)

                    if not jobs:
                        print(f"No jobs found on page {page_number}, stopping pagination")
                        break
                    
                    all_jobs.extend(jobs)
                    random_delay()

                except Exception as e:
                    print(f"Failed page {page_number}: {e}")
                    if page_number == 1:  # If first page fails, stop completely
                        break
                    continue  # Continue with next page

            browser.close()

    except Exception as e:
        print(f"Error in browser setup: {e}")

    # Save to CSV
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        output_csv = build_timestamped_path("stepstone_jobs")

        try:
            df.to_csv(output_csv, index=False, encoding='utf-8')
            print(f"Saved {len(all_jobs)} jobs to {output_csv}")
        except PermissionError as e:
            fallback_path = build_timestamped_path("stepstone_jobs_fallback")
            print(f"Permission denied writing {output_csv}; saving fallback file to {fallback_path}")
            df.to_csv(fallback_path, index=False, encoding='utf-8')
            print(f"Saved {len(all_jobs)} jobs to fallback file {fallback_path}")
    else:
        print("No jobs scraped from StepStone")

    return all_jobs


if __name__ == "__main__":
    scrape_stepstone_jobs()