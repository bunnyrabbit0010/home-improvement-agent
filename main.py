import json
import logging

from workflows.discovery_vetting_graph import build_discovery_vetting_graph


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    service_type = input("Service type (e.g., plumbing, electrical): ").strip()
    zip_code = input("ZIP code: ").strip()
    target_input = input("Target contractor count [default: 5]: ").strip()

    target_count = 5
    if target_input:
        try:
            target_count = int(target_input)
        except ValueError:
            logger.warning("Invalid target count '%s'. Defaulting to 5.", target_input)

    graph = build_discovery_vetting_graph()
    initial_state = {
        "service_type": service_type or "home improvement",
        "target_contractor_count": target_count,
        "contractor_name": None,
        "selected_contractor_index": 0,
        "zip_code": zip_code,
        "yelp_candidates": [],
        "contractor_data": None,
        "yelp_url": None,
        "google_url": None,
        "bbb_url": None,
        "raw_yelp_data": None,
        "raw_google_data": None,
        "raw_bbb_data": None,
        "raw_website_data": None,
        "raw_synthesis_data": None,
        "flags": [],
    }
    final_state = graph.invoke(initial_state)

    print("\n=== Consolidated Summary ===")
    synthesis = final_state.get("raw_synthesis_data")
    if synthesis:
        try:
            print(json.dumps(json.loads(synthesis), indent=2))
        except Exception:
            print(synthesis)
    else:
        print("No synthesis output generated.")

    if final_state.get("flags"):
        print("\n=== Flags ===")
        for flag in final_state["flags"]:
            print(f"- {flag}")


if __name__ == "__main__":
    main()
