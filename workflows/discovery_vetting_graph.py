import logging

from langgraph.graph import END, StateGraph

from tools.firecrawl_tool import get_bbb_info, get_google_reviews, search_contractors
from workflows.state import AgentState

logger = logging.getLogger(__name__)


def scrape_yelp_node(state: AgentState) -> AgentState:
    updated_state = dict(state)
    flags = list(updated_state.get("flags", []))

    zip_code = (updated_state.get("zip_code") or "").strip()
    service_type = (updated_state.get("service_type") or "roofing").strip()
    logger.info(
        "Starting Yelp discovery for service='%s', zip='%s'.",
        service_type,
        zip_code,
    )

    if not zip_code:
        logger.warning("Skipping Yelp discovery because zip_code is missing.")
        flags.append("Missing zip_code for Yelp discovery.")
        updated_state["flags"] = flags
        updated_state["raw_yelp_data"] = ""
        return updated_state

    try:
        search_result = search_contractors(service_type, zip_code)
        contractors = search_result.contractors
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

        if not (updated_state.get("contractor_name") or "").strip():
            updated_state["contractor_name"] = contractors[0].name

        updated_state["yelp_url"] = search_result.source_url
        updated_state["raw_yelp_data"] = "\n".join(
            f"{idx}. {contractor.name} | rating={contractor.rating} | reviews={contractor.reviews_count}"
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

    contractor_name = (updated_state.get("contractor_name") or "").strip()
    zip_code = (updated_state.get("zip_code") or "").strip()
    logger.info(
        "Starting Google review scrape for contractor='%s', zip='%s'.",
        contractor_name,
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
        google_content = get_google_reviews(contractor_name, zip_code)
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

    contractor_name = (updated_state.get("contractor_name") or "").strip()
    zip_code = (updated_state.get("zip_code") or "").strip()
    logger.info(
        "Starting BBB scrape for contractor='%s', zip='%s'.",
        contractor_name,
        zip_code,
    )

    if not contractor_name or not zip_code:
        logger.warning("Skipping BBB scrape due to missing contractor_name or zip_code.")
        flags.append("Missing contractor_name or zip_code for BBB scrape.")
        updated_state["flags"] = flags
        updated_state["raw_bbb_data"] = ""
        return updated_state

    try:
        bbb_content = get_bbb_info(contractor_name, zip_code)
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
    return state


def synthesize_vetting_node(state: AgentState) -> AgentState:
    return state


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
