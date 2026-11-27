from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class AgentReviewState(TypedDict):
    """
    Central state container for the LangGraph multi-agent review workflow.
    """
    pr_id: int
    repository_id: int
    owner: str
    repo_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    title: str
    author: str
    raw_diff: str
    parsed_files: List[Dict[str, Any]]
    rules: Dict[str, Any]
    retrieved_context: List[Dict[str, Any]]
    
    # Specialist agent findings (collected in parallel branches)
    security_findings: List[Dict[str, Any]]
    performance_findings: List[Dict[str, Any]]
    quality_findings: List[Dict[str, Any]]

    # Final synthesized result
    aggregated_review: Optional[Dict[str, Any]]
    errors: Annotated[List[str], operator.add]
