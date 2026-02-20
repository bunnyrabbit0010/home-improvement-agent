from typing import List, Optional, TypedDict

from schema.models import Contractor, VettedContractor


class AgentState(TypedDict):
    service_type: Optional[str]
    target_contractor_count: Optional[int]
    contractor_name: Optional[str]
    selected_contractor_index: Optional[int]
    zip_code: str
    yelp_candidates: List[Contractor]
    contractor_data: Optional[VettedContractor]
    yelp_url: Optional[str]
    google_url: Optional[str]
    bbb_url: Optional[str]
    raw_yelp_data: Optional[str]
    raw_google_data: Optional[str]
    raw_bbb_data: Optional[str]
    raw_website_data: Optional[str]
    raw_synthesis_data: Optional[str]
    flags: List[str]
