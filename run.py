#!/usr/bin/env python
"""
Job Scraper Pipeline CLI Runner

Usage:
    python run.py scrape           # Run all scrapers
    python run.py scrape-all       # Run all scrapers
    python run.py scrape-stepstone # Run only StepStone scraper
    python run.py scrape-arbeitnow # Fetch only from ArbeitNow API
    python run.py server           # Start FastAPI server
    python run.py help             # Show this help message
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def print_banner(title, *lines, width=70):
    print("\n" + "=" * width)
    print(title)
    for line in lines:
        print(line)
    print("=" * width + "\n")


def page_arg(default=10):
    return int(sys.argv[2]) if len(sys.argv) > 2 else default


def run_all_scrapers(stepstone_pages=10):
    """Run all scrapers."""
    from services.scraper_service import scrape_all_job_sources

    print_banner("STARTING JOB SCRAPER - ALL SOURCES")
    results = scrape_all_job_sources(stepstone_pages=stepstone_pages)
    print_banner(
        "SCRAPING COMPLETE",
        f"Total jobs fetched: {results.get('total_jobs', 0)}",
        f"  - ArbeitNow: {results.get('arbeitnow', {}).get('count', 0)}",
        f"  - StepStone: {results.get('stepstone', {}).get('count', 0)}",
    )
    return results


def run_stepstone_scraper(pages=10):
    """Run only StepStone scraper."""
    from scraper.stepstone_scraper import scrape_stepstone_jobs

    print_banner("SCRAPING STEPSTONE")
    jobs = scrape_stepstone_jobs(max_pages=pages)
    print(f"\n✓ Completed! Scraped {len(jobs)} jobs from StepStone\n")
    return jobs


def run_arbeitnow_fetch():
    """Fetch only from ArbeitNow API."""
    from services.arbeitnow_csv import fetch_arbeitnow_jobs

    print_banner("FETCHING FROM ARBEITNOW API")
    result = fetch_arbeitnow_jobs()
    print(f"\n✓ Completed! Fetched {result.get('count', 0)} jobs from ArbeitNow\n")
    return result


def run_server():
    """Start FastAPI server."""
    import uvicorn

    print_banner(
        "STARTING JOB SCRAPER API SERVER",
        "Server running at: http://localhost:8000",
        "API Docs at: http://localhost:8000/docs",
        "Press Ctrl+C to stop",
    )
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


def show_help():
    print(__doc__)


COMMANDS = {
    "scrape": lambda: run_all_scrapers(page_arg()),
    "scrape-all": lambda: run_all_scrapers(page_arg()),
    "scrape-stepstone": lambda: run_stepstone_scraper(page_arg()),
    "scrape-arbeitnow": run_arbeitnow_fetch,
    "server": run_server,
    "help": show_help,
    "-h": show_help,
    "--help": show_help,
}


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command not in COMMANDS:
            print(f"Unknown command: {command}")
            print("Use 'python run.py help' for available commands")
            sys.exit(1)
        COMMANDS[command]()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
