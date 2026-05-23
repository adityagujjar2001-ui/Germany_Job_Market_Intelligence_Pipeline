import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Scraper API",
    description="API for scraping job data from multiple sources",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Job Scraper API",
        "version": "1.0.0",
        "endpoints": {"health": "/api/health", "fetch_jobs": "/api/fetch-job-data"},
    }


def start_server():
    import uvicorn

    logger.info("Starting Job Scraper API...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    start_server()
