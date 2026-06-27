import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os

# ── Connection ────────────────────────────────────────────────────────────────
# Replace 'yourpassword' with the password you set during PostgreSQL install
DB_URL = "postgresql://postgres:ocean7_Priest@localhost:5432/blood_donation_analytics"
engine = create_engine(DB_URL)

RAW = os.path.expanduser("~/Desktop/blood-donation-analytics/data/raw")

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_csv(name):
    return pd.read_csv(f"{RAW}/{name}.csv")

def to_sql(df, table, if_exists="append"):
    """Load a DataFrame into PostgreSQL. append = add rows, replace = wipe first."""
    df.to_sql(table, engine, if_exists=if_exists, index=False)
    print(f"  → Loaded {len(df):,} rows into {table}")


# ── STEP 1: dim_time ─────────────────────────────────────────────────────────
# We generate this from scratch — one row per day 2022-01-01 to 2024-12-31.
# No CSV for this one; it's purely derived.

print("Loading dim_time...")

# Kenyan public holidays (same logic as data generation)
HOLIDAYS = {
    (1, 1):   "New Year's Day",
    (4, 18):  "Good Friday",
    (4, 21):  "Easter Monday",
    (5, 1):   "Labour Day",
    (6, 1):   "Madaraka Day",
    (10, 10): "Huduma Day",
    (10, 20): "Mashujaa Day",
    (12, 12): "Jamhuri Day",
    (12, 25): "Christmas Day",
    (12, 26): "Boxing Day",
}

def get_season(month):
    # Kenya has two rainy seasons and two dry seasons
    if month in [12, 1, 2]:
        return "Dry"
    elif month in [3, 4, 5]:
        return "Long Rains"
    elif month in [6, 7, 8, 9]:
        return "Dry"
    else:
        return "Short Rains"

dates = pd.date_range("2022-01-01", "2024-12-31", freq="D")
time_rows = []
for d in dates:
    key = (d.month, d.day)
    is_holiday = key in HOLIDAYS
    time_rows.append({
        "full_date":         d.date(),
        "day_of_week":       d.isoweekday(),   # 1=Mon … 7=Sun (ISO)
        "day_name":          d.strftime("%A"),
        "week_of_year":      d.isocalendar()[1],
        "month_num":         d.month,
        "month_name":        d.strftime("%B"),
        "quarter":           d.quarter,
        "year":              d.year,
        "season":            get_season(d.month),
        "is_public_holiday": is_holiday,
        "holiday_name":      HOLIDAYS.get(key, None),
    })

dim_time = pd.DataFrame(time_rows)
to_sql(dim_time, "dim_time")

# Read back with generated time_key so we can use it in fact tables
time_keys = pd.read_sql("SELECT time_key, full_date FROM dim_time", engine)
time_keys["full_date"] = pd.to_datetime(time_keys["full_date"]).dt.date


# ── STEP 2: dim_counties ─────────────────────────────────────────────────────
print("Loading dim_counties...")

counties_raw = load_csv("counties")
dim_counties = counties_raw.rename(columns={"county_id": "_raw_id"})
# We only need the columns matching our schema
dim_counties = dim_counties[["county_name", "region", "population", "urban_rural"]]
to_sql(dim_counties, "dim_counties")

county_keys = pd.read_sql("SELECT county_key, county_name FROM dim_counties", engine)


# ── STEP 3: dim_hospitals ────────────────────────────────────────────────────
print("Loading dim_hospitals...")

hospitals_raw = load_csv("hospitals")
dim_hospitals = hospitals_raw[[
    "hospital_id", "hospital_name", "county", "region", "facility_level"
]].rename(columns={"county": "county_name"})
to_sql(dim_hospitals, "dim_hospitals")

hospital_keys = pd.read_sql(
    "SELECT hospital_key, hospital_id FROM dim_hospitals", engine
)


# ── STEP 4: dim_donors ───────────────────────────────────────────────────────
# Transform: bin raw age into age_group, extract registration year
print("Loading dim_donors...")

donors_raw = load_csv("donors")

def age_group(age):
    if age <= 25:   return "18-25"
    elif age <= 35: return "26-35"
    elif age <= 45: return "36-45"
    else:           return "46-60"

dim_donors = pd.DataFrame({
    "donor_id":          donors_raw["donor_id"],
    "age_group":         donors_raw["age"].apply(age_group),
    "gender":            donors_raw["gender"],
    "blood_type":        donors_raw["blood_type"],
    "county_name":       donors_raw["county"],
    "registration_year": pd.to_datetime(donors_raw["registration_date"]).dt.year,
})
to_sql(dim_donors, "dim_donors")

donor_keys = pd.read_sql("SELECT donor_key, donor_id FROM dim_donors", engine)


# ── STEP 5: dim_blood_types ──────────────────────────────────────────────────
print("Loading dim_blood_types...")

BLOOD_TYPE_META = {
    "O+":  ("Common",   False, False),
    "A+":  ("Common",   False, False),
    "B+":  ("Common",   False, False),
    "AB+": ("Uncommon", False, True),
    "O-":  ("Rare",     True,  False),
    "A-":  ("Rare",     False, False),
    "B-":  ("Rare",     False, False),
    "AB-": ("Rare",     False, False),
}

dim_blood_types = pd.DataFrame([
    {
        "blood_type":             bt,
        "rarity_category":        meta[0],
        "is_universal_donor":     meta[1],
        "is_universal_recipient": meta[2],
    }
    for bt, meta in BLOOD_TYPE_META.items()
])
to_sql(dim_blood_types, "dim_blood_types")

blood_type_keys = pd.read_sql(
    "SELECT blood_type_key, blood_type FROM dim_blood_types", engine
)


# ── STEP 6: fact_donations ───────────────────────────────────────────────────
# This is where surrogate key lookups happen.
# We merge raw donations with each dimension's key table to swap IDs.
print("Loading fact_donations...")

donations_raw = load_csv("donations")
donations_raw["date"] = pd.to_datetime(donations_raw["date"]).dt.date

fact_donations = donations_raw.merge(
    donor_keys, on="donor_id", how="left"
).merge(
    hospital_keys, on="hospital_id", how="left"
).merge(
    time_keys, left_on="date", right_on="full_date", how="left"
).merge(
    blood_type_keys, on="blood_type", how="left"
)

fact_donations = fact_donations[[
    "donation_id", "donor_key", "hospital_key",
    "time_key", "blood_type_key", "units_donated", "status"
]]

# Check for any unmatched keys before loading
nulls = fact_donations.isnull().sum()
if nulls.any():
    print("  WARNING: null keys found:", nulls[nulls > 0].to_dict())

to_sql(fact_donations, "fact_donations")


# ── STEP 7: fact_blood_requests ──────────────────────────────────────────────
print("Loading fact_blood_requests...")

requests_raw = load_csv("blood_requests")
requests_raw["date"] = pd.to_datetime(requests_raw["date"]).dt.date

fact_requests = requests_raw.merge(
    hospital_keys, on="hospital_id", how="left"
).merge(
    time_keys, left_on="date", right_on="full_date", how="left"
).merge(
    blood_type_keys, on="blood_type", how="left"
)

fact_requests = fact_requests[[
    "request_id", "hospital_key", "time_key", "blood_type_key",
    "units_requested", "units_fulfilled", "urgency_level", "fulfillment_rate"
]]

nulls = fact_requests.isnull().sum()
if nulls.any():
    print("  WARNING: null keys found:", nulls[nulls > 0].to_dict())

to_sql(fact_requests, "fact_blood_requests")


# ── Done ──────────────────────────────────────────────────────────────────────
print("\nETL complete. Verifying row counts...")

with engine.connect() as conn:
    for table in [
        "dim_time", "dim_counties", "dim_hospitals",
        "dim_donors", "dim_blood_types",
        "fact_donations", "fact_blood_requests"
    ]:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table}: {count:,} rows")