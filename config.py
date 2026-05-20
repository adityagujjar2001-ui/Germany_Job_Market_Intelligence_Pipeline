import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Data directory
DATA_DIR = BASE_DIR / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
RAW_HTML_DIR.mkdir(exist_ok=True)

# Scraper configuration
SCRAPER_CONFIG = {
    "stepstone": {
        "base_url": "https://www.stepstone.de/jobs/in-berlin?action=facet_selected%3bdisciplines%3bIT&di=IT",
        "max_pages": 10,
        "output_csv_pattern": str(DATA_DIR / "stepstone_jobs_{timestamp}.csv"),
        "timeout": 60000,
        "page_delay_min": 2,
        "page_delay_max": 5,
    },
    "arbeitnow": {
        "api_url": "https://arbeitnow.com/api/job-board-api",
        "output_csv_pattern": str(DATA_DIR / "arbeitnow_jobs_{timestamp}.csv"),
        "timeout": 30,
    }
}

# API configuration
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "log_level": "info",
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
}

# Export required fields
REQUIRED_FIELDS = [
    "title",
    "location",
    "url",
    "company",
    "salary",
    "skills",
    "date_posted",
    "source",
]
