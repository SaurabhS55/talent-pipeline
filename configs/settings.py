import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "talent_pipeline")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

# Support legacy DB_HOST=host:port values
if DB_HOST and ":" in DB_HOST and not os.getenv("DB_PORT"):
    host, port = DB_HOST.rsplit(":", 1)
    if port.isdigit():
        DB_HOST = host
        DB_PORT = port

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

JOBSPY_SITES = [
    site.strip()
    for site in os.getenv("JOBSPY_SITES", "linkedin,naukri").split(",")
    if site.strip()
]
JOBSPY_SEARCH_TERM = os.getenv("JOBSPY_SEARCH_TERM", "software engineer")
JOBSPY_LOCATION = os.getenv("JOBSPY_LOCATION", "Bangalore")
JOBSPY_RESULTS_WANTED = int(os.getenv("JOBSPY_RESULTS_WANTED", "20"))
JOBSPY_HOURS_OLD = int(os.getenv("JOBSPY_HOURS_OLD", "72"))
JOBSPY_COUNTRY = os.getenv("JOBSPY_COUNTRY", "India")
JOBSPY_FETCH_DESCRIPTION = os.getenv("JOBSPY_FETCH_DESCRIPTION", "false").lower() in {
    "1",
    "true",
    "yes",
}
JOBSPY_VERBOSE = int(os.getenv("JOBSPY_VERBOSE", "1"))

LOAD_BATCH_SIZE = int(os.getenv("LOAD_BATCH_SIZE", "100"))
TRANSFORM_RAW_LIMIT = int(os.getenv("TRANSFORM_RAW_LIMIT", "500"))
