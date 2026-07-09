from __future__ import annotations

from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.llm import PlannerUnavailable, build_plan, compose_response
from app.agent.tools import TOOL_LABELS, TOOL_REGISTRY
from app.schemas import ChatResponse, InteractionDraft, InteractionPlan, InteractionPreferences, ToolTrace


class AgentState(TypedDict, total=False):
    user_message: str
    draft: dict[str, Any]
    preferences: dict[str, Any]
    model_override: str | None
    plan: InteractionPlan
    plan_error: str
    profile: dict[str, Any]
    tool_trace: list[dict[str, Any]]
    assistant_message: str


def _plan_node(state: AgentState) -> AgentState:
    draft = InteractionDraft(**state.get("draft", {}))
    preferences = InteractionPreferences(**state.get("preferences", {}))
    try:
        plan = build_plan(state["user_message"], draft, preferences, state.get("model_override"))
        return {"plan": plan}
    except PlannerUnavailable as exc:
        # AI-only by design: never fabricate a plan with hard-coded logic. Surface it.
        return {
            "plan": InteractionPlan(intent="help", tool_calls=[], planner_mode="error"),
            "plan_error": str(exc),
        }


def _execute_tools_node(state: AgentState) -> AgentState:
    draft = InteractionDraft(**state.get("draft", {}))
    plan = state["plan"]
    trace: list[dict[str, Any]] = []
    profile: dict[str, Any] = state.get("profile", {})

    for call in plan.tool_calls:
        tool = TOOL_REGISTRY.get(call.tool_name)
        if tool is None:
            trace.append(
                ToolTrace(
                    name=call.tool_name,
                    label=call.tool_name,
                    status="skipped",
                    summary="Tool is not registered.",
                ).model_dump()
            )
            continue

        args = dict(call.arguments)
        args.setdefault("current_draft", draft.model_dump())
        if call.tool_name in {"log_interaction", "edit_interaction", "schedule_follow_up"}:
            args.setdefault("preferences", state.get("preferences", {}))
        if call.tool_name == "recommend_next_best_action":
            args.setdefault("profile", profile)
        if call.tool_name == "compliance_guardrail":
            args.setdefault("message", state["user_message"])

        result = tool.invoke(args)
        if isinstance(result, dict) and "draft" in result:
            draft = InteractionDraft(**result["draft"])
        if isinstance(result, dict) and "profile" in result:
            profile = result["profile"]

        summary = result.get("summary", "Tool completed.") if isinstance(result, dict) else str(result)
        trace.append(
            ToolTrace(
                name=call.tool_name,
                label=TOOL_LABELS.get(call.tool_name, call.tool_name),
                status="completed",
                summary=summary,
                payload=result if isinstance(result, dict) else {"result": result},
            ).model_dump()
        )

    return {"draft": draft.model_dump(), "profile": profile, "tool_trace": trace}


def _respond_node(state: AgentState) -> AgentState:
    if state.get("plan_error"):
        return {
            "assistant_message": (
                "The AI planner is unavailable right now, so nothing on the form was changed. "
                f"({state['plan_error']}) Check the Developer settings: confirm the Groq API key is "
                "configured, the selected model is reachable, and live LLM mode is enabled."
            )
        }
    draft = InteractionDraft(**state.get("draft", {}))
    message = compose_response(
        message=state["user_message"],
        draft=draft,
        plan=state["plan"],
        tool_trace=state.get("tool_trace", []),
    )
    return {"assistant_message": message}


@lru_cache
def _compiled_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", _plan_node)
    graph.add_node("tool_executor", _execute_tools_node)
    graph.add_node("responder", _respond_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "tool_executor")
    graph.add_edge("tool_executor", "responder")
    graph.add_edge("responder", END)
    return graph.compile()


def run_agent(
    message: str,
    draft: InteractionDraft | None = None,
    preferences: InteractionPreferences | None = None,
    model_override: str | None = None,
) -> ChatResponse:
    initial_draft = draft or InteractionDraft()
    active_preferences = preferences or InteractionPreferences()
    result = _compiled_graph().invoke(
        {
            "user_message": message,
            "draft": initial_draft.model_dump(),
            "preferences": active_preferences.model_dump(),
            "model_override": model_override,
            "tool_trace": [],
        }
    )
    plan = result.get("plan")
    return ChatResponse(
        assistant_message=result["assistant_message"],
        draft=InteractionDraft(**result["draft"]),
        tool_trace=[ToolTrace(**item) for item in result.get("tool_trace", [])],
        planner_mode=getattr(plan, "planner_mode", "error"),
        planner_model=getattr(plan, "planner_model", ""),
    )
