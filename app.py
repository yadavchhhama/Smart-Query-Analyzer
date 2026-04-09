"""
app.py
------
Streamlit UI for the Smart Query Analyzer.
Run with:  streamlit run app.py

Requirements:
    pip install streamlit pandas mysql-connector-python
"""

import streamlit as st
import pandas as pd

from database import setup_database, get_schema_info
from nl2sql   import natural_to_sql
from executor import execute_query, analyze_query

st.set_page_config(
    page_title="Smart Query Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

.hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 2rem;
    border: 1px solid rgba(255,255,255,0.07);
}
.hero h1 { font-size: 2.4rem; font-weight: 800; color: #fff; letter-spacing: -0.5px; margin: 0 0 0.3rem; }
.hero p   { color: rgba(255,255,255,0.6); font-size: 1rem; margin: 0; }
.accent   { color: #7c6af7; }

.card {
    background: #1a1a2e;
    border: 1px solid rgba(124,106,247,0.2);
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.card-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #7c6af7; margin-bottom: 0.75rem;
}

.sql-block {
    font-family: 'JetBrains Mono', monospace;
    background: #0d0d1a;
    border: 1px solid rgba(124,106,247,0.3);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    color: #a9b7ff;
    font-size: 0.88rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
}

.sug-warning { background: rgba(255,180,50,0.1);   border-left: 3px solid #ffb432; padding: 0.7rem 1rem; border-radius: 6px; margin-bottom: 0.6rem; font-size: 0.88rem; color: #ffe0a0; }
.sug-tip     { background: rgba(80,200,255,0.08);  border-left: 3px solid #50c8ff; padding: 0.7rem 1rem; border-radius: 6px; margin-bottom: 0.6rem; font-size: 0.88rem; color: #b0e8ff; }
.sug-info    { background: rgba(100,220,150,0.08); border-left: 3px solid #64dc96; padding: 0.7rem 1rem; border-radius: 6px; margin-bottom: 0.6rem; font-size: 0.88rem; color: #b0f0cc; }

.stButton > button {
    background: linear-gradient(90deg, #7c6af7, #5c4de8) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    padding: 0.55rem 2rem !important; font-size: 0.95rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Initialise DB once per session
# ─────────────────────────────────────────────────────────────────────────────
if "db_ready" not in st.session_state:
    try:
        setup_database()
        st.session_state["db_ready"] = True
    except Exception as e:
        st.error(f"⚠️ Could not connect to MySQL: {e}")
        st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Hero header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔍 Smart Query <span class="accent">Analyzer</span></h1>
  <p>Type a question in plain English — get SQL, results, timing &amp; optimization tips instantly.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Input area
# ─────────────────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("prefill", "")

user_input = st.text_input(
    label="Natural Language Query",
    value=prefill,
    placeholder="e.g.  Show me orders above 300  |  Total amount per user  |  Top 5 orders",
    label_visibility="collapsed",
)

run_col, _ = st.columns([1, 5])
with run_col:
    run_btn = st.button("▶  Analyze Query", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Main logic
# ─────────────────────────────────────────────────────────────────────────────
if run_btn and user_input.strip():

    # Step 1: NL → SQL
    generated_sql, explanation = natural_to_sql(user_input)

    # Step 2: Execute
    exec_result = execute_query(generated_sql)

    # Step 3: Analyze
    suggestions = analyze_query(generated_sql)

    left, right = st.columns([1, 1], gap="large")

    # ── LEFT: Generated SQL ───────────────────────────────────────────────────
    with left:
        st.markdown('<div class="card"><div class="card-title">📝 Generated SQL</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sql-block">{generated_sql}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📋 Copy SQL"):
            st.code(generated_sql, language="sql")

        st.markdown(f"""
        <div class="card">
          <div class="card-title">💡 What this query does</div>
          {explanation}
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: Optimization suggestions ──────────────────────────────────────
    with right:
        st.markdown('<div class="card"><div class="card-title">⚡ Optimization Tips</div>', unsafe_allow_html=True)
        for s in suggestions:
            css_class = f"sug-{s['level']}"
            st.markdown(f'<div class="{css_class}">{s["message"]}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Execution metrics
        if exec_result["success"]:
            st.markdown(f"""
            <div class="card">
              <div class="card-title">📈 Execution Metrics</div>
              <span class="metric-pill">⏱ {exec_result["execution_ms"]} ms</span>
              <span class="metric-pill">📄 {exec_result["row_count"]} row(s)</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="card">
              <div class="card-title"> Query Error</div>
              <div class="sql-block">{exec_result["error"]}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Results table ─────────────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">📊 Query Results</div>', unsafe_allow_html=True)

    if exec_result["success"]:
        if exec_result["rows"]:
            df = pd.DataFrame(exec_result["rows"])
            st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(df)))
        else:
            st.info("Query executed successfully but returned no rows.")
    else:
        st.error("Could not display results due to the query error above.")

    st.markdown("</div>", unsafe_allow_html=True)

elif run_btn and not user_input.strip():
    st.warning("Please enter a question before clicking Analyze.")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<br>
<div style="text-align:center; color:rgba(255,255,255,0.2); font-size:0.78rem;">
    Smart Query Analyzer · Python + MySQL + Streamlit · Rule-based NL2SQL
</div>
""", unsafe_allow_html=True)