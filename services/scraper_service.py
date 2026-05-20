import os
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# Import scrapers
from scraper.stepstone_scraper import scrape_stepstone_jobs, DATA_DIR
from services.arbeitnow_csv import fetch_arbeitnow_jobs

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


def scrape_all_job_sources(stepstone_pages):
    """
    Main orchestration function to scrape all job sources:
    - ArbeitNow API
    - StepStone

    Returns scraping statistics only
    """

    try:
        logger.info("=" * 60)
        logger.info("STARTING JOB DATA SCRAPING FROM ALL SOURCES")
        logger.info("=" * 60)

        results = {
            "arbeitnow": {
                "success": False,
                "count": 0,
                "error": None
            },
            "stepstone": {
                "success": False,
                "count": 0,
                "error": None
            }
        }

        # ---------------------------------------------------
        # 1. Fetch from ArbeitNow API
        # ---------------------------------------------------

        logger.info("\n1. Fetching from ArbeitNow API...")
        logger.info("-" * 40)

        try:

            arbeitnow_result = fetch_arbeitnow_jobs()

            if arbeitnow_result:

                results["arbeitnow"]["success"] = True
                results["arbeitnow"]["count"] = arbeitnow_result.get("count", 0)

                logger.info(
                    f"✓ ArbeitNow: "
                    f"{results['arbeitnow']['count']} jobs fetched"
                )

            else:

                results["arbeitnow"]["error"] = "No data returned"

                logger.warning(
                    "✗ ArbeitNow: Failed to fetch data"
                )

        except Exception as e:

            results["arbeitnow"]["error"] = str(e)

            logger.error(f"✗ ArbeitNow Error: {e}")

        # ---------------------------------------------------
        # 2. Scrape StepStone
        # ---------------------------------------------------

        logger.info("\n2. Scraping from StepStone...")
        logger.info("-" * 40)

        try:

            stepstone_jobs = scrape_stepstone_jobs(
                max_pages=stepstone_pages
            )

            results["stepstone"]["success"] = (
                len(stepstone_jobs) > 0
            )

            results["stepstone"]["count"] = len(stepstone_jobs)

            logger.info(
                f"✓ StepStone: "
                f"{len(stepstone_jobs)} jobs scraped"
            )

        except Exception as e:

            results["stepstone"]["error"] = str(e)

            logger.error(f"✗ StepStone Error: {e}")

        # ---------------------------------------------------
        # FINAL SUMMARY
        # ---------------------------------------------------

        total_jobs = (
            results["arbeitnow"]["count"] +
            results["stepstone"]["count"]
        )

        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)

        logger.info(
            f"ArbeitNow Jobs : "
            f"{results['arbeitnow']['count']}"
        )

        logger.info(
            f"StepStone Jobs : "
            f"{results['stepstone']['count']}"
        )

        logger.info(
            f"TOTAL JOBS FETCHED : {total_jobs}"
        )

        logger.info("=" * 60 + "\n")

        # Add total to response
        results["total_jobs"] = total_jobs

        return results

    except Exception as e:

        logger.error(
            f"Critical error in scrape_all_job_sources: {e}"
        )

        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Run all scrapers
    results = scrape_all_job_sources(stepstone_pages=5)
    print("\nFinal Results:", results)
