import logging
import json

from langgraph.graph import END, StateGraph

from tools.firecrawl_tool import (
    analyze_contractor_website,
    get_bbb_info,
    get_google_reviews,
    search_contractors,
)
from tools.llm_tool import summarize_reviews
from workflows.state import AgentState

logger = logging.getLogger(__name__)


def _resolve_selected_yelp_candidate(state: AgentState):
    candidates = state.get("yelp_candidates") or []
    selected_index = state.get("selected_contractor_index")
    if selected_index is None:
        selected_index = 0
    if not candidates:
        return None
    if selected_index < 0 or selected_index >= len(candidates):
        return None
    return candidates[selected_index]


def scrape_yelp_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    zip_code = (updated_state.get("zip_code") or "").strip()
    service_type = (updated_state.get("service_type") or "home improvement").strip()
    target_count = updated_state.get("target_contractor_count") or 5
    if target_count <= 0:
        logger.warning(
            "Invalid target_contractor_count='%s'; defaulting to 5.", target_count
        )
        flags.append(
            f"Invalid target_contractor_count='{target_count}', defaulted to 5."
        )
        target_count = 5

    logger.info(
        "Starting Yelp discovery for service='%s', zip='%s', target_count=%d.",
        service_type,
        zip_code,
        target_count,
    )

    if not zip_code:
        logger.warning("Skipping Yelp discovery because zip_code is missing.")
        flags.append("Missing zip_code for Yelp discovery.")
        updated_state["flags"] = flags
        updated_state["raw_yelp_data"] = ""
        return updated_state

    try:
        search_result = search_contractors(service_type, zip_code)
        contractors = search_result.contractors[:target_count]
        if not contractors:
            logger.warning(
                "No Yelp contractors found for service='%s' in zip='%s'.",
                service_type,
                zip_code,
            )
            flags.append(
                f"No Yelp contractors found for service='{service_type}' in zip='{zip_code}'."
            )
            updated_state["flags"] = flags
            updated_state["raw_yelp_data"] = ""
            return updated_state

        if len(search_result.contractors) < target_count:
            logger.warning(
                "Yelp returned %d contractors, below target_count=%d for service='%s' zip='%s'.",
                len(search_result.contractors),
                target_count,
                service_type,
                zip_code,
            )
            flags.append(
                f"Only {len(search_result.contractors)} contractors found; target was {target_count}."
            )

        if not (updated_state.get("contractor_name") or "").strip():
            updated_state["contractor_name"] = contractors[0].name

        updated_state["yelp_candidates"] = contractors
        updated_state["selected_contractor_index"] = 0
        updated_state["yelp_url"] = search_result.source_url
        updated_state["raw_yelp_data"] = "\n".join(
            f"{idx}. {contractor.name} | rating={contractor.rating} | reviews={contractor.reviews_count}"
            f" | phone={contractor.phone or 'n/a'} | website={contractor.website or 'n/a'}"
            f" | yelp_profile_url={contractor.yelp_profile_url or 'n/a'}"
            f" | address={contractor.address or 'n/a'}"
            for idx, contractor in enumerate(contractors, start=1)
        )
        updated_state["flags"] = flags

        logger.info(
            "Yelp discovery complete for service='%s' zip='%s' with %d candidates.",
            service_type,
            zip_code,
            len(contractors),
        )
        return updated_state
    except Exception:
        logger.exception(
            "Yelp discovery failed for service='%s', zip='%s'.",
            service_type,
            zip_code,
        )
        flags.append(
            f"Yelp discovery failed for service='{service_type}' in zip='{zip_code}'."
        )
        updated_state["flags"] = flags
        updated_state["raw_yelp_data"] = ""
        return updated_state


def scrape_google_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    yelp_candidates = updated_state.get("yelp_candidates") or []
    selected_index = updated_state.get("selected_contractor_index")
    selected_candidate = _resolve_selected_yelp_candidate(updated_state)
    if yelp_candidates and selected_candidate is None:
        logger.warning(
            "Selected contractor index '%s' is invalid for %d Yelp candidates.",
            selected_index,
            len(yelp_candidates),
        )
        flags.append(
            f"Invalid selected_contractor_index='{selected_index}' for Yelp candidates."
        )

    contractor_name = (
        (selected_candidate.name if selected_candidate else None)
        or updated_state.get("contractor_name")
        or ""
    ).strip()
    if contractor_name:
        updated_state["contractor_name"] = contractor_name
    service_type = (updated_state.get("service_type") or "home improvement").strip()
    zip_code = (updated_state.get("zip_code") or "").strip()
    logger.info(
        "Starting Google review scrape for contractor='%s', service='%s', zip='%s'.",
        contractor_name,
        service_type,
        zip_code,
    )

    if not contractor_name or not zip_code:
        logger.warning(
            "Skipping Google review scrape due to missing contractor_name or zip_code."
        )
        flags.append("Missing contractor_name or zip_code for Google review scrape.")
        updated_state["flags"] = flags
        updated_state["raw_google_data"] = ""
        return updated_state

    try:
        google_content = get_google_reviews(
            contractor_name,
            zip_code,
            service_type,
            expected_phone=selected_candidate.phone if selected_candidate else None,
            expected_address=selected_candidate.address if selected_candidate else None,
        )
        if not google_content:
            logger.warning(
                "No Google review content found for contractor='%s' zip='%s'.",
                contractor_name,
                zip_code,
            )
            flags.append(
                f"No Google review data found for contractor='{contractor_name}' in zip='{zip_code}'."
            )
            updated_state["flags"] = flags
            updated_state["raw_google_data"] = ""
            return updated_state

        updated_state["raw_google_data"] = google_content
        updated_state["flags"] = flags
        logger.info(
            "Google review scrape complete for contractor='%s' zip='%s'.",
            contractor_name,
            zip_code,
        )
        return updated_state
    except Exception:
        logger.exception(
            "Google review scrape failed for contractor='%s', zip='%s'.",
            contractor_name,
            zip_code,
        )
        flags.append(
            f"Google review scrape failed for contractor='{contractor_name}' in zip='{zip_code}'."
        )
        updated_state["flags"] = flags
        updated_state["raw_google_data"] = ""
        return updated_state


def scrape_bbb_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    yelp_candidates = updated_state.get("yelp_candidates") or []
    selected_index = updated_state.get("selected_contractor_index")
    selected_candidate = _resolve_selected_yelp_candidate(updated_state)
    if yelp_candidates and selected_candidate is None:
        logger.warning(
            "Selected contractor index '%s' is invalid for %d Yelp candidates.",
            selected_index,
            len(yelp_candidates),
        )
        flags.append(
            f"Invalid selected_contractor_index='{selected_index}' for Yelp candidates."
        )

    contractor_name = (
        (selected_candidate.name if selected_candidate else None)
        or updated_state.get("contractor_name")
        or ""
    ).strip()
    if contractor_name:
        updated_state["contractor_name"] = contractor_name
    service_type = (updated_state.get("service_type") or "home improvement").strip()
    zip_code = (updated_state.get("zip_code") or "").strip()
    logger.info(
        "Starting BBB scrape for contractor='%s', service='%s', zip='%s'.",
        contractor_name,
        service_type,
        zip_code,
    )

    if not contractor_name or not zip_code:
        logger.warning("Skipping BBB scrape due to missing contractor_name or zip_code.")
        flags.append("Missing contractor_name or zip_code for BBB scrape.")
        updated_state["flags"] = flags
        updated_state["raw_bbb_data"] = ""
        return updated_state

    try:
        bbb_content = get_bbb_info(contractor_name, zip_code, service_type)
        if not bbb_content:
            logger.warning(
                "No BBB content found for contractor='%s' zip='%s'.",
                contractor_name,
                zip_code,
            )
            flags.append(
                f"No BBB data found for contractor='{contractor_name}' in zip='{zip_code}'."
            )
            updated_state["flags"] = flags
            updated_state["raw_bbb_data"] = ""
            return updated_state

        updated_state["raw_bbb_data"] = bbb_content
        updated_state["flags"] = flags
        logger.info(
            "BBB scrape complete for contractor='%s' zip='%s'.",
            contractor_name,
            zip_code,
        )
        return updated_state
    except Exception:
        logger.exception(
            "BBB scrape failed for contractor='%s', zip='%s'.",
            contractor_name,
            zip_code,
        )
        flags.append(
            f"BBB scrape failed for contractor='{contractor_name}' in zip='{zip_code}'."
        )
        updated_state["flags"] = flags
        updated_state["raw_bbb_data"] = ""
        return updated_state


def scrape_website_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    service_type = (updated_state.get("service_type") or "home improvement").strip()
    yelp_candidates = updated_state.get("yelp_candidates") or []
    selected_index = updated_state.get("selected_contractor_index")
    selected_candidate = _resolve_selected_yelp_candidate(updated_state)
    if yelp_candidates and selected_candidate is None:
        logger.warning(
            "Selected contractor index '%s' is invalid for %d Yelp candidates.",
            selected_index,
            len(yelp_candidates),
        )
        flags.append(
            f"Invalid selected_contractor_index='{selected_index}' for Yelp candidates."
        )

    contractor_name = (
        (selected_candidate.name if selected_candidate else None)
        or updated_state.get("contractor_name")
        or ""
    ).strip()
    if contractor_name:
        updated_state["contractor_name"] = contractor_name

    contractor_data = updated_state.get("contractor_data")
    website_url = (selected_candidate.website if selected_candidate else None) or ""
    if not website_url and contractor_data and contractor_data.website:
        website_url = contractor_data.website.strip()

    logger.info(
        "Starting website scrape for contractor='%s', service='%s', website='%s'.",
        contractor_name,
        service_type,
        website_url,
    )

    if not website_url:
        logger.warning("Skipping website scrape because contractor website URL is missing.")
        flags.append("Missing contractor website URL for website scrape.")
        updated_state["flags"] = flags
        updated_state["raw_website_data"] = ""
        return updated_state

    try:
        website_info = analyze_contractor_website(website_url, service_type)
        if not website_info.services_offered and not website_info.license_number:
            logger.warning(
                "Website analysis returned sparse data for website='%s'.",
                website_url,
            )
            flags.append(
                f"Website analysis returned sparse data for website='{website_url}'."
            )

        updated_state["raw_website_data"] = website_info.model_dump_json()
        updated_state["flags"] = flags
        logger.info("Website scrape complete for website='%s'.", website_url)
        return updated_state
    except Exception:
        logger.exception("Website scrape failed for website='%s'.", website_url)
        flags.append(f"Website scrape failed for website='{website_url}'.")
        updated_state["flags"] = flags
        updated_state["raw_website_data"] = ""
        return updated_state


def synthesize_vetting_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    selected_candidate = _resolve_selected_yelp_candidate(updated_state)
    contractor_name = (
        (selected_candidate.name if selected_candidate else None)
        or updated_state.get("contractor_name")
        or ""
    ).strip()
    logger.info("Starting synthesis for contractor='%s'.", contractor_name)

    if not contractor_name:
        logger.warning("Skipping synthesis because no contractor is selected.")
        flags.append("No contractor selected for synthesis.")
        updated_state["flags"] = flags
        updated_state["raw_synthesis_data"] = ""
        return updated_state

    try:
        yelp_snippet = ""
        if selected_candidate:
            yelp_snippet = (
                f"name={selected_candidate.name}, rating={selected_candidate.rating}, "
                f"reviews={selected_candidate.reviews_count}, website={selected_candidate.website or 'n/a'}, "
                f"yelp_profile_url={selected_candidate.yelp_profile_url or 'n/a'}, "
                f"phone={selected_candidate.phone or 'n/a'}, address={selected_candidate.address or 'n/a'}"
            )

        review_input = "\n\n".join(
            part
            for part in [
                f"Yelp candidate details: {yelp_snippet}" if yelp_snippet else "",
                f"Google review content: {updated_state.get('raw_google_data') or ''}",
                f"BBB content: {updated_state.get('raw_bbb_data') or ''}",
            ]
            if part.strip()
        )
        review_summary = summarize_reviews(review_input)

        website_info = {}
        raw_website_data = (updated_state.get("raw_website_data") or "").strip()
        if raw_website_data:
            try:
                website_info = json.loads(raw_website_data)
            except Exception:
                logger.warning("Website data was not valid JSON; storing as raw text.")
                website_info = {"raw_text": raw_website_data}

        consolidated = {
            "contractor_name": contractor_name,
            "selected_contractor_index": updated_state.get("selected_contractor_index"),
            "service_type": updated_state.get("service_type"),
            "zip_code": updated_state.get("zip_code"),
            "yelp": {
                "source_url": updated_state.get("yelp_url"),
                "candidate": {
                    "name": selected_candidate.name,
                    "rating": selected_candidate.rating,
                    "reviews_count": selected_candidate.reviews_count,
                    "website": selected_candidate.website,
                    "yelp_profile_url": selected_candidate.yelp_profile_url,
                    "phone": selected_candidate.phone,
                    "address": selected_candidate.address,
                }
                if selected_candidate
                else None,
            },
            "google_reviews_raw": updated_state.get("raw_google_data"),
            "bbb_raw": updated_state.get("raw_bbb_data"),
            "website_analysis": website_info,
            "review_summary": review_summary.model_dump(),
            "flags": flags,
        }

        updated_state["raw_synthesis_data"] = json.dumps(consolidated, indent=2)
        updated_state["flags"] = flags
        logger.info("Synthesis complete for contractor='%s'.", contractor_name)
        return updated_state
    except Exception:
        logger.exception("Synthesis failed for contractor='%s'.", contractor_name)
        flags.append(f"Synthesis failed for contractor='{contractor_name}'.")
        updated_state["flags"] = flags
        updated_state["raw_synthesis_data"] = ""
        return updated_state


def build_discovery_vetting_graph():
    graph = StateGraph(AgentState)

    graph.add_node("scrape_yelp", scrape_yelp_node)
    graph.add_node("scrape_google", scrape_google_node)
    graph.add_node("scrape_bbb", scrape_bbb_node)
    graph.add_node("scrape_website", scrape_website_node)
    graph.add_node("synthesize_vetting", synthesize_vetting_node)

    graph.set_entry_point("scrape_yelp")
    graph.add_edge("scrape_yelp", "scrape_google")
    graph.add_edge("scrape_google", "scrape_bbb")
    graph.add_edge("scrape_bbb", "scrape_website")
    graph.add_edge("scrape_website", "synthesize_vetting")
    graph.add_edge("synthesize_vetting", END)

    return graph.compile()
