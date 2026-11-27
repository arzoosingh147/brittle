import json
import logging
from typing import Dict, Any, List

try:
    from langchain_core.messages import SystemMessage, HumanMessage
except ImportError:
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content

from app.agents.state import AgentReviewState
from app.agents.schemas import SpecialistReviewOutput, AggregatedReviewOutput, InlineCommentOutput
from app.agents.prompts import (
    SECURITY_AGENT_SYSTEM_PROMPT,
    PERFORMANCE_AGENT_SYSTEM_PROMPT,
    QUALITY_AGENT_SYSTEM_PROMPT,
    AGGREGATOR_SYSTEM_PROMPT,
)
from app.core.llm import LLMFactory
from app.core.config import settings

logger = logging.getLogger(__name__)


def _format_diff_for_llm(parsed_files: List[Dict[str, Any]], max_chars: int = 15000) -> str:
    """Formats parsed diff into a clear prompt representation within token budget."""
    formatted = []
    char_count = 0
    for f in parsed_files:
        header = f"--- FILE: {f.get('target_file') or f.get('source_file')} ---\n"
        patch = f.get("full_patch", "")
        if len(patch) > 3000:
            patch = patch[:3000] + "\n...[truncated remainder of file diff]...\n"
        block = header + patch + "\n"
        if char_count + len(block) > max_chars:
            formatted.append("\n...[Remaining diff omitted to respect token budget]...\n")
            break
        formatted.append(block)
        char_count += len(block)
    return "".join(formatted)


def _format_context(retrieved_context: List[Dict[str, Any]]) -> str:
    if not retrieved_context:
        return "No cross-file codebase context available."
    out = []
    for c in retrieved_context:
        out.append(f"File: {c.get('file_path')} (lines {c.get('start_line')}-{c.get('end_line')}):\n```\n{c.get('content', '')}\n```")
    return "\n\n".join(out)


async def retrieve_context_node(state: AgentReviewState) -> Dict[str, Any]:
    retrieved = state.get("retrieved_context") or []
    return {"retrieved_context": retrieved}


async def security_agent_node(state: AgentReviewState) -> Dict[str, Any]:
    llm = LLMFactory.get_review_model(temperature=0.1)
    diff_text = _format_diff_for_llm(state.get("parsed_files", []))
    context_text = _format_context(state.get("retrieved_context", []))

    prompt = (
        f"PR Title: {state.get('title', 'Unknown')}\n\n"
        f"CROSS-FILE CONTEXT:\n{context_text}\n\n"
        f"DIFF TO REVIEW:\n{diff_text}"
    )

    try:
        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(SpecialistReviewOutput)
            res: SpecialistReviewOutput = await structured_llm.ainvoke([
                SystemMessage(content=SECURITY_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            findings = [f.model_dump() for f in res.findings]
            for f in findings:
                f["agent_name"] = "security"
            return {"security_findings": findings}
    except Exception as e:
        logger.warning(f"Structured invocation failed in security agent: {e}")

    return {"security_findings": []}


async def performance_agent_node(state: AgentReviewState) -> Dict[str, Any]:
    llm = LLMFactory.get_review_model(temperature=0.1)
    diff_text = _format_diff_for_llm(state.get("parsed_files", []))
    context_text = _format_context(state.get("retrieved_context", []))

    prompt = (
        f"PR Title: {state.get('title', 'Unknown')}\n\n"
        f"CROSS-FILE CONTEXT:\n{context_text}\n\n"
        f"DIFF TO REVIEW:\n{diff_text}"
    )

    try:
        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(SpecialistReviewOutput)
            res: SpecialistReviewOutput = await structured_llm.ainvoke([
                SystemMessage(content=PERFORMANCE_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            findings = [f.model_dump() for f in res.findings]
            for f in findings:
                f["agent_name"] = "performance"
            return {"performance_findings": findings}
    except Exception as e:
        logger.warning(f"Structured invocation failed in performance agent: {e}")

    return {"performance_findings": []}


async def quality_agent_node(state: AgentReviewState) -> Dict[str, Any]:
    llm = LLMFactory.get_review_model(temperature=0.2)
    diff_text = _format_diff_for_llm(state.get("parsed_files", []))
    context_text = _format_context(state.get("retrieved_context", []))
    rules_json = json.dumps(state.get("rules", {}), indent=2)

    prompt = (
        f"PR Title: {state.get('title', 'Unknown')}\n\n"
        f"CUSTOM REPO RULES:\n{rules_json}\n\n"
        f"CROSS-FILE CONTEXT:\n{context_text}\n\n"
        f"DIFF TO REVIEW:\n{diff_text}"
    )

    try:
        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(SpecialistReviewOutput)
            res: SpecialistReviewOutput = await structured_llm.ainvoke([
                SystemMessage(content=QUALITY_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            findings = [f.model_dump() for f in res.findings]
            for f in findings:
                f["agent_name"] = "quality"
            return {"quality_findings": findings}
    except Exception as e:
        logger.warning(f"Structured invocation failed in quality agent: {e}")

    return {"quality_findings": []}


async def aggregator_node(state: AgentReviewState) -> Dict[str, Any]:
    sec_findings = state.get("security_findings", [])
    perf_findings = state.get("performance_findings", [])
    qual_findings = state.get("quality_findings", [])

    all_raw_findings = sec_findings + perf_findings + qual_findings

    deduped: Dict[str, Dict[str, Any]] = {}
    severity_order = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}

    for f in all_raw_findings:
        key = f"{f.get('file_path')}:{f.get('line_number')}"
        if key not in deduped:
            deduped[key] = f
        else:
            existing_sev = severity_order.get(deduped[key].get("severity", "MEDIUM"), 3)
            current_sev = severity_order.get(f.get("severity", "MEDIUM"), 3)
            if current_sev > existing_sev:
                deduped[key] = f

    final_comments = list(deduped.values())

    sec_count = sum(1 for f in final_comments if f.get("agent_name") == "security")
    perf_count = sum(1 for f in final_comments if f.get("agent_name") == "performance")
    qual_count = sum(1 for f in final_comments if f.get("agent_name") == "quality")

    critical_count = sum(1 for f in final_comments if f.get("severity") == "CRITICAL")
    high_count = sum(1 for f in final_comments if f.get("severity") == "HIGH")

    base_risk = 1
    base_risk += critical_count * 4
    base_risk += high_count * 2
    base_risk += len(final_comments)
    risk_score = min(10, max(1, base_risk))

    if critical_count > 0 or high_count >= 2 or risk_score >= 7:
        recommendation = "REQUEST_CHANGES"
    elif risk_score <= 3 and critical_count == 0 and high_count == 0:
        recommendation = "APPROVE"
    else:
        recommendation = "COMMENT"

    summary = (
        f"Brittle AI Review completed across {len(state.get('parsed_files', []))} files.\n"
        f"Risk Score: {risk_score}/10 | Recommendation: {recommendation}.\n"
        f"Detected {sec_count} security concerns, {perf_count} performance issues, and {qual_count} quality suggestions."
    )

    aggregated = {
        "summary": summary,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "comments": final_comments,
        "security_issues_count": sec_count,
        "perf_issues_count": perf_count,
        "quality_issues_count": qual_count,
    }

    return {"aggregated_review": aggregated}
