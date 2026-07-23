# 📊 Funnel Dashboard

A professional, responsive **Streamlit + Plotly** dashboard for analyzing user
conversion funnels from raw event-level data — KPI tracking, drop-off
detection, segment comparison, data quality auditing, and more, all in one
interactive app.

---

## Features

- **KPI Cards** — total users entered, total converted, overall conversion rate, biggest drop-off stage, duplicate rows removed
- **Funnel Chart** — interactive Plotly funnel visualization of users per stage
- **Stage-wise Conversion Table** — per-stage user counts, % of start, % of previous stage, drop-off counts
- **Biggest Drop-off Detection** — automatically identifies and highlights the stage with the largest user loss
- **Drop-off Chart** — bar chart of drop-off % at each funnel transition
- **Pie Chart** — converted vs. dropped-off users at a glance
- **Time-to-Convert Analysis** — histogram + median/average/fastest time from first touch to final conversion
- **Segment Comparison** — conversion rate by segment (e.g. channel/campaign), table + bar chart
- **Data Quality Report** — raw vs. clean row counts, duplicates removed, invalid rows removed
- **Duplicate Handling** — automatic detection and removal of exact duplicate event rows
- **Skipped-User Detection** — flags users who reached a later funnel stage without a logged event at an earlier stage (tracking gaps)
- **Recommendation Section** — auto-generated, data-driven suggestions based on the current view
- **CSV Download** — export the stage-wise summary and the cleaned/filtered event data
- **Filters** — date range, segment, device, and adjustable funnel stage order, all in the sidebar
- **Responsive, professional UI** — custom CSS theme (`assets/style.css`) for a polished look on desktop and mobile

---

## Project Structure

```
Funnel_Dashboard/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
├── generate_sample_data.py     # Script used to generate the bundled sample dataset
├── assets/
│   └── style.css                # Custom dashboard styling
└── data/
    └── funnel_events_sample.csv # Sample funnel event dataset
```

---

## Dataset Schema

The app expects a CSV of **event-level** funnel data with these columns:

| Column        | Required | Description                                              |
|---------------|----------|------------------------------------------------------------|
| `user_id`     | ✅        | Unique identifier for the user                              |
| `event_name`  | ✅        | The funnel stage the event represents (e.g. `Visit`, `Signup`, `Checkout`, `Purchase`) |
| `timestamp`   | ✅        | Date/time the event occurred (any pandas-parsable format) |
| `segment`     | Optional | Acquisition/marketing segment (e.g. `Organic`, `Paid_Ads`) |
| `device`      | Optional | Device type (e.g. `Desktop`, `Mobile`, `Tablet`)            |
| `session_id`  | Optional | Session identifier                                          |

> The bundled sample dataset (`data/funnel_events_sample.csv`) was
> synthetically generated (`generate_sample_data.py`) to simulate a realistic
> 5-stage funnel — **Visit → Signup → Add_to_Cart → Checkout → Purchase** —
> and intentionally includes duplicate rows, missing values, and skipped
> stages so every feature of the dashboard (data quality report, duplicate
> handling, skipped-user detection) has real issues to surface.

To use your own data, either replace `data/funnel_events_sample.csv` or
upload a CSV directly from the sidebar in the running app.

---

## Getting Started

### 1. Clone / download the project

```bash
cd Funnel_Dashboard
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## Using Your Own Data

1. Launch the app.
2. Use the **"Upload funnel_events CSV"** control in the sidebar.
3. Ensure your CSV has at least the required columns (`user_id`, `event_name`, `timestamp`).
4. Optionally include `segment` and `device` columns to unlock segment comparison and device filtering.
5. Adjust the inferred funnel stage order in the sidebar if needed — stages are auto-ordered by median timestamp but can be manually reordered.

---

## How the Analysis Works

- **Duplicate handling**: exact duplicate rows (identical across all columns) are dropped before analysis — these are almost always re-fired tracking events rather than genuine repeat actions.
- **Funnel counts**: a user "reaches" a stage if they have at least one event with that `event_name`. Counts are unique users per stage, not raw event counts.
- **Drop-off %**: computed stage-over-stage as `1 - (users at stage / users at previous stage)`.
- **Skipped-user detection**: a user is flagged if they reached a later stage without ever having an event at an earlier stage in the inferred funnel order — a strong signal of tracking/instrumentation gaps.
- **Time-to-convert**: computed only for users who reached both the first and last stage, as the time delta between their earliest event at the first stage and earliest event at the final stage.

---

## Tech Stack

- [Streamlit](https://streamlit.io/) — app framework
- [Plotly](https://plotly.com/python/) — interactive charts
- [Pandas](https://pandas.pydata.org/) — data processing

---

## License

This project is provided as-is for educational and internal analytics use.
