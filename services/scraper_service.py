import logging

from scraper.stepstone_scraper import DATA_DIR, scrape_stepstone_jobs
from services.arbeitnow_csv import fetch_arbeitnow_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _source_result():
    return {"success": False, "count": 0, "error": None}


def _log_section(title, width=60):
    logger.info("\n%s", title)
    logger.info("-" * width)


def scrape_all_job_sources(stepstone_pages):
    """Scrape ArbeitNow and StepStone, returning source-level statistics."""
    try:
        logger.info("=" * 60)
        logger.info("STARTING JOB DATA SCRAPING FROM ALL SOURCES")
        logger.info("=" * 60)

        results = {"arbeitnow": _source_result(), "stepstone": _source_result()}

        _log_section("1. Fetching from ArbeitNow API...", 40)
        try:
            arbeitnow_result = fetch_arbeitnow_jobs()
            if arbeitnow_result:
                results["arbeitnow"]["success"] = True
                results["arbeitnow"]["count"] = arbeitnow_result.get("count", 0)
                logger.info("✓ ArbeitNow: %s jobs fetched", results["arbeitnow"]["count"])
            else:
                results["arbeitnow"]["error"] = "No data returned"
                logger.warning("✗ ArbeitNow: Failed to fetch data")
        except Exception as exc:
            results["arbeitnow"]["error"] = str(exc)
            logger.error("✗ ArbeitNow Error: %s", exc)

        _log_section("2. Scraping from StepStone...", 40)
        try:
            stepstone_jobs = scrape_stepstone_jobs(max_pages=stepstone_pages)
            results["stepstone"]["success"] = len(stepstone_jobs) > 0
            results["stepstone"]["count"] = len(stepstone_jobs)
            logger.info("✓ StepStone: %s jobs scraped", len(stepstone_jobs))
        except Exception as exc:
            results["stepstone"]["error"] = str(exc)
            logger.error("✗ StepStone Error: %s", exc)

        total_jobs = results["arbeitnow"]["count"] + results["stepstone"]["count"]
        logger.info("\n%s", "=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info("ArbeitNow Jobs : %s", results["arbeitnow"]["count"])
        logger.info("StepStone Jobs : %s", results["stepstone"]["count"])
        logger.info("TOTAL JOBS FETCHED : %s", total_jobs)
        logger.info("%s\n", "=" * 60)

        results["total_jobs"] = total_jobs
        return results
    except Exception as exc:
        logger.error("Critical error in scrape_all_job_sources: %s", exc)
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    print("\nFinal Results:", scrape_all_job_sources(stepstone_pages=5))
