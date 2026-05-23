import asyncio
import logging

from fastapi import APIRouter, HTTPException

from services.scraper_service import scrape_all_job_sources

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["jobs"])


def _count(results, source):
    return results.get(source, {}).get("count", 0)


@router.get("/fetch-job-data")
async def fetch_job_data(stepstone_pages: int = 50):
    """Fetch job data from ArbeitNow and StepStone."""
    try:
        stepstone_pages = max(1, min(stepstone_pages, 50))
        logger.info("Fetching job data with stepstone_pages=%s", stepstone_pages)
        results = await asyncio.to_thread(scrape_all_job_sources, stepstone_pages)
        return {
            "success": True,
            "message": "Job data scraped successfully",
            "results": results,
            "total_jobs": results.get("total_jobs", 0),
            "arbeitnow_jobs": _count(results, "arbeitnow"),
            "stepstone_jobs": _count(results, "stepstone"),
        }
    except Exception as exc:
        message = f"Error fetching job data: {exc}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message)


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "OK", "message": "Job scraper service is running"}
