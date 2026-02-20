import logging
from pydantic import BaseModel, Field
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Structured Data Model
class Contractor(BaseModel):
    name: str = Field(description="The name of the company")
    rating: float = Field(description="The Yelp star rating")
    reviews_count: int = Field(description="Number of reviews")
    yelp_profile_url: Optional[str] = Field(
        default=None, description="Yelp business profile URL if available."
    )
    website: Optional[str] = Field(
        default=None, description="Official contractor website URL if available."
    )
    phone: Optional[str] = Field(
        default=None, description="Primary business phone number if available."
    )
    address: Optional[str] = Field(
        default=None, description="Business address if available."
    )

class ContractorList(BaseModel):
    contractors: List[Contractor]


class ContractorSearchResult(BaseModel):
    source_url: str
    service_type: str
    zip_code: str
    contractors: List[Contractor] = Field(default_factory=list)


class ContractorWebsiteInfo(BaseModel):
    source_url: Optional[str] = None
    services_offered: List[str] = Field(default_factory=list)
    license_number: Optional[str] = None
    years_in_business: Optional[int] = None


class ReviewSummary(BaseModel):
    positive_themes: List[str] = Field(default_factory=list, description="Key positive themes from reviews.")
    negative_themes: List[str] = Field(default_factory=list, description="Key negative themes from reviews.")
    overall_sentiment: str = Field(description="Overall sentiment (e.g., 'Positive', 'Mixed', 'Negative').")

class VettedContractor(BaseModel):
    name: str
    address: str
    phone: Optional[str]
    website: Optional[str]
    yelp_rating: Optional[float]
    yelp_review_count: Optional[int]
    google_rating: Optional[float]
    google_review_count: Optional[int]
    bbb_rating: Optional[str] = Field(description="Better Business Bureau rating (e.g., 'A+', 'B-').")
    bbb_accredited: bool
    services_offered: List[str] = Field(
        default_factory=list,
        description="Specific services offered by the contractor.",
    )
    license_number: Optional[str]
    years_in_business: Optional[int]
    review_summary: Optional[ReviewSummary]
    red_flags: List[str] = Field(default_factory=list, description="Identified issues requiring human review.")
