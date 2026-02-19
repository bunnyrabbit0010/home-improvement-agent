import logging
import os

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from agents.models.contractor import Contractor, ContractorList

logger = logging.getLogger(__name__)

load_dotenv()
fc_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
logger.info("FirecrawlApp initialized successfully for discovery tools.")


def _extract_content(scrape_result) -> str:
    if isinstance(scrape_result, dict):
        return scrape_result.get("content", "") or ""
    return getattr(scrape_result, "content", "") or ""


def get_google_reviews(contractor_name: str, zip_code: str) -> str:
    if not contractor_name or not zip_code:
        logger.warning("Missing contractor_name or zip_code for Google review lookup.")
        return ""

    google_maps_url = f"https://www.google.com/maps/search/{contractor_name}+roofing+{zip_code}"
    logger.info(
        "Fetching Google reviews content for contractor='%s', zip='%s'",
        contractor_name,
        zip_code,
    )
    logger.debug("Google Maps search URL: %s", google_maps_url)

    try:
        scraped_data = fc_app.scrape(
            google_maps_url,
            {"pageOptions": {"onlyMainContent": True}},
        )
        content = _extract_content(scraped_data)
        if not content:
            logger.warning(
                "No review content returned from Google Maps scrape for '%s' (%s).",
                contractor_name,
                zip_code,
            )
            return ""

        logger.info(
            "Successfully fetched Google review content for '%s' (%s).",
            contractor_name,
            zip_code,
        )
        return content
    except Exception:
        logger.exception(
            "Failed to fetch Google reviews for contractor='%s', zip='%s'.",
            contractor_name,
            zip_code,
        )
        return ""


def get_bbb_info(contractor_name: str, zip_code: str) -> str:
    if not contractor_name or not zip_code:
        logger.warning("Missing contractor_name or zip_code for BBB lookup.")
        return ""

    search_url = (
        "https://www.bbb.org/search"
        f"?find_country=USA&find_latlng=&find_loc={zip_code}&find_text={contractor_name}+roofing"
    )

    logger.info(
        "Fetching BBB info for contractor='%s', zip='%s'",
        contractor_name,
        zip_code,
    )
    logger.debug("BBB search URL: %s", search_url)

    try:
        search_results = fc_app.scrape(
            search_url,
            {"pageOptions": {"onlyMainContent": True}},
        )
        content = _extract_content(search_results)
        if not content:
            logger.warning(
                "No BBB content returned for contractor='%s', zip='%s'.",
                contractor_name,
                zip_code,
            )
            return ""

        logger.info(
            "Successfully fetched BBB content for contractor='%s', zip='%s'.",
            contractor_name,
            zip_code,
        )
        return content
    except Exception:
        logger.exception(
            "Failed to fetch BBB info for contractor='%s', zip='%s'.",
            contractor_name,
            zip_code,
        )
        return ""


def search_contractors(service: str, zip_code: str) -> list[Contractor]:
    logger.info("Searching for service='%s' in zip='%s'.", service, zip_code)
    url = f"https://www.yelp.com/search?find_desc={service}&find_loc={zip_code}"

    try:
        response = fc_app.extract(
            urls=[url],
            prompt=f"Find the top 5 {service} companies with their ratings.",
            schema=ContractorList.model_json_schema(),
        )

        if response.success:
            raw_data = response.data
            validated = ContractorList.model_validate(raw_data)
            return validated.contractors

        logger.warning(
            "Contractor extraction failed for service='%s', zip='%s': %s",
            service,
            zip_code,
            getattr(response, "error", "unknown error"),
        )
        return []
    except Exception:
        logger.exception(
            "Failed to search contractors for service='%s', zip='%s'.",
            service,
            zip_code,
        )
        return []
