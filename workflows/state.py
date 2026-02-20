from typing import List, Optional, TypedDict

from schema.models import VettedContractor


class AgentState(TypedDict):
    service_type: Optional[str]
    contractor_name: str
    zip_code: str
    contractor_data: Optional[VettedContractor]
    yelp_url: Optional[str]
    google_url: Optional[str]
    bbb_url: Optional[str]
    raw_yelp_data: Optional[str]
    raw_google_data: Optional[str]
    raw_bbb_data: Optional[str]
    raw_website_data: Optional[str]
    flags: List[str]
