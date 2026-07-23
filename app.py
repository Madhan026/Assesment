"""
Funnel Dashboard
================
A production-quality Streamlit + Plotly dashboard for analyzing a
user conversion funnel from raw event-level data.

Run locally:
    streamlit run app.py

Expected input CSV columns:
    user_id      - unique identifier for a user
    event_name   - funnel stage the event represents (e.g. Visit, Signup, ...)
    timestamp    - datetime string for when the event occurred
    segment      - marketing / acquisition segment (optional but recommended)
    device       - device type (optional)
    session_id   - session identifier (optional)

The app is defensive about missing/optional columns and about common
data quality issues (duplicates, missing values, skipped funnel stages).
"""

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Page configuration
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Funnel Dashboard",
    page_icon="assets/favicon.png" if False else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css(path: str) -> None:
    """Inject a local CSS file into the Streamlit app."""
    try:
        with open(path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # App should still run even if the stylesheet is missing.
        pass


load_css("assets/style.css")

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
DEFAULT_DATA_PATH = "data/funnel_events_sample.csv"
REQUIRED_COLUMNS = ["user_id", "event_name", "timestamp"]
OPTIONAL_COLUMNS = ["segment", "device", "session_id"]
COLUMN_ALIASES = {
    "user": "user_id",
    "user id": "user_id",
    "userid": "user_id",
    "event": "event_name",
    "event name": "event_name",
    "event type": "event_name",
    "stage": "event_name",
    "action": "event_name",
    "time": "timestamp",
    "event time": "timestamp",
    "date": "timestamp",
}


# --------------------------------------------------------------------------
# Data loading & caching
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file_or_path) -> pd.DataFrame:
    """
    Load funnel event data from an uploaded file or a default path.
    Returns the RAW dataframe (before cleaning) so the Data Quality
    Report can inspect it faithfully.
    """
    df = pd.read_csv(file_or_path, encoding="utf-8-sig")
    normalized_columns = [" ".join(str(c).strip().lower().split()) for c in df.columns]
    renamed_columns = {}
    for original, normalized in zip(df.columns, normalized_columns):
        renamed_columns[original] = COLUMN_ALIASES.get(normalized, normalized.replace(" ", "_"))
    df = df.rename(columns=renamed_columns)
    return df


@st.cache_data(show_spinner=False)
def clean_data(df: pd.DataFrame):
    """
    Clean the raw dataframe and return:
        clean_df       - deduplicated, valid rows only
        n_duplicates    - number of exact duplicate rows removed
        n_missing_rows  - number of rows dropped due to missing required fields
    """
    raw_len = len(df)

    # --- Duplicate handling: exact duplicate rows are almost always
    # re-fired/re-logged events, not genuine repeat actions. ---
    deduped = df.drop_duplicates()
    n_duplicates = raw_len - len(deduped)

    # --- Drop rows missing required fields (can't analyze them safely) ---
    before_na = len(deduped)
    deduped = deduped.dropna(subset=[c for c in REQUIRED_COLUMNS if c in deduped.columns])
    for col in REQUIRED_COLUMNS:
        if col in deduped.columns:
            deduped = deduped[deduped[col].astype(str).str.strip() != ""]
    n_missing_rows = before_na - len(deduped)

    # --- Parse timestamp ---
    if "timestamp" in deduped.columns:
        deduped["timestamp"] = pd.to_datetime(deduped["timestamp"], errors="coerce")
        n_bad_timestamps = deduped["timestamp"].isna().sum()
        deduped = deduped.dropna(subset=["timestamp"])
        n_missing_rows += n_bad_timestamps

    # Normalize stage names (trim whitespace, consistent casing for grouping)
    deduped["event_name"] = deduped["event_name"].astype(str).str.strip()

    return deduped.reset_index(drop=True), n_duplicates, n_missing_rows


def infer_stage_order(df: pd.DataFrame) -> list:
    """
    Infer a sensible funnel stage order.
    Uses the earliest median timestamp per stage as a proxy for its
    position in the funnel, which works even if stage names are custom.
    """
    stage_time = df.groupby("event_name")["timestamp"].median().sort_values()
    return list(stage_time.index)


# --------------------------------------------------------------------------
# Sidebar — data source & filters
# --------------------------------------------------------------------------
st.sidebar.title("📊 Funnel Dashboard")
st.sidebar.caption("Upload your own funnel event log or use the bundled sample data.")

uploaded_file = st.sidebar.file_uploader("Upload funnel_events CSV", type=["csv"])

if uploaded_file is not None:
    raw_df = load_data(uploaded_file)
    data_source_label = uploaded_file.name
else:
    raw_df = load_data(DEFAULT_DATA_PATH)
    data_source_label = "sample dataset (data/funnel_events_sample.csv)"

st.sidebar.success(f"Loaded: {data_source_label}")

# Validate required columns exist before proceeding
missing_required = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
if missing_required:
    detected_columns = ", ".join(raw_df.columns) or "none"
    st.error(
        f"The uploaded file is missing required column(s): {', '.join(missing_required)}. "
        f"Required columns are: {', '.join(REQUIRED_COLUMNS)}. "
        f"Detected columns: {detected_columns}."
    )
    st.stop()

clean_df, n_duplicates, n_missing_rows = clean_data(raw_df)
stage_order_full = infer_stage_order(clean_df)

# --- Sidebar filters ---
st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

# Date range filter
min_date = clean_df["timestamp"].min().date()
max_date = clean_df["timestamp"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Segment filter (only if column exists)
segment_filter = None
if "segment" in clean_df.columns:
    segments_available = sorted(clean_df["segment"].dropna().unique().tolist())
    segment_filter = st.sidebar.multiselect(
        "Segment", options=segments_available, default=segments_available
    )

# Device filter (only if column exists)
device_filter = None
if "device" in clean_df.columns:
    devices_available = sorted(clean_df["device"].dropna().unique().tolist())
    device_filter = st.sidebar.multiselect(
        "Device", options=devices_available, default=devices_available
    )

# Stage order override
st.sidebar.markdown("---")
st.sidebar.subheader("Funnel Stage Order")
stage_order = st.sidebar.multiselect(
    "Confirm/reorder funnel stages (in order)",
    options=stage_order_full,
    default=stage_order_full,
    help="Stages are auto-ordered by median timestamp. Adjust if needed.",
)
if not stage_order:
    stage_order = stage_order_full

# --------------------------------------------------------------------------
# Apply filters
# --------------------------------------------------------------------------
mask = (clean_df["timestamp"].dt.date >= start_date) & (clean_df["timestamp"].dt.date <= end_date)
if segment_filter is not None:
    mask &= clean_df["segment"].isin(segment_filter)
if device_filter is not None:
    mask &= clean_df["device"].isin(device_filter)

df = clean_df[mask].copy()
df = df[df["event_name"].isin(stage_order)]

if df.empty:
    st.warning("No data matches the selected filters. Try widening your date range or filters.")
    st.stop()

# --------------------------------------------------------------------------
# Core funnel computation
# --------------------------------------------------------------------------
def compute_funnel_counts(data: pd.DataFrame, stages: list) -> pd.DataFrame:
    """
    Compute unique-user counts per stage, assuming a user only counts
    toward a stage if they reached it (any event with that stage name).
    """
    counts = []
    for stage in stages:
        n_users = data.loc[data["event_name"] == stage, "user_id"].nunique()
        counts.append({"stage": stage, "users": n_users})
    funnel_df = pd.DataFrame(counts)
    funnel_df["conversion_from_start_%"] = (
        funnel_df["users"] / funnel_df["users"].iloc[0] * 100 if len(funnel_df) else 0
    ).round(1)
    funnel_df["conversion_from_prev_%"] = (
        funnel_df["users"].pct_change().fillna(0) * 100 + 100
    ).round(1)
    funnel_df.loc[0, "conversion_from_prev_%"] = 100.0
    funnel_df["drop_off_users"] = funnel_df["users"].shift(1) - funnel_df["users"]
    funnel_df.loc[0, "drop_off_users"] = 0
    funnel_df["drop_off_%"] = (100 - funnel_df["conversion_from_prev_%"]).round(1)
    funnel_df.loc[0, "drop_off_%"] = 0.0
    return funnel_df


funnel_df = compute_funnel_counts(df, stage_order)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.title("📊 Funnel Analytics Dashboard")
st.caption(
    f"Analyzing **{df['user_id'].nunique():,}** unique users across "
    f"**{len(stage_order)}** funnel stages "
    f"({start_date} → {end_date})."
)

# --------------------------------------------------------------------------
# KPI Cards
# --------------------------------------------------------------------------
total_entered = funnel_df["users"].iloc[0] if len(funnel_df) else 0
total_converted = funnel_df["users"].iloc[-1] if len(funnel_df) else 0
overall_conversion = round((total_converted / total_entered * 100), 1) if total_entered else 0.0

if len(funnel_df) > 1:
    biggest_drop_idx = funnel_df["drop_off_%"].iloc[1:].idxmax()
    biggest_drop_stage = funnel_df.loc[biggest_drop_idx, "stage"]
    biggest_drop_pct = funnel_df.loc[biggest_drop_idx, "drop_off_%"]
    biggest_drop_users = int(funnel_df.loc[biggest_drop_idx, "drop_off_users"])
    prev_stage_name = funnel_df.loc[biggest_drop_idx - 1, "stage"]
else:
    biggest_drop_stage, biggest_drop_pct, biggest_drop_users, prev_stage_name = "N/A", 0, 0, "N/A"

kpi_cols = st.columns(5)
kpi_cols[0].metric("Total Users Entered", f"{total_entered:,}")
kpi_cols[1].metric("Total Converted", f"{total_converted:,}")
kpi_cols[2].metric("Overall Conversion", f"{overall_conversion}%")
kpi_cols[3].metric(
    "Biggest Drop-off",
    f"{prev_stage_name} → {biggest_drop_stage}",
    delta=f"-{biggest_drop_pct}%",
    delta_color="inverse",
)
kpi_cols[4].metric("Duplicate Rows Removed", f"{n_duplicates:,}")

st.markdown("---")

# --------------------------------------------------------------------------
# Funnel Chart + Pie Chart (side by side)
# --------------------------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Conversion Funnel")
    fig_funnel = go.Figure(
        go.Funnel(
            y=funnel_df["stage"],
            x=funnel_df["users"],
            textposition="inside",
            textinfo="value+percent initial",
            marker={"color": px.colors.sequential.Blues_r[: len(funnel_df)]},
            connector={"line": {"color": "#94A3B8", "dash": "dot", "width": 2}},
        )
    )
    fig_funnel.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=420,
        font=dict(family="Inter, sans-serif", size=13),
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

with col2:
    st.subheader("Users Reaching Final Stage")
    remaining = total_converted
    dropped = total_entered - total_converted
    fig_pie = px.pie(
        names=["Converted", "Dropped Off"],
        values=[remaining, dropped],
        color_discrete_sequence=["#2563EB", "#E2E8F0"],
        hole=0.55,
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=420,
        showlegend=False,
        font=dict(family="Inter, sans-serif", size=13),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --------------------------------------------------------------------------
# Stage-wise Conversion Table + Drop-off Chart
# --------------------------------------------------------------------------
col3, col4 = st.columns([1, 1])

with col3:
    st.subheader("Stage-wise Conversion")
    display_funnel = funnel_df.copy()
    display_funnel.columns = [
        "Stage", "Users", "% of Start", "% of Previous Stage",
        "Users Dropped", "Drop-off %",
    ]
    st.dataframe(display_funnel, use_container_width=True, hide_index=True)

with col4:
    st.subheader("Drop-off by Stage")
    dropoff_plot_df = funnel_df.iloc[1:].copy()
    fig_drop = px.bar(
        dropoff_plot_df,
        x="stage",
        y="drop_off_%",
        text="drop_off_%",
        color="drop_off_%",
        color_continuous_scale="Reds",
    )
    fig_drop.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_drop.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        xaxis_title=None,
        yaxis_title="Drop-off %",
        coloraxis_showscale=False,
        font=dict(family="Inter, sans-serif", size=13),
    )
    st.plotly_chart(fig_drop, use_container_width=True)

# --------------------------------------------------------------------------
# Biggest Drop-off Callout
# --------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔻 Biggest Drop-off Detection")
if len(funnel_df) > 1:
    st.error(
        f"The largest drop-off occurs between **{prev_stage_name}** and **{biggest_drop_stage}**: "
        f"**{biggest_drop_users:,} users ({biggest_drop_pct}%)** did not proceed to the next stage. "
        f"This is the highest-leverage stage to investigate and optimize."
    )
else:
    st.info("Not enough stages to detect a drop-off.")

st.markdown("---")

# --------------------------------------------------------------------------
# Time-to-Convert Analysis
# --------------------------------------------------------------------------
st.subheader("⏱️ Time-to-Convert Analysis")


@st.cache_data(show_spinner=False)
def compute_time_to_convert(data: pd.DataFrame, stages: list) -> pd.DataFrame:
    """
    For each user, compute the elapsed time (in hours) between their
    first-stage event and their last-stage event reached, restricted
    to users who reached the final stage (full converters).
    """
    if len(stages) < 2:
        return pd.DataFrame()

    first_stage, last_stage = stages[0], stages[-1]
    first_times = (
        data[data["event_name"] == first_stage]
        .groupby("user_id")["timestamp"].min()
    )
    last_times = (
        data[data["event_name"] == last_stage]
        .groupby("user_id")["timestamp"].min()
    )
    merged = pd.concat([first_times, last_times], axis=1, keys=["start", "end"]).dropna()
    merged["hours_to_convert"] = (merged["end"] - merged["start"]).dt.total_seconds() / 3600
    merged = merged[merged["hours_to_convert"] >= 0]
    return merged.reset_index()


ttc_df = compute_time_to_convert(df, stage_order)

if not ttc_df.empty:
    ttc_col1, ttc_col2, ttc_col3 = st.columns(3)
    ttc_col1.metric("Median Time to Convert", f"{ttc_df['hours_to_convert'].median():.1f} hrs")
    ttc_col2.metric("Average Time to Convert", f"{ttc_df['hours_to_convert'].mean():.1f} hrs")
    ttc_col3.metric("Fastest Conversion", f"{ttc_df['hours_to_convert'].min():.2f} hrs")

    fig_ttc = px.histogram(
        ttc_df, x="hours_to_convert", nbins=30,
        color_discrete_sequence=["#2563EB"],
        labels={"hours_to_convert": "Hours to Convert (Start → Final Stage)"},
    )
    fig_ttc.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=350,
        yaxis_title="Number of Users",
        font=dict(family="Inter, sans-serif", size=13),
    )
    st.plotly_chart(fig_ttc, use_container_width=True)
else:
    st.info("Not enough converting users in the current filter selection to compute time-to-convert.")

st.markdown("---")

# --------------------------------------------------------------------------
# Segment Comparison
# --------------------------------------------------------------------------
st.subheader("👥 Segment Comparison")

if "segment" in df.columns and df["segment"].nunique() > 1:
    seg_rows = []
    for seg in sorted(df["segment"].dropna().unique()):
        seg_data = df[df["segment"] == seg]
        seg_funnel = compute_funnel_counts(seg_data, stage_order)
        if len(seg_funnel):
            seg_rows.append({
                "segment": seg,
                "entered": seg_funnel["users"].iloc[0],
                "converted": seg_funnel["users"].iloc[-1],
                "conversion_%": round(seg_funnel["users"].iloc[-1] / seg_funnel["users"].iloc[0] * 100, 1)
                if seg_funnel["users"].iloc[0] else 0,
            })
    seg_summary = pd.DataFrame(seg_rows).sort_values("conversion_%", ascending=False)

    seg_col1, seg_col2 = st.columns([1, 1])
    with seg_col1:
        st.dataframe(
            seg_summary.rename(columns={
                "segment": "Segment", "entered": "Entered",
                "converted": "Converted", "conversion_%": "Conversion %",
            }),
            use_container_width=True, hide_index=True,
        )
    with seg_col2:
        fig_seg = px.bar(
            seg_summary, x="segment", y="conversion_%",
            text="conversion_%", color="segment",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_seg.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_seg.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350, showlegend=False,
            xaxis_title=None, yaxis_title="Conversion %",
            font=dict(family="Inter, sans-serif", size=13),
        )
        st.plotly_chart(fig_seg, use_container_width=True)
else:
    st.info("No 'segment' column available (or only one segment present) — segment comparison skipped.")

st.markdown("---")

# --------------------------------------------------------------------------
# Data Quality Report
# --------------------------------------------------------------------------
st.subheader("🧪 Data Quality Report")

dq_col1, dq_col2, dq_col3, dq_col4 = st.columns(4)
dq_col1.metric("Raw Rows", f"{len(raw_df):,}")
dq_col2.metric("Duplicate Rows Removed", f"{n_duplicates:,}")
dq_col3.metric("Invalid / Missing Rows Removed", f"{n_missing_rows:,}")
dq_col4.metric("Clean Rows Used", f"{len(clean_df):,}")

with st.expander("View detailed data quality notes"):
    st.markdown(
        f"""
- **Raw dataset size:** {len(raw_df):,} rows
- **Exact duplicate rows removed:** {n_duplicates:,}
  (identical rows across all columns — typically re-fired tracking events)
- **Rows dropped for missing required fields** (`user_id`, `event_name`, or unparseable `timestamp`):
  {n_missing_rows:,}
- **Final clean dataset used for analysis:** {len(clean_df):,} rows,
  {clean_df['user_id'].nunique():,} unique users
        """
    )


# --------------------------------------------------------------------------
# Skipped User Detection
# --------------------------------------------------------------------------
st.subheader("⏭️ Skipped-Stage User Detection")


@st.cache_data(show_spinner=False)
def detect_skipped_users(data: pd.DataFrame, stages: list) -> pd.DataFrame:
    """
    A user is considered to have 'skipped' a stage if they reached a
    LATER stage in the funnel without any event at an EARLIER stage.
    e.g. reached 'Checkout' but never had a 'Signup' event.
    Returns a dataframe of user_id -> list of skipped stages.
    """
    user_stage_sets = data.groupby("user_id")["event_name"].apply(set)
    skipped_records = []
    for user_id, stages_reached in user_stage_sets.items():
        reached_indices = [i for i, s in enumerate(stages) if s in stages_reached]
        if not reached_indices:
            continue
        furthest = max(reached_indices)
        expected = set(stages[: furthest + 1])
        missing = expected - stages_reached
        if missing:
            skipped_records.append({
                "user_id": user_id,
                "furthest_stage": stages[furthest],
                "skipped_stages": ", ".join(sorted(missing, key=lambda s: stages.index(s))),
            })
    return pd.DataFrame(skipped_records)


skipped_df = detect_skipped_users(df, stage_order)

if not skipped_df.empty:
    st.warning(
        f"Detected **{len(skipped_df):,} users** who reached a later funnel stage "
        f"without a logged event at an earlier stage. This usually indicates "
        f"tracking gaps, direct entry links, or missing instrumentation."
    )
    st.dataframe(skipped_df, use_container_width=True, hide_index=True, height=250)
else:
    st.success("No skipped-stage users detected — funnel tracking looks sequentially consistent.")

st.markdown("---")

# --------------------------------------------------------------------------
# Recommendation Section
# --------------------------------------------------------------------------
st.subheader("💡 Recommendations")

recommendations = []

if len(funnel_df) > 1:
    recommendations.append(
        f"**Focus on {prev_stage_name} → {biggest_drop_stage}:** this stage loses "
        f"{biggest_drop_users:,} users ({biggest_drop_pct}%), the largest drop in the funnel. "
        f"Investigate UX friction, load times, or messaging clarity at this step."
    )

if overall_conversion < 20:
    recommendations.append(
        f"**Overall conversion is low ({overall_conversion}%).** Consider A/B testing "
        f"the entry point and simplifying the number of steps required to convert."
    )
elif overall_conversion >= 50:
    recommendations.append(
        f"**Overall conversion is strong ({overall_conversion}%).** Consider scaling "
        f"acquisition spend toward the channels driving this funnel."
    )

if not skipped_df.empty:
    recommendations.append(
        f"**{len(skipped_df):,} users show tracking gaps** (skipped stages). "
        f"Audit event instrumentation to ensure every funnel step fires reliably."
    )

if not ttc_df.empty and ttc_df["hours_to_convert"].median() > 72:
    recommendations.append(
        f"**Median time-to-convert is {ttc_df['hours_to_convert'].median():.0f} hours.** "
        f"Consider lifecycle nudges (email/push reminders) to shorten the decision window."
    )

if "segment" in df.columns and df["segment"].nunique() > 1 and not seg_summary.empty:
    best_seg = seg_summary.iloc[0]
    worst_seg = seg_summary.iloc[-1]
    if best_seg["segment"] != worst_seg["segment"]:
        recommendations.append(
            f"**'{best_seg['segment']}' converts best ({best_seg['conversion_%']}%)** while "
            f"**'{worst_seg['segment']}' lags ({worst_seg['conversion_%']}%).** "
            f"Review what makes the top segment succeed and apply learnings to the underperforming one."
        )

if n_duplicates > 0:
    recommendations.append(
        f"**{n_duplicates:,} duplicate events were found in raw data.** "
        f"Review the event-tracking pipeline for double-firing issues to keep metrics accurate."
    )

if not recommendations:
    recommendations.append("Funnel performance looks healthy — no critical issues detected in this view.")

for rec in recommendations:
    st.markdown(f"- {rec}")

st.markdown("---")

# --------------------------------------------------------------------------
# CSV Download
# --------------------------------------------------------------------------
st.subheader("⬇️ Export")

exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    csv_buffer = io.StringIO()
    funnel_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download Stage-wise Funnel Summary (CSV)",
        data=csv_buffer.getvalue(),
        file_name=f"funnel_summary_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp_col2:
    clean_csv_buffer = io.StringIO()
    df.to_csv(clean_csv_buffer, index=False)
    st.download_button(
        label="Download Cleaned & Filtered Event Data (CSV)",
        data=clean_csv_buffer.getvalue(),
        file_name=f"funnel_events_clean_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption("Built with Streamlit + Plotly · Funnel Dashboard")
