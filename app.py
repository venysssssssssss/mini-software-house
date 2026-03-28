"""Streamlit Dashboard v2 — Mini Software House Agent Pipeline."""

import json
from datetime import datetime, timezone

import streamlit as st
from sqlmodel import Session, col, create_engine, func, select

from src.core.events import EventBus
from src.core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus

# ---------------------------------------------------------------------------
# DB connection (read-only queries)
# ---------------------------------------------------------------------------
engine = create_engine("sqlite:///software_house.db", echo=False)

st.set_page_config(page_title="Mini Software House", layout="wide")
st.title("Mini Software House — Dashboard")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
page = st.sidebar.radio(
    "Navigate",
    ["Pipeline History", "Agent Performance", "Error Patterns", "Live Run View"],
)

if st.sidebar.button("Refresh"):
    st.rerun()


# ---------------------------------------------------------------------------
# Page: Pipeline History
# ---------------------------------------------------------------------------
def page_pipeline_history():
    st.header("Pipeline History")

    with Session(engine) as session:
        runs = session.exec(
            select(PipelineRun).order_by(col(PipelineRun.started_at).desc()).limit(50)
        ).all()

    if not runs:
        st.info("No pipeline runs found. Run `make run TASK='...'` to generate data.")
        return

    # Summary metrics
    total = len(runs)
    succeeded = sum(1 for r in runs if r.status == TaskStatus.COMPLETED)
    failed = sum(1 for r in runs if r.status == TaskStatus.FAILED)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs", total)
    col2.metric("Succeeded", succeeded)
    col3.metric("Failed", failed)
    col4.metric("Success Rate", f"{succeeded / total * 100:.0f}%" if total else "N/A")

    # Runs table
    rows = []
    for r in runs:
        rows.append(
            {
                "ID": r.id,
                "Request": (r.user_request[:80] + "...") if len(r.user_request) > 80 else r.user_request,
                "Status": r.status.value,
                "Phases": f"{r.completed_phases}/{r.total_phases}",
                "Duration (s)": round(r.execution_time_s, 1) if r.execution_time_s else "-",
                "Tokens (in)": r.total_prompt_tokens,
                "Tokens (out)": r.total_response_tokens,
                "Agent Calls": r.total_agent_calls,
                "Started": r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "-",
            }
        )

    st.dataframe(rows, use_container_width=True)

    # Detail expander for each run
    for r in runs[:10]:
        with st.expander(f"Run #{r.id} — {r.user_request[:60]}"):
            st.json(
                {
                    "id": r.id,
                    "status": r.status.value,
                    "phases_completed": r.completed_phases,
                    "total_prompt_tokens": r.total_prompt_tokens,
                    "total_response_tokens": r.total_response_tokens,
                    "total_latency_ms": round(r.total_latency_ms, 1),
                    "total_agent_calls": r.total_agent_calls,
                    "execution_time_s": round(r.execution_time_s, 2) if r.execution_time_s else None,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                }
            )


# ---------------------------------------------------------------------------
# Page: Agent Performance
# ---------------------------------------------------------------------------
def page_agent_performance():
    st.header("Agent Performance")

    with Session(engine) as session:
        # Query aggregated agent metrics
        logs = session.exec(
            select(AgentLog).where(AgentLog.message == "llm_call")
        ).all()

    if not logs:
        st.info("No agent call data found. Run the pipeline to generate metrics.")
        return

    # Group by agent
    agent_stats: dict[str, dict] = {}
    for log in logs:
        name = log.agent_name
        if name not in agent_stats:
            agent_stats[name] = {
                "calls": 0,
                "successes": 0,
                "total_latency_ms": 0.0,
                "total_prompt_tokens": 0,
                "total_response_tokens": 0,
                "model": log.model or "unknown",
            }
        s = agent_stats[name]
        s["calls"] += 1
        s["successes"] += 1 if log.success else 0
        s["total_latency_ms"] += log.latency_ms
        s["total_prompt_tokens"] += log.prompt_tokens
        s["total_response_tokens"] += log.response_tokens

    # Display as table
    rows = []
    for agent, s in sorted(agent_stats.items()):
        avg_latency = s["total_latency_ms"] / s["calls"] if s["calls"] else 0
        success_rate = s["successes"] / s["calls"] * 100 if s["calls"] else 0
        rows.append(
            {
                "Agent": agent,
                "Model": s["model"],
                "Calls": s["calls"],
                "Success Rate": f"{success_rate:.0f}%",
                "Avg Latency (ms)": round(avg_latency, 1),
                "Total Prompt Tokens": s["total_prompt_tokens"],
                "Total Response Tokens": s["total_response_tokens"],
            }
        )

    st.dataframe(rows, use_container_width=True)

    # Per-agent charts
    st.subheader("Latency Distribution")
    for agent in sorted(agent_stats.keys()):
        latencies = [
            log.latency_ms for log in logs if log.agent_name == agent
        ]
        if latencies:
            st.write(f"**{agent}** — {len(latencies)} calls, avg {sum(latencies)/len(latencies):.1f}ms")
            st.bar_chart(latencies)


# ---------------------------------------------------------------------------
# Page: Error Patterns
# ---------------------------------------------------------------------------
def page_error_patterns():
    st.header("Error Patterns")

    with Session(engine) as session:
        # Failed test logs
        error_logs = session.exec(
            select(AgentLog).where(
                AgentLog.level == "WARNING",
                AgentLog.message == "Tests failed",
            )
        ).all()

        # DPO tuples with errors
        dpo_entries = session.exec(
            select(DPOTuple).where(DPOTuple.error_type.isnot(None))  # type: ignore[union-attr]
        ).all()

    if not error_logs and not dpo_entries:
        st.info("No error data found. Errors are logged when tests fail during pipeline runs.")
        return

    # Error type distribution
    st.subheader("Error Type Distribution")
    error_types: dict[str, int] = {}
    for log in error_logs:
        if log.structured_data:
            data = json.loads(log.structured_data)
            etype = data.get("error_type", "unknown") or "unknown"
            error_types[etype] = error_types.get(etype, 0) + 1

    for entry in dpo_entries:
        etype = entry.error_type or "unknown"
        error_types[etype] = error_types.get(etype, 0) + 1

    if error_types:
        st.bar_chart(error_types)

    # Correction success rates
    st.subheader("Self-Healing Success Rates")
    correction_stats: dict[str, dict] = {}
    for entry in dpo_entries:
        etype = entry.error_type or "unknown"
        if etype not in correction_stats:
            correction_stats[etype] = {"total": 0, "successful": 0}
        correction_stats[etype]["total"] += 1
        if entry.correction_successful:
            correction_stats[etype]["successful"] += 1

    if correction_stats:
        rows = []
        for etype, stats in sorted(correction_stats.items()):
            rate = stats["successful"] / stats["total"] * 100 if stats["total"] else 0
            rows.append(
                {
                    "Error Type": etype,
                    "Attempts": stats["total"],
                    "Successful": stats["successful"],
                    "Success Rate": f"{rate:.0f}%",
                }
            )
        st.dataframe(rows, use_container_width=True)

    # Recent error details
    st.subheader("Recent Errors")
    for log in error_logs[:20]:
        if log.structured_data:
            data = json.loads(log.structured_data)
            with st.expander(
                f"{data.get('error_type', 'unknown')} — attempt {data.get('attempt', '?')}"
            ):
                st.code(data.get("error", "No details"), language="text")


# ---------------------------------------------------------------------------
# Page: Live Run View
# ---------------------------------------------------------------------------
def page_live_run():
    st.header("Live Run View")

    # Show current EventBus state
    history = EventBus.get_history()

    if not history:
        st.info(
            "No live events. Events appear here when a pipeline is running "
            "in the same process. Start a run with `make run TASK='...'`."
        )
    else:
        st.subheader(f"Event Stream ({len(history)} events)")
        for event in reversed(history[-50:]):
            status_icon = {
                "pipeline.started": "🚀",
                "pipeline.finished": "🏁",
                "phase.started": "▶️",
                "phase.completed": "✅",
                "test.failed": "❌",
            }.get(event.type, "📌")

            st.write(
                f"{status_icon} **{event.type}** — "
                f"`{event.timestamp.strftime('%H:%M:%S')}` — "
                f"{json.dumps(event.payload, default=str)}"
            )

    # Also show state.json if available
    import os

    state_file = "workspace/state.json"
    if os.path.exists(state_file):
        st.subheader("Pipeline State (state.json)")
        with open(state_file, "r") as f:
            state = json.load(f)
        st.write(f"**Task:** {state.get('task', 'N/A')}")
        st.write(f"**Phase:** {state.get('phase', 1)} / 5")
        st.write(f"**Retries Left:** {state.get('retries', 0)}")
        st.progress(state.get("phase", 1) / 5)
        if state.get("plan"):
            with st.expander("View Plan"):
                st.json(state["plan"])

    # Show run log
    log_file = "workspace/run.log"
    if os.path.exists(log_file):
        st.subheader("Execution Logs")
        with open(log_file, "r") as f:
            logs = f.read()
        st.text_area("Live Logs", logs, height=400)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if page == "Pipeline History":
    page_pipeline_history()
elif page == "Agent Performance":
    page_agent_performance()
elif page == "Error Patterns":
    page_error_patterns()
elif page == "Live Run View":
    page_live_run()
