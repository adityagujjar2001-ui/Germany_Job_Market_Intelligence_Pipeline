#!/usr/bin/env python
"""
Job Scraper Pipeline CLI Runner

Usage:
    python run.py scrape          # Run all scrapers
    python run.py scrape-all      # Run all scrapers (same as above)
    python run.py scrape-stepstone # Run only StepStone scraper
    python run.py scrape-arbeitnow # Fetch only from ArbeitNow API
    python run.py server          # Start FastAPI server
    python run.py help            # Show this help message
"""

import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_all_scrapers(stepstone_pages=10):
    """Run all scrapers"""
    print("\n" + "=" * 70)
    print("STARTING JOB SCRAPER - ALL SOURCES")
    print("=" * 70 + "\n")
    
    from services.scraper_service import scrape_all_job_sources
    
    results = scrape_all_job_sources(stepstone_pages=stepstone_pages)
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total jobs fetched: {results.get('total_jobs', 0)}")
    print(f"  - ArbeitNow: {results.get('arbeitnow', {}).get('count', 0)}")
    print(f"  - StepStone: {results.get('stepstone', {}).get('count', 0)}")
    print("=" * 70 + "\n")
    
    return results


def run_stepstone_scraper(pages=10):
    """Run only StepStone scraper"""
    print("\n" + "=" * 70)
    print("SCRAPING STEPSTONE")
    print("=" * 70 + "\n")
    
    from scraper.stepstone_scraper import scrape_stepstone_jobs
    
    jobs = scrape_stepstone_jobs(max_pages=pages)
    
    print(f"\n✓ Completed! Scraped {len(jobs)} jobs from StepStone\n")
    return jobs


def run_arbeitnow_fetch():
    """Fetch only from ArbeitNow API"""
    print("\n" + "=" * 70)
    print("FETCHING FROM ARBEITNOW API")
    print("=" * 70 + "\n")
    
    from services.arbeitnow_csv import fetch_arbeitnow_jobs
    
    result = fetch_arbeitnow_jobs()
    
    print(f"\n✓ Completed! Fetched {result.get('count', 0)} jobs from ArbeitNow\n")
    return result


def run_server():
    """Start FastAPI server"""
    import uvicorn
    
    print("\n" + "=" * 70)
    print("STARTING JOB SCRAPER API SERVER")
    print("=" * 70)
    print("Server running at: http://localhost:8000")
    print("API Docs at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def show_help():
    """Show help message"""
    print(__doc__)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command in ["scrape", "scrape-all"]:
            # Extract optional parameters
            stepstone_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            run_all_scrapers(stepstone_pages=stepstone_pages)
            
        elif command == "scrape-stepstone":
            pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            run_stepstone_scraper(pages=pages)
            
        elif command == "scrape-arbeitnow":
            run_arbeitnow_fetch()
            
        elif command == "server":
            run_server()
            
        elif command in ["help", "-h", "--help"]:
            show_help()
            
        else:
            print(f"Unknown command: {command}")
            print("Use 'python run.py help' for available commands")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
