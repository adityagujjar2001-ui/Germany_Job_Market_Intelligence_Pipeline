import requests
import pandas as pd
from pathlib import Path
import datetime
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Configuration constants
BASE_URL = "https://arbeitnow.com/api/job-board-api"
DEFAULT_LIMIT = 100
MAX_PAGES = 100
REQUEST_TIMEOUT = 30
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Filters for IT jobs
IT_JOB_KEYWORDS = (
    r"IT|Python|Java|C\+\+|JavaScript|React|Node|DevOps|Cloud|AWS|Azure|Go|Rust|Kotlin|"
    r"Scala|Django|Flask|Spring|Angular|Vue|Docker|Kubernetes|Microservices|API|Backend|Frontend|Fullstack|"
    r"Software Engineer|Developer|Programmer|Data Scientist|Machine Learning Engineer|AI Engineer|Cloud Engineer|"
    r"DevOps Engineer|SRE|Site Reliability Engineer|System Administrator|Network Engineer|Security Engineer|Cybersecurity|"
    r"Information Security|Penetration Tester|Ethical Hacker|Security Analyst|Data Engineer|Big Data Engineer|"
    r"ETL Developer|Database Administrator|DBA|Business Intelligence Developer|BI Developer|Data Analyst|"
    r"Data Architect|Data Warehouse Engineer|Data Visualization|Tableau|Power BI|QlikView|Looker|Snowflake|"
    r"Redshift|BigQuery|Hadoop|Spark|Kafka|Scala|R|SAS|MATLAB|TensorFlow|PyTorch|Keras|Scikit-learn|XGBoost|"
    r"LightGBM|CatBoost"
)
LOCATION_FILTER = "Berlin"
SEARCH_QUERY = "IT"

# Headers for API requests
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_paginated_jobs(page: int) -> tuple[List[Dict[str, Any]], int]:
    """
    Fetch a single page of jobs from the API.
    
    Args:
        page: Page number to fetch
        
    Returns:
        Tuple of (jobs_list, status_code)
    """
    params = {
        "page": page,
        "limit": DEFAULT_LIMIT,
        "search": SEARCH_QUERY,
        "location": LOCATION_FILTER
    }
    
    try:
        response = requests.get(
            BASE_URL,
            headers=API_HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("data", [])
            return jobs, response.status_code
        else:
            logger.warning(f"API returned status {response.status_code} on page {page}")
            return [], response.status_code
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout while fetching page {page}")
        return [], 408
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error on page {page}: {str(e)}")
        return [], 500


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply filters to the job dataframe for IT roles in Berlin.
    
    Args:
        df: Input dataframe with job data
        
    Returns:
        Filtered dataframe
    """
    # Filter by job title keywords
    if "title" in df.columns:
        df = df[df["title"].str.contains(IT_JOB_KEYWORDS, case=False, na=False, regex=True)]
        logger.info(f"Jobs after title filter: {len(df)}")
    
    # Filter by location
    if "location" in df.columns:
        df = df[df["location"].str.contains(LOCATION_FILTER, case=False, na=False)]
        logger.info(f"Jobs after location filter: {len(df)}")
    
    # Remove duplicates
    if "url" in df.columns:
        df = df.drop_duplicates(subset=["title", "url"], keep="first")
        logger.info(f"Jobs after deduplication: {len(df)}")
    
    return df


def save_jobs_to_csv(df: pd.DataFrame) -> str:
    """
    Save jobs dataframe to a timestamped CSV file.
    
    Args:
        df: Dataframe to save
        
    Returns:
        Path to saved file
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = DATA_DIR / f"arbeitnow_jobs_{timestamp}.csv"
    
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"Saved {len(df)} jobs to {filename}")
    
    return str(filename)


def fetch_arbeitnow_jobs() -> Dict[str, Any]:
    """
    Fetch all IT job listings from ArbeitNow API for Berlin with pagination.
    
    Returns:
        dict: {
            "success": bool,
            "count": int,
            "file": str,
            "message": str
        }
    """
    try:
        logger.info("Starting ArbeitNow API fetch for IT jobs in Berlin")
        
        all_jobs = []
        page = 1
        
        # Pagination loop
        while page <= MAX_PAGES:
            logger.info(f"Fetching page {page}...")
            
            jobs, status_code = fetch_paginated_jobs(page)
            
            if not jobs:
                logger.info(f"No jobs on page {page}. Pagination complete.")
                break
            
            all_jobs.extend(jobs)
            logger.info(f"Page {page}: {len(jobs)} jobs fetched. Total: {len(all_jobs)}")
            page += 1
        
        if not all_jobs:
            logger.warning("No IT jobs found in Berlin")
            return {
                "success": False,
                "count": 0,
                "message": "No IT jobs in Berlin returned from API"
            }
        
        # Process dataframe
        df = pd.DataFrame(all_jobs)
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        
        # Apply filters
        df = filter_dataframe(df)
        
        if df.empty:
            logger.warning("No jobs remaining after filtering")
            return {
                "success": False,
                "count": 0,
                "message": "No jobs matched the IT and Berlin filters"
            }
        
        # Add source column
        df["source"] = "ArbeitNow"
        
        # Save to CSV
        filename = save_jobs_to_csv(df)
        
        logger.info(f"✓ Successfully fetched {len(df)} IT jobs from Berlin ({page - 1} pages)")
        
        return {
            "success": True,
            "count": len(df),
            "file": filename,
            "message": f"Fetched {len(df)} IT jobs in Berlin from {page - 1} pages"
        }
            
    except requests.exceptions.Timeout:
        logger.error("Request timeout while fetching from ArbeitNow API")
        return {
            "success": False,
            "count": 0,
            "message": "Request timeout while fetching from ArbeitNow API"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching from ArbeitNow API: {str(e)}")
        return {
            "success": False,
            "count": 0,
            "message": f"Network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching ArbeitNow jobs: {str(e)}")
        return {
            "success": False,
            "count": 0,
            "message": f"Error: {str(e)}"
        }


if __name__ == "__main__":
    result = fetch_arbeitnow_jobs()
    print(result)