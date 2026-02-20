import logging
import os
import re
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from schema.models import (
    Contractor,
    ContractorList,
    ContractorSearchResult,
    ContractorWebsiteInfo,
)

logger = logging.getLogger(__name__)

load_dotenv()
fc_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
logger.info("FirecrawlApp initialized successfully for discovery tools.")


def _extract_content(scrape_result) -> str:
    if isinstance(scrape_result, dict):
        return (
            scrape_result.get("content")
            or scrape_result.get("markdown")
            or scrape_result.get("summary")
            or scrape_result.get("html")
            or ""
        )
    return (
        getattr(scrape_result, "content", "")
        or getattr(scrape_result, "markdown", "")
        or getattr(scrape_result, "summary", "")
        or getattr(scrape_result, "html", "")
        or ""
    )


def _build_yelp_search_url(service: str, zip_code: str) -> str:
    return (
        f"https://www.yelp.com/search?find_desc={quote_plus(service)}"
        f"&find_loc={quote_plus(zip_code)}"
    )


def _is_yelp_url(url: str) -> bool:
    clean_url = (url or "").strip().lower()
    if not clean_url:
        return False
    if "yelp.com" in clean_url:
        return True
    parsed = urlparse(clean_url)
    return "yelp.com" in (parsed.netloc or "")


def _normalize_contractor_urls(contractor: Contractor) -> Contractor:
    website = (contractor.website or "").strip()
    yelp_profile_url = (contractor.yelp_profile_url or "").strip()

    if website and _is_yelp_url(website):
        yelp_profile_url = website
        website = ""

    return contractor.model_copy(
        update={
            "website": website or None,
            "yelp_profile_url": yelp_profile_url or None,
        }
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())).strip()


def _digits_only(text: str) -> str:
    return re.sub(r"\D+", "", text or "")


def _extract_google_listing_block(
    raw_content: str,
    contractor_name: str,
    expected_phone: str | None = None,
    expected_address: str | None = None,
) -> str:
    lines = [line.strip() for line in raw_content.splitlines()]
    listing_starts = [
        idx
        for idx, line in enumerate(lines)
        if line.startswith("[")
        and "(https://www.google.com/maps/place/" in line
    ]
    if not listing_starts:
        return ""

    normalized_name = _normalize_text(contractor_name)
    phone_digits = _digits_only(expected_phone or "")
    address_tokens = [
        token
        for token in _normalize_text(expected_address or "").split()
        if len(token) >= 4
    ]

    best_score = -1
    best_block = ""
    for start in listing_starts:
        end = min(start + 14, len(lines))
        block_lines = [line for line in lines[start:end] if line]
        if not block_lines:
            continue
        block_text = "\n".join(block_lines)
        normalized_block = _normalize_text(block_text)
        score = 0
        if normalized_name and normalized_name in normalized_block:
            score += 3
        if phone_digits and phone_digits in _digits_only(block_text):
            score += 2
        if address_tokens and any(token in normalized_block for token in address_tokens):
            score += 1

        if score > best_score:
            best_score = score
            best_block = block_text

    return best_block if best_score > 0 else ""


def get_google_reviews(
    contractor_name: str,
    zip_code: str,
    service_type: str | None = None,
    expected_phone: str | None = None,
    expected_address: str | None = None,
) -> str:
    if not contractor_name or not zip_code:
        logger.warning("Missing contractor_name or zip_code for Google review lookup.")
        return ""

    clean_service = (service_type or "").strip()
    query_parts = [contractor_name, zip_code]
    if clean_service and _normalize_text(clean_service) not in _normalize_text(
        contractor_name
    ):
        query_parts.append(clean_service)
    google_maps_query = " ".join(part for part in query_parts if part)
    google_maps_url = "https://www.google.com/maps/search/" f"{quote_plus(google_maps_query)}"
    logger.info(
        "Fetching Google reviews content for contractor='%s', service='%s', zip='%s'",
        contractor_name,
        clean_service,
        zip_code,
    )
    logger.debug("Google Maps search URL: %s", google_maps_url)

    try:
        scraped_data = fc_app.scrape(
            google_maps_url,
            formats=["markdown"],
            only_main_content=True,
        )
        content = _extract_content(scraped_data)
        if not content:
            logger.warning(
                "No review content returned from Google Maps scrape for '%s' (%s).",
                contractor_name,
                zip_code,
            )
            return ""

        filtered_content = _extract_google_listing_block(
            content,
            contractor_name,
            expected_phone=expected_phone,
            expected_address=expected_address,
        )
        if filtered_content:
            logger.info(
                "Filtered Google content to likely matching listing for '%s'.",
                contractor_name,
            )
            return filtered_content

        logger.warning(
            "Could not confidently isolate matching Google listing for '%s'; using raw content.",
            contractor_name,
        )

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


def get_bbb_info(
    contractor_name: str, zip_code: str, service_type: str | None = None
) -> str:
    if not contractor_name or not zip_code:
        logger.warning("Missing contractor_name or zip_code for BBB lookup.")
        return ""

    clean_service = (service_type or "home improvement").strip()
    search_url = (
        "https://www.bbb.org/search"
        f"?find_country=USA&find_latlng=&find_loc={quote_plus(zip_code)}"
        f"&find_text={quote_plus(contractor_name)}+{quote_plus(clean_service)}"
    )

    logger.info(
        "Fetching BBB info for contractor='%s', service='%s', zip='%s'",
        contractor_name,
        clean_service,
        zip_code,
    )
    logger.debug("BBB search URL: %s", search_url)

    try:
        search_results = fc_app.scrape(
            search_url,
            formats=["markdown"],
            only_main_content=True,
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


def search_contractors(service: str, zip_code: str) -> ContractorSearchResult:
    logger.info("Searching for service='%s' in zip='%s'.", service, zip_code)
    url = _build_yelp_search_url(service, zip_code)

    try:
        response = fc_app.extract(
            urls=[url],
            prompt=(
                f"Find the top 5 {service} companies with their ratings, review counts, "
                "website URL, phone number, and address where available."
            ),
            schema=ContractorList.model_json_schema(),
        )

        if response.success:
            raw_data = response.data
            validated = ContractorList.model_validate(raw_data)
            normalized_contractors = [
                _normalize_contractor_urls(contractor)
                for contractor in validated.contractors
            ]
            return ContractorSearchResult(
                source_url=url,
                service_type=service,
                zip_code=zip_code,
                contractors=normalized_contractors,
            )

        logger.warning(
            "Contractor extraction failed for service='%s', zip='%s': %s",
            service,
            zip_code,
            getattr(response, "error", "unknown error"),
        )
        return ContractorSearchResult(
            source_url=url,
            service_type=service,
            zip_code=zip_code,
            contractors=[],
        )
    except Exception:
        logger.exception(
            "Failed to search contractors for service='%s', zip='%s'.",
            service,
            zip_code,
        )
        return ContractorSearchResult(
            source_url=url,
            service_type=service,
            zip_code=zip_code,
            contractors=[],
        )


def analyze_contractor_website(
    website_url: str, service_type: str | None = None
) -> ContractorWebsiteInfo:
    logger.info(
        "Starting contractor website analysis for url='%s', service='%s'.",
        website_url,
        service_type,
    )
    clean_url = (website_url or "").strip()
    clean_service = (service_type or "home improvement").strip()
    if not clean_url:
        logger.warning("Skipping website analysis because website_url is missing.")
        return ContractorWebsiteInfo()

    try:
        response = fc_app.extract(
            urls=[clean_url],
            prompt=(
                f"Extract services offered relevant to {clean_service}, contractor "
                "license number, and years in business. Return structured output only."
            ),
            schema=ContractorWebsiteInfo.model_json_schema(),
        )
        if not response.success:
            logger.warning(
                "Website analysis extraction failed for url='%s': %s",
                clean_url,
                getattr(response, "error", "unknown error"),
            )
            return ContractorWebsiteInfo(source_url=clean_url)

        raw_data = response.data
        parsed = ContractorWebsiteInfo.model_validate(raw_data)
        if not parsed.source_url:
            parsed.source_url = clean_url

        logger.info("Completed contractor website analysis for url='%s'.", clean_url)
        return parsed
    except Exception:
        logger.exception("Website analysis failed for url='%s'.", clean_url)
        return ContractorWebsiteInfo(source_url=clean_url)
