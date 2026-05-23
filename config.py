from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"

for directory in (DATA_DIR, RAW_HTML_DIR):
    directory.mkdir(exist_ok=True)

SCRAPER_CONFIG = {
    "stepstone": {
        "base_url": "https://www.stepstone.de/jobs/in-berlin?action=facet_selected%3bdisciplines%3bIT&di=IT",
        "max_pages": 50,
        "output_csv_pattern": str(DATA_DIR / "stepstone_jobs_{timestamp}.csv"),
        "timeout": 60000,
        "page_delay_min": 2,
        "page_delay_max": 5,
    },
    "arbeitnow": {
        "api_url": "https://arbeitnow.com/api/job-board-api",
        "output_csv_pattern": str(DATA_DIR / "arbeitnow_jobs_{timestamp}.csv"),
        "timeout": 30,
    },
}

API_CONFIG = {"host": "0.0.0.0", "port": 8000, "reload": True, "log_level": "info"}

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
}

REQUIRED_FIELDS = [
    "title",
    "location",
    "url",
    "company",
    "remote",
    "skills",
    "date_posted",
    "source",
]
