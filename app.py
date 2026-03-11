import streamlit as st
import json
import os

st.title("🤖 Mini Software House - Agent Pipeline Status")

STATE_FILE = "workspace/state.json"
LOG_FILE = "workspace/run.log"

st.sidebar.header("Controls")
if st.sidebar.button("Refresh"):
    st.rerun()

st.header("Pipeline State")
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    
    st.write(f"**Current Task:** {state.get('task', 'N/A')}")
    st.write(f"**Current Phase:** {state.get('phase', 1)} / 5")
    st.write(f"**Retries Left:** {state.get('retries', 0)}")
    
    st.progress(state.get('phase', 1) / 5)
    
    if state.get('plan'):
        with st.expander("View Plan"):
            st.json(state['plan'])
else:
    st.info("No active pipeline state found.")

st.header("Execution Logs")
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        logs = f.read()
    st.text_area("Live Logs", logs, height=400)
else:
    st.info("No logs found.")
