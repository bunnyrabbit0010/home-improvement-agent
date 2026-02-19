from langgraph.graph import END, StateGraph

from agents.workflows.state import AgentState


def scrape_yelp_node(state: AgentState) -> AgentState:
    return state


def scrape_google_node(state: AgentState) -> AgentState:
    return state


def scrape_bbb_node(state: AgentState) -> AgentState:
    return state


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

