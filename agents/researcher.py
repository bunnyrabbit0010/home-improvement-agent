#researcher.py used to connect with FireCrawl to look for contractors

import os
from typing import List
from urllib import response
from pydantic import BaseModel, Field
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
fc_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
logging.info("FirecrawlApp initialized successfully.")
#print(dir(fc_app))


# Structured Data Model
class Contractor(BaseModel):
    name: str = Field(description="The name of the company")
    rating: float = Field(description="The Yelp star rating")
    reviews_count: int = Field(description="Number of reviews")

class ContractorList(BaseModel):
    contractors: List[Contractor]


def search_contractors(service: str, zip_code: str):
    print(f"🔎 Searching for {service} in {zip_code}...")
    
    url = f"https://www.yelp.com/search?find_desc={service}&find_loc={zip_code}"
    
    try:
        # In the latest SDK, 'extract' is replaced by jsonOptions within the scrape call
        # Assuming ContractorList is a Pydantic model
        '''response = fc_app.scrape(
            url=url,
            formats=['json'], 
            extract={
                'schema': ContractorList.model_json_schema(),
                'systemPrompt': f"Find the top 5 {service} companies with their ratings."
            }
        )
        
        # The data is returned in the 'json' key
        return response.get('json', {}).get('contractors', [])
        '''
        # Use extract instead of scrape
        response = fc_app.extract(
            urls=[url],  # Note: extract takes a list of URLs
            prompt=f"Find the top 5 {service} companies with their ratings.",
            schema=ContractorList.model_json_schema()
        )

        if response.success:
            # This will contain your extracted JSON/Object
            # 1. Take the raw dictionary from Firecrawl
            raw_data = response.data 
            
            # 2. Turn it back into your Pydantic Class
            # This gives you "Object" powers (c.name instead of c['name'])
            validated = ContractorList.model_validate(raw_data)
            
            # 3. Return the list of OBJECTS
            return validated.contractors       
        else:
            print(f"Extraction failed: {response.error}")
 
     
    except Exception as e:
        print(f"Detailed Error: {e}")
        return []
    
if __name__ == "__main__":
    # Get user context
    service_type = input("What service are you looking for? (e.g., Roofing, Plumbing): ")
    zip_code = input("Enter your ZIP code: ")
    
    logging.info(f"User is looking for {service_type} in {zip_code}.")
    results = search_contractors(service_type, zip_code)
    
    logging.info(f"Found {len(results)} contractors for {service_type} in {zip_code}.")

    logging.info(f"Displaying top 5 results for {service_type} in {zip_code}.")
    for i, c in enumerate(results[:5], 1):
        logging.info(f"{i}. {c.name} | ⭐ {c.rating} ({c.reviews_count} reviews)")
       