# Job Seeker Pipeline - Scraping Architecture

## Overview

This project is a comprehensive job scraping pipeline built with FastAPI that aggregates job listings from multiple sources:
- **ArbeitNow API** - Direct API integration
- **StepStone** - Web scraping with pagination support

All data is extracted with consistent schema: job title, location, skills, salary, job posted date, and URL.

## Architecture

### Project Structure

```
Job Seeker Pipeline/
├── app/
│   ├── main.py              # FastAPI application setup
│   └── api/
│       └── routes.py        # API endpoints
├── scraper/
│   └── stepstone_scraper.py      # StepStone scraper with pagination
├── services/
│   ├── arbeitnow_csv.py     # ArbeitNow API integration
│   └── scraper_service.py   # Main orchestration service
├── data/
│   ├── stepstone_jobs_YYYY-MM-DD_HH-MM-SS.csv   # StepStone job data
│   ├── arbeitnow_jobs_*.csv            # ArbeitNow job data
│   └── raw_html/                       # Raw HTML for debugging
└── requirements.txt          # Python dependencies
```

## Key Features

### 1. **Scraper Layer** (`scraper/`)

#### StepStone Scraper (`stepstone_scraper.py`)
- **URL**: https://www.stepstone.de/jobs/in-berlin?action=facet_selected%3bdisciplines%3bIT&di=IT
- **Features**:
  - Pagination support with dynamic page-count detection
  - Random user agent rotation using `fake_useragent`
  - Headless browser automation with Playwright
  - Exponential backoff retry mechanism
  - Random delays between requests to avoid detection
  - Raw HTML saving for debugging
  
- **Extracted Fields**:
  - Job Title
  - Company Name
  - Location
  - Salary Range
  - Skills/Requirements
  - Job Posted Date
  - Job URL

### 2. **Services Layer** (`services/`)

#### ArbeitNow Integration (`arbeitnow_csv.py`)
- Direct API integration: `https://arbeitnow.com/api/job-board-api`
- Features:
  - Error handling with timeout support
  - Automatic CSV generation with timestamp
  - Normalization of column names
  - Returns structured response with count and file path

#### Scraper Service (`scraper_service.py`)
- **Main Orchestrator** function: `scrape_all_job_sources()`
- Coordinates StepStone and ArbeitNow data sources
- Features:
  - Comprehensive logging
  - Error handling for each source independently
  - Data combining and deduplication
  - Generates combined CSV with unique jobs
  - Returns detailed statistics

**Functions**:
- `scrape_all_job_sources(stepstone_pages=10)` - Main entry point
- `combine_job_data()` - Merges and deduplicates data

### 3. **API Layer** (`app/`)

#### Main App (`main.py`)
- FastAPI application setup
- CORS middleware configuration
- Logging setup
- Root endpoint for documentation

#### Routes (`api/routes.py`)
- **GET `/api/fetch-job-data`**: Triggers scraping of all sources
  - Parameters:
    - `stepstone_pages` (int, default=10)
  - Returns combined statistics and total job count
- **GET `/api/health`**: Health check endpoint

## Data Schema

All CSV files follow this schema:

| Column | Type | Description |
|--------|------|-------------|
| title | string | Job title |
| company | string | Company/Organization name |
| location | string | Job location |
| salary | string | Salary range (if available) |
| skills | string | Required skills (comma-separated) |
| date_posted | string | When job was posted |
| url | string | Direct job listing URL |
| source | string | Data source (StepStone, ArbeitNow) |

## Installation

### Prerequisites
- Python 3.10+
- Windows PowerShell or Command Prompt

### Setup

1. **Create Virtual Environment**
```bash
python -m venv myenv
myenv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Required Packages**
```
fastapi==0.136.1
uvicorn==0.47.0
playwright==1.48.0
beautifulsoup4==4.14.3
pandas==2.3.3
requests==2.33.1
fake-useragent==1.5.1
tenacity==9.0.0
```

4. **Install Playwright Browsers**
```bash
playwright install chromium
```

## Usage

### Option 1: Via API

**Start the server:**
```bash
python -m app.main
```

**Or using uvicorn directly:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Access API:**
- Health Check: `http://localhost:8000/api/health`
- Fetch Jobs: `http://localhost:8000/api/fetch-job-data?stepstone_pages=5`
- API Docs: `http://localhost:8000/docs`

### Option 2: Direct Python

```python
from services.scraper_service import scrape_all_job_sources

# Scrape all sources
results = scrape_all_job_sources(stepstone_pages=10)

print(f"Total jobs: {results['total_jobs']}")
print(f"ArbeitNow: {results['arbeitnow']['count']}")
print(f"StepStone: {results['stepstone']['count']}")
```

### Option 3: Individual Scrapers

```python
# Scrape only StepStone
from scraper.stepstone_scraper import scrape_stepstone_jobs
jobs = scrape_stepstone_jobs(max_pages=5)

# Fetch from ArbeitNow only
from services.arbeitnow_csv import fetch_arbeitnow_jobs
result = fetch_arbeitnow_jobs()
```

## Output Files

After running a scrape:

1. **Individual Source CSVs**:
   - `data/stepstone_jobs_YYYY-MM-DD_HH-MM-SS.csv` - StepStone data with timestamp
   - `data/arbeitnow_jobs_YYYY-MM-DD_HH-MM-SS.csv` - ArbeitNow data with timestamp

2. **Combined Data**:
   - This project no longer generates a combined `all_jobs.csv` file.

3. **Debug Files**:
   - `data/raw_html/` - Raw HTML snapshots for debugging scraping issues

## Features & Anti-Detection

### Scraping Protections

1. **User Agent Rotation**: Uses `fake_useragent` to rotate browser agents
2. **Random Delays**: 2-5 second random delays between requests
3. **Headless Browser**: Playwright with realistic browser context
4. **Retry Mechanism**: Exponential backoff with 3 retry attempts
5. **Timeout Handling**: 60-second page load timeout
6. **Request Headers**: Proper User-Agent and HTTP headers

### Error Handling

- Independent error handling for each data source
- Graceful degradation if one source fails
- Comprehensive logging for debugging
- Request timeout handling
- Network error recovery

## Logging

All operations are logged to console with timestamps and log levels:

```
2024-05-16 10:30:45 - services.scraper_service - INFO - Starting StepStone scraping...
2024-05-16 10:31:12 - scraper.stepstone_scraper - INFO - Found 45 jobs on page 1
```

## Data Deduplication

The `combine_job_data()` function in `scraper_service.py`:
- Removes duplicate jobs across sources
- Uses `title + url` as unique identifier
- Keeps first occurrence of duplicates
- No combined `all_jobs.csv` file is generated; source CSVs are kept separate.

## Performance Considerations

- **StepStone**: ~2-3 seconds per page (includes delays)
- **ArbeitNow**: ~1-2 seconds (API call, no browser)
- **Total Time**: ~1-2 minutes for 10 pages StepStone + ArbeitNow

## Troubleshooting

### Common Issues

1. **Playwright Installation Error**
   ```bash
   playwright install chromium
   ```

2. **Connection Timeout**
   - Check internet connection
   - Website might be blocking requests (adjust delays)
   - Try reducing page count

3. **No Data Scraped**
   - HTML selectors might have changed
   - Website structure updated - review raw_html files
   - Update CSS selectors in scraper files

4. **CSV Already Exists**
   - Old CSV will be overwritten
   - Timestamped ArbeitNow CSVs are kept

## Future Enhancements

- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] Job filtering and search API endpoints
- [ ] Email notifications for new jobs
- [ ] Salary range standardization across sources
- [ ] Geographic filtering and clustering
- [ ] Job skill matching and recommendations
- [ ] Scheduled scraping (Celery/APScheduler)
- [ ] WebSocket real-time updates

## API Response Example

```json
{
  "success": true,
  "message": "Job data scraped successfully",
  "total_jobs": 970,
  "arbeitnow_jobs": 450,
  "stepstone_jobs": 520,
  "results": {
    "arbeitnow": {
      "success": true,
      "count": 450,
      "error": null
    },
    "stepstone": {
      "success": true,
      "count": 520,
      "error": null
    },
    "combined": {
      "success": true,
      "count": 1250,
      "error": null
    }
  }
}
```

## License

This project is for educational and non-commercial use.

## Notes

- Respect website robots.txt and terms of service
- Adjust delays to be respectful to servers
- Monitor your IP for potential blocks
- Consider implementing rotating proxies for large-scale scraping
