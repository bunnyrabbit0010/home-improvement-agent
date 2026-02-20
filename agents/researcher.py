import logging
from tools.firecrawl_tool import search_contractors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get user context
    service_type = input("What service are you looking for? (e.g., Roofing, Plumbing): ")
    zip_code = input("Enter your ZIP code: ")
    
    logging.info(f"User is looking for {service_type} in {zip_code}.")
    search_result = search_contractors(service_type, zip_code)
    results = search_result.contractors

    logging.info(
        "Found %d contractors for %s in %s from %s.",
        len(results),
        service_type,
        zip_code,
        search_result.source_url,
    )

    logging.info(f"Displaying top 5 results for {service_type} in {zip_code}.")
    for i, c in enumerate(results[:5], 1):
        logging.info(f"{i}. {c.name} | ⭐ {c.rating} ({c.reviews_count} reviews)")
       
