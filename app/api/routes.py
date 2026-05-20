from fastapi import APIRouter, HTTPException
from services.scraper_service import scrape_all_job_sources
from bs4 import BeautifulSoup
from pathlib import Path
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/fetch-job-data")
async def fetch_job_data(stepstone_pages: int = 10):
    """
    Fetch job data from all sources:
    - ArbeitNow API
    - StepStone (Berlin jobs)
    
    Returns combined statistics and total jobs count
    """
    try:
        logger.info(f"Fetching job data with stepstone_pages={stepstone_pages}")
        # Run the blocking, sync orchestrator in a separate thread to avoid
        # using Playwright sync API inside the async event loop.
        results = await asyncio.to_thread(scrape_all_job_sources, stepstone_pages)
        
        return {
            "success": True,
            "message": "Job data scraped successfully",
            "results": results,
            "total_jobs": results.get("total_jobs", 0),
            "arbeitnow_jobs": results.get("arbeitnow", {}).get("count", 0),
            "stepstone_jobs": results.get("stepstone", {}).get("count", 0),
        }
    except Exception as e:
        logger.error(f"Error fetching job data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching job data: {str(e)}")


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "OK", "message": "Job scraper service is running"}
