from typing import List, Dict, Any, TypedDict

class AgentState(TypedDict):
    process_id: str
    industry: str
    process_name: str
    search_provider: str
    current_activities: List[Dict[str, Any]]
    research_queries: List[Dict[str, Any]]
    search_results: List[Dict[str, Any]]
    evidence_analyses: List[Dict[str, Any]]
    ai_opportunities: List[Dict[str, Any]]
    future_activities: List[Dict[str, Any]]
    error: str
