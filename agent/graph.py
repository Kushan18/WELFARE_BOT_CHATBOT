import logging
from langgraph.graph import StateGraph, END
from agent.state import ConversationState
from agent.nodes import (
    detect_intent,
    handle_onboarding,
    handle_faq,
    handle_scheme_query,
    handle_reminder,
)

logger = logging.getLogger(__name__)

def build_graph(groq_client, users_collection, schemes_collection):
    """Create a LangGraph workflow for WelfareBot.

    Only the essential handlers are used after the Groq‑only migration:
    * ``detect_intent`` – determines the user intent.
    * ``handle_onboarding`` – collects profile information.
    * ``handle_faq`` – answers generic questions.
    * ``handle_scheme_query`` – returns matching welfare schemes.
    * ``handle_reminder`` – handles reminder scheduling.
    """
    # expose shared resources to nodes (if they need them)
    import agent.nodes as nodes
    nodes.groq_client = groq_client
    nodes.users_collection = users_collection
    nodes.schemes_collection = schemes_collection

    workflow = StateGraph(ConversationState)
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("handle_onboarding", handle_onboarding)
    workflow.add_node("handle_faq", handle_faq)
    workflow.add_node("handle_scheme_query", handle_scheme_query)
    workflow.add_node("handle_reminder", handle_reminder)

    # Conditional routing based on detected intent
    workflow.add_conditional_edges(
        "detect_intent",
        lambda state: state.get("intent", "unclear"),
        {
            "onboarding": "handle_onboarding",
            "scheme_query": "handle_scheme_query",
            "faq": "handle_faq",
            "schedule_reminder": "handle_reminder",
            "unclear": "handle_faq",  # fallback to FAQ handler
            "change_lang": END,
        },
    )

    # Conditional routing from handle_onboarding (in case it changes intent)
    workflow.add_conditional_edges(
        "handle_onboarding",
        lambda state: state.get("intent", "unclear"),
        {
            "scheme_query": "handle_scheme_query",
            "faq": "handle_faq",
            "schedule_reminder": "handle_reminder",
            "unclear": END,
            "onboarding": END,
        },
    )

    # End transitions – leaf nodes finish the conversation
    workflow.add_edge("handle_faq", END)
    workflow.add_edge("handle_scheme_query", END)
    workflow.add_edge("handle_reminder", END)

    workflow.set_entry_point("detect_intent")
    
    compiled = workflow.compile()
    logger.info("Graph compiled successfully")
    return compiled