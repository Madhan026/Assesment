"""
generate_sample_data.py
------------------------
One-off script used to generate data/funnel_events_sample.csv.
Not part of the Streamlit app itself — kept for transparency/reproducibility.

Simulates a realistic product funnel:
    Visit -> Signup -> Add_to_Cart -> Checkout -> Purchase

Includes intentional data-quality issues so the dashboard's
Data Quality Report / Duplicate Handling / Skipped User Detection
features have something real to detect:
    - duplicate event rows
    - users who skip stages (drop off) at random points
    - a couple of malformed/missing values
"""

import random
import uuid
from datetime import datetime, timedelta
import csv

random.seed(42)

STAGES = ["Visit", "Signup", "Add_to_Cart", "Checkout", "Purchase"]
SEGMENTS = ["Organic", "Paid_Ads", "Referral", "Email"]
DEVICES = ["Desktop", "Mobile", "Tablet"]

# Conversion probability from one stage to the next (drop-off baked in)
STAGE_CONVERSION = {
    "Visit": 1.00,        # everyone visits
    "Signup": 0.55,       # 55% of visitors sign up
    "Add_to_Cart": 0.60,  # 60% of signups add to cart
    "Checkout": 0.45,     # 45% of cart users check out  <- biggest drop-off
    "Purchase": 0.70,     # 70% of checkouts purchase
}

N_USERS = 2500
start_date = datetime(2025, 1, 1)

rows = []
for i in range(N_USERS):
    user_id = f"U{i:05d}"
    segment = random.choice(SEGMENTS)
    device = random.choices(DEVICES, weights=[0.45, 0.45, 0.10])[0]
    session_id = str(uuid.uuid4())[:8]

    event_time = start_date + timedelta(
        days=random.randint(0, 89),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    reached_stage = True
    for stage in STAGES:
        if not reached_stage:
            break

        # Decide if the user reaches this stage
        prob = STAGE_CONVERSION[stage]
        if random.random() > prob:
            reached_stage = False
            continue

        # time increases as user moves down the funnel
        event_time = event_time + timedelta(minutes=random.randint(2, 4000))

        rows.append({
            "user_id": user_id,
            "event_name": stage,
            "timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "segment": segment,
            "device": device,
            "session_id": session_id,
        })

# --- Inject duplicate rows (exact copies) ---
dupe_sample = random.sample(rows, k=int(len(rows) * 0.03))
rows.extend(dupe_sample)

# --- Inject a few malformed rows (missing timestamp / segment) ---
for _ in range(15):
    r = random.choice(rows).copy()
    if random.random() < 0.5:
        r["timestamp"] = ""
    else:
        r["segment"] = ""
    rows.append(r)

random.shuffle(rows)

with open("data/funnel_events_sample.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["user_id", "event_name", "timestamp", "segment", "device", "session_id"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> data/funnel_events_sample.csv")
