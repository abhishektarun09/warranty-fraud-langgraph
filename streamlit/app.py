import streamlit as st
import pandas as pd
from main import process_claims
import io

# Page config
st.set_page_config(page_title="Warranty Fraud Detector", layout="wide")


# --- Styles and header ---
st.markdown(
    """
    <style>
    /* ---- App background ---- */
    .stApp {
        background: #f8fafc;
        color: #0f172a;
    }

    /* ---- Header ---- */
    .header {
        background: white;
        padding: 22px 24px;
        border-radius: 12px;
        margin-bottom: 18px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 24px rgba(15,23,42,0.06);
    }

    .header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .header .subtitle {
        margin-top: 6px;
        font-size: 14px;
        color: #475569;
    }

    /* ---- Buttons ---- */
    .stButton>button {
        background: #0f172a;
        color: white;
        border: 1px solid #0f172a;
        padding: 10px 18px;
        font-weight: 600;
        border-radius: 10px;
        transition: all 0.15s ease;
    }

    .stButton>button:hover {
        background: #020617;
        border-color: #020617;
        transform: translateY(-1px);
    }

    /* ---- Subtle containers ---- */
    .subtle-box {
        background: white;
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }

    .small {
        font-size: 13px;
        color: #64748b;
    }

    /* ---- KPI cards ---- */
    .kpi-card {
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        font-weight: 600;
        box-shadow: 0 6px 18px rgba(15,23,42,0.06);
    }

    .kpi-approve {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }

    .kpi-reject {
        background: #fef2f2;
        color: #7f1d1d;
        border: 1px solid #fecaca;
    }

    .kpi-escalate {
        background: #fffbeb;
        color: #78350f;
        border: 1px solid #fde68a;
    }

    .kpi-total {
        background: white;
        color: #0f172a;
        border: 2px solid #0f172a;
    }
    </style>

    <div class="header">
        <h1>Warranty Fraud Detector</h1>
        <div class="subtitle">
            Upload claims, analyze risk, review decisions, and export results.
        </div>
    </div>
    
    <style>
    button {
        color: #000000 !important;
        background-color: #f0f2f6 !important;
        border: 1px solid #ccc !important;
    }

    button:hover {
        background-color: #e0e2e6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.write("")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("## Upload claims CSV")
    uploaded_file = st.file_uploader("Choose a CSV file with warranty claims", type=["csv"])
    st.markdown("<div class='small'>Expected: one claim per row. The app will add policy_check, fraud_score, evidence, and decision columns.</div>", unsafe_allow_html=True)

with col2:
    st.markdown("## Actions")
    # Generate button (styled via global CSS above)
    generate_button = st.button("Generate Results", key="generate", use_container_width=True)

results_df = None
uploaded_df = None

# restore previous results (so widgets that cause reruns keep showing the data)
if 'results_df' in st.session_state:
    results_df = st.session_state['results_df']

if uploaded_file is not None:
    try:
        uploaded_df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")

    if uploaded_df is not None:
        st.markdown("### Preview uploaded data")
        st.dataframe(uploaded_df.head(10))

        # only run when user presses generate
        if generate_button:
            # progress UI
            placeholder = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_cb(current, total):
                pct = int(current / total * 100)
                progress_bar.progress(pct)
                status_text.info(f"Processing {current}/{total}")

            with st.spinner("Analyzing claims — this may take a few moments..."):
                results_df = process_claims(uploaded_df, progress_callback=progress_cb)

            # persist results so subsequent widget interactions (selectbox, expanders) survive reruns
            st.session_state['results_df'] = results_df

            progress_bar.progress(100)
            status_text.success("Processing complete")

        else:
            st.info("Upload a file and press 'Generate Results' to start processing.")

else:
    st.info("Please upload a CSV file to get started.")

# If we have results from a previous run (stored in session_state), render them here so
# widget interactions (like selecting a row) don't cause the app to fall back to the upload prompt.
if results_df is not None:
    # show summary KPIs (styled cards)
    st.markdown("## Results summary")
    if not results_df.empty:
        total = len(results_df)
        approves = int((results_df['decision'] == 'Approve claim').sum())
        rejects = int((results_df['decision'] == 'Reject claim').sum())
        escalates = int((results_df['decision'] == 'Escalate to HITL').sum())

        k1, k2, k3, k4 = st.columns([1,1,1,2])
        k1.markdown(f"<div class='kpi-card kpi-total'><strong>Total</strong><div style='font-size:28px'>{total}</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='kpi-card kpi-approve'><strong>Approved</strong><div style='font-size:28px'>{approves}</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='kpi-card kpi-reject'><strong>Rejected</strong><div style='font-size:28px'>{rejects}</div></div>", unsafe_allow_html=True)
        k4.markdown(f"<div class='kpi-card kpi-escalate'><strong>Escalated</strong><div style='font-size:28px'>{escalates}</div><div class='small'>Claims flagged for manual review</div></div>", unsafe_allow_html=True)

    # styled results table
    st.markdown("### Detailed Results")

    def style_decision(val):
        if val == 'Approve claim':
            return 'background-color: #d1fae5; color: #065f46'
        if val == 'Reject claim':
            return 'background-color: #fee2e2; color: #7f1d1d'
        if val == 'Escalate to HITL':
            return 'background-color: #fff7ed; color: #92400e'
        return ''

    styled = results_df.style.applymap(style_decision, subset=['decision'])
    st.dataframe(styled, use_container_width=True)

    # enable download with actual data
    csv_bytes = results_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", data=csv_bytes, file_name="processed_claims.csv", mime="text/csv")

    # Agent conversation trace viewer
    st.markdown("---")
    st.markdown("### Agent conversation trace")
    sel_idx = st.selectbox(
        "Select a claim to inspect the agent conversation",
        options=list(range(len(results_df))),
        format_func=lambda i: f"Row {i} - {results_df.index[i]}",
    )

    trace = results_df.iloc[sel_idx].get('agent_trace', [])

    if not trace:
        st.info("No agent trace available for this claim.")
    else:
        for step in trace:
            agent = step.get('agent')
            prompt = step.get('prompt', '')
            response = step.get('response', '')
            with st.expander(f"{agent}"):
                st.markdown("**Prompt**")
                st.code(prompt, language='')
                st.markdown("**Response**")
                st.code(response, language='')