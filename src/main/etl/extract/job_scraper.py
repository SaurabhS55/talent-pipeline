from __future__ import annotations

from typing import Any

import pandas as pd
from jobspy import scrape_jobs

from configs import settings


#fetch jobs from one or more sources using JobSpy
def scrape_job_listings(
    *,
    site_name: list[str] | None = None,
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int | None = None,
    hours_old: int | None = None,
    country_indeed: str | None = None,
    fetch_description: bool | None = None,
    verbose: int | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    return scrape_jobs(
        site_name=site_name or settings.JOBSPY_SITES,
        search_term=search_term or settings.JOBSPY_SEARCH_TERM,
        location=location or settings.JOBSPY_LOCATION,
        results_wanted=results_wanted or settings.JOBSPY_RESULTS_WANTED,
        hours_old=hours_old or settings.JOBSPY_HOURS_OLD,
        country_indeed=country_indeed or settings.JOBSPY_COUNTRY,
        fetch_description=(
            settings.JOBSPY_FETCH_DESCRIPTION
            if fetch_description is None
            else fetch_description
        ),
        verbose=settings.JOBSPY_VERBOSE if verbose is None else verbose,
        **kwargs,
    )
