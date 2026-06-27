import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os

# ── Setup ────────────────────────────────────────────────────────────────────
fake = Faker()
np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.expanduser("~/Desktop/blood-donation-analytics/data/raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

START_DATE = datetime(2022, 1, 1)
END_DATE   = datetime(2024, 12, 31)

# ── Reference data ───────────────────────────────────────────────────────────
# 47 Kenyan counties with region and urban weight
# Urban weight controls how many donations/requests a county attracts
COUNTIES = [
    ("Nairobi",       "Nairobi",       1.00),
    ("Mombasa",       "Coast",         0.80),
    ("Kisumu",        "Nyanza",        0.70),
    ("Nakuru",        "Rift Valley",   0.65),
    ("Eldoret",       "Rift Valley",   0.60),
    ("Kiambu",        "Central",       0.60),
    ("Machakos",      "Eastern",       0.50),
    ("Meru",          "Eastern",       0.50),
    ("Nyeri",         "Central",       0.45),
    ("Kakamega",      "Western",       0.45),
    ("Kisii",         "Nyanza",        0.45),
    ("Kilifi",        "Coast",         0.40),
    ("Murang'a",      "Central",       0.40),
    ("Embu",          "Eastern",       0.40),
    ("Bungoma",       "Western",       0.40),
    ("Siaya",         "Nyanza",        0.35),
    ("Vihiga",        "Western",       0.35),
    ("Migori",        "Nyanza",        0.35),
    ("Bomet",         "Rift Valley",   0.35),
    ("Kericho",       "Rift Valley",   0.35),
    ("Nandi",         "Rift Valley",   0.35),
    ("Trans Nzoia",   "Rift Valley",   0.35),
    ("Uasin Gishu",   "Rift Valley",   0.35),
    ("Laikipia",      "Rift Valley",   0.30),
    ("Nyandarua",     "Central",       0.30),
    ("Kirinyaga",     "Central",       0.30),
    ("Tharaka-Nithi", "Eastern",       0.25),
    ("Kitui",         "Eastern",       0.25),
    ("Makueni",       "Eastern",       0.25),
    ("Kajiado",       "Rift Valley",   0.25),
    ("Narok",         "Rift Valley",   0.25),
    ("Baringo",       "Rift Valley",   0.25),
    ("West Pokot",    "Rift Valley",   0.20),
    ("Samburu",       "Rift Valley",   0.15),
    ("Taita-Taveta",  "Coast",         0.20),
    ("Kwale",         "Coast",         0.20),
    ("Tana River",    "Coast",         0.15),
    ("Lamu",          "Coast",         0.15),
    ("Garissa",       "North Eastern", 0.20),
    ("Wajir",         "North Eastern", 0.15),
    ("Mandera",       "North Eastern", 0.15),
    ("Marsabit",      "Northern",      0.15),
    ("Isiolo",        "Northern",      0.20),
    ("Turkana",       "Northern",      0.15),
    ("Pokot",         "Rift Valley",   0.15),
    ("Elgeyo-M.",     "Rift Valley",   0.25),
    ("Homa Bay",      "Nyanza",        0.35),
]

COUNTY_NAMES   = [c[0] for c in COUNTIES]
COUNTY_REGIONS = {c[0]: c[1] for c in COUNTIES}
COUNTY_WEIGHTS = [c[2] for c in COUNTIES]

# Kenyan blood type prevalence (these are real approximate figures)
BLOOD_TYPES   = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
BLOOD_WEIGHTS = [0.40, 0.27, 0.20, 0.06, 0.03, 0.02, 0.015, 0.005]

# Kenyan public holidays (approximate dates repeated across years)
def get_holidays(year):
    return [
        datetime(year, 1, 1),   # New Year
        datetime(year, 4, 18),  # Good Friday (approx)
        datetime(year, 4, 21),  # Easter Monday (approx)
        datetime(year, 5, 1),   # Labour Day
        datetime(year, 6, 1),   # Madaraka Day
        datetime(year, 10, 10), # Huduma Day
        datetime(year, 10, 20), # Mashujaa Day
        datetime(year, 12, 12), # Jamhuri Day
        datetime(year, 12, 25), # Christmas
        datetime(year, 12, 26), # Boxing Day
    ]

ALL_HOLIDAYS = set()
for yr in [2022, 2023, 2024]:
    for h in get_holidays(yr):
        ALL_HOLIDAYS.add(h.date())

def random_date(start, end):
    """Return a random datetime between start and end."""
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def donation_weight(date):
    """
    Return a multiplier for how likely a donation is on this date.
    Higher near holidays, higher March–August (trauma season).
    """
    w = 1.0
    if date.date() in ALL_HOLIDAYS:
        w *= 2.5   # Blood drives cluster around holidays
    if 3 <= date.month <= 8:
        w *= 1.3   # Trauma season
    return w


# ── Table 1: Counties ────────────────────────────────────────────────────────
# Simple reference table. Each county gets an ID, its region, and a rough
# population estimate, plus an urban/rural label.
# Manual logic: assign IDs sequentially, look up region from our dict,
# estimate population from publicly known figures.

COUNTY_POPULATIONS = {
    "Nairobi": 4397073, "Kiambu": 2417735, "Nakuru": 2162202,
    "Kakamega": 1867579, "Bungoma": 1670570, "Meru": 1545714,
    "Kilifi": 1453787, "Machakos": 1421932, "Kisii": 1266860,
    "Mombasa": 1208333, "Murang'a": 1056640, "Siaya": 993183,
    "Migori": 1116436, "Homa Bay": 1131950, "Kisumu": 1155574,
    "Nyeri": 759164, "Embu": 608599, "Kitui": 1136187,
    "Makueni": 987653, "Nandi": 885711, "Trans Nzoia": 990341,
    "Uasin Gishu": 1163186, "Eldoret": 1163186,
    "Kericho": 901777, "Bomet": 875689, "Vihiga": 590013,
    "Nyandarua": 638289, "Laikipia": 518560, "Kirinyaga": 610411,
    "Kajiado": 1117840, "Narok": 1157873, "Baringo": 666763,
    "Elgeyo-M.": 454480, "West Pokot": 621241, "Samburu": 310327,
    "Tharaka-Nithi": 393177, "Taita-Taveta": 340671, "Kwale": 866820,
    "Tana River": 315943, "Lamu": 143920, "Garissa": 841353,
    "Wajir": 781263, "Mandera": 1025756, "Marsabit": 459785,
    "Isiolo": 268002, "Turkana": 926976, "Pokot": 621241,
}

def generate_counties():
    rows = []
    for i, (name, region, weight) in enumerate(COUNTIES, start=1):
        pop = COUNTY_POPULATIONS.get(name, 400000)
        urban = "Urban" if weight >= 0.5 else "Rural"
        rows.append({
            "county_id":    i,
            "county_name":  name,
            "region":       region,
            "population":   pop,
            "urban_rural":  urban,
        })
    return pd.DataFrame(rows)


# ── Table 2: Hospitals ───────────────────────────────────────────────────────
# Manual logic: distribute hospitals across counties weighted by urbanness.
# Urban counties get more hospitals and higher-level facilities.
# Facility levels follow Kenya's actual tiering: Level 4 = county hospital,
# Level 5 = referral hospital, National = KNH/Moi Teaching etc.

HOSPITAL_NAMES = [
    "General Hospital", "County Referral Hospital", "Mission Hospital",
    "Medical Centre", "District Hospital", "Teaching & Referral Hospital",
    "Community Hospital", "Specialist Hospital",
]

def generate_hospitals(n=80):
    rows = []
    # Weight county selection by urban weight so Nairobi gets more hospitals
    county_weights_norm = np.array(COUNTY_WEIGHTS) / sum(COUNTY_WEIGHTS)

    for i in range(1, n + 1):
        county = np.random.choice(COUNTY_NAMES, p=county_weights_norm)
        weight = dict(zip(COUNTY_NAMES, COUNTY_WEIGHTS))[county]

        # Facility level depends on how urban the county is
        if weight >= 0.8:
            level = np.random.choice(
                ["Level 4", "Level 5", "National"],
                p=[0.3, 0.4, 0.3]
            )
        elif weight >= 0.5:
            level = np.random.choice(
                ["Level 4", "Level 5", "National"],
                p=[0.5, 0.4, 0.1]
            )
        else:
            level = np.random.choice(
                ["Level 4", "Level 5"],
                p=[0.8, 0.2]
            )

        name = f"{county} {random.choice(HOSPITAL_NAMES)}"
        rows.append({
            "hospital_id":    i,
            "hospital_name":  name,
            "county":         county,
            "region":         COUNTY_REGIONS[county],
            "facility_level": level,
        })
    return pd.DataFrame(rows)


# ── Table 3: Donors ──────────────────────────────────────────────────────────
# Manual logic: most donors are 18–45 (that's the eligible donation range).
# Gender is roughly 50/50. Blood type follows Kenyan prevalence weights.
# County follows urban weights (more donors registered in urban areas).
# last_donation_date must be after registration_date.

def generate_donors(n=5000):
    rows = []
    county_weights_norm = np.array(COUNTY_WEIGHTS) / sum(COUNTY_WEIGHTS)

    for i in range(1, n + 1):
        reg_date  = random_date(START_DATE, END_DATE - timedelta(days=90))
        # Last donation is sometime after registration (or None for new donors)
        if random.random() < 0.75:  # 75% have donated at least once
            last_don = random_date(reg_date, END_DATE)
        else:
            last_don = None

        rows.append({
            "donor_id":           i,
            "name":               fake.name(),
            "age":                random.randint(18, 60),
            "gender":             random.choice(["Male", "Female"]),
            "blood_type":         random.choices(BLOOD_TYPES, weights=BLOOD_WEIGHTS)[0],
            "county":             np.random.choice(COUNTY_NAMES, p=county_weights_norm),
            "registration_date":  reg_date.date(),
            "last_donation_date": last_don.date() if last_don else None,
        })
    return pd.DataFrame(rows)


# ── Table 4: Donations ───────────────────────────────────────────────────────
# Manual logic: each donation links a donor to a hospital on a date.
# Not every donor donates — repeat donors donate multiple times.
# Date selection is weighted: higher probability near holidays and in
# March–August trauma season.
# Units donated is almost always 1 (a standard unit = 450ml).
# Status: most are "Completed", a small % are "Deferred" (donor turned away).

def generate_donations(donors_df, hospitals_df, n=15000):
    rows = []
    donor_ids   = donors_df["donor_id"].tolist()
    hospital_ids = hospitals_df["hospital_id"].tolist()

    # Build a pool of candidate dates, weighted by donation_weight
    all_days = [START_DATE + timedelta(days=d)
                for d in range((END_DATE - START_DATE).days + 1)]
    day_weights = [donation_weight(d) for d in all_days]
    day_weights_norm = np.array(day_weights) / sum(day_weights)

    for i in range(1, n + 1):
        date = np.random.choice(all_days, p=day_weights_norm)
        rows.append({
            "donation_id":  i,
            "donor_id":     random.choice(donor_ids),
            "hospital_id":  random.choice(hospital_ids),
            "date":         date.date(),
            "blood_type":   random.choices(BLOOD_TYPES, weights=BLOOD_WEIGHTS)[0],
            "units_donated": 1,
            "status":       random.choices(
                                ["Completed", "Deferred"],
                                weights=[0.92, 0.08]
                            )[0],
        })
    return pd.DataFrame(rows)


# ── Table 5: Blood Requests ──────────────────────────────────────────────────
# Manual logic: hospitals request blood based on patient need.
# Urban/high-level hospitals have more requests.
# Urgency is either Routine, Urgent, or Emergency.
# Units fulfilled <= units requested (some requests only partially filled).
# Shortage happens more for rare blood types (O-, AB-, B-).

RARE_TYPES = {"O-", "A-", "B-", "AB-"}

def generate_blood_requests(hospitals_df, n=12000):
    rows = []
    hospital_ids = hospitals_df["hospital_id"].tolist()

    all_days = [START_DATE + timedelta(days=d)
                for d in range((END_DATE - START_DATE).days + 1)]

    for i in range(1, n + 1):
        blood_type    = random.choices(BLOOD_TYPES, weights=BLOOD_WEIGHTS)[0]
        units_requested = random.randint(1, 10)
        urgency       = random.choices(
                            ["Routine", "Urgent", "Emergency"],
                            weights=[0.5, 0.35, 0.15]
                        )[0]

        # Rare blood types are harder to fulfil
        if blood_type in RARE_TYPES:
            fulfillment_rate = random.uniform(0.2, 0.7)
        elif urgency == "Emergency":
            fulfillment_rate = random.uniform(0.5, 1.0)
        else:
            fulfillment_rate = random.uniform(0.6, 1.0)

        units_fulfilled = round(units_requested * fulfillment_rate)

        rows.append({
            "request_id":       i,
            "hospital_id":      random.choice(hospital_ids),
            "blood_type":       blood_type,
            "units_requested":  units_requested,
            "units_fulfilled":  units_fulfilled,
            "date":             random.choice(all_days).date(),
            "urgency_level":    urgency,
            "fulfillment_rate": round(fulfillment_rate, 3),
        })
    return pd.DataFrame(rows)


# ── Run everything ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating counties...")
    counties  = generate_counties()
    counties.to_csv(f"{OUTPUT_DIR}/counties.csv", index=False)
    print(f"  → {len(counties)} counties")

    print("Generating hospitals...")
    hospitals = generate_hospitals(n=80)
    hospitals.to_csv(f"{OUTPUT_DIR}/hospitals.csv", index=False)
    print(f"  → {len(hospitals)} hospitals")

    print("Generating donors...")
    donors    = generate_donors(n=5000)
    donors.to_csv(f"{OUTPUT_DIR}/donors.csv", index=False)
    print(f"  → {len(donors)} donors")

    print("Generating donations...")
    donations = generate_donations(donors, hospitals, n=15000)
    donations.to_csv(f"{OUTPUT_DIR}/donations.csv", index=False)
    print(f"  → {len(donations)} donations")

    print("Generating blood requests...")
    requests  = generate_blood_requests(hospitals, n=12000)
    requests.to_csv(f"{OUTPUT_DIR}/blood_requests.csv", index=False)
    print(f"  → {len(requests)} blood requests")

    print("\nDone. Files saved to:", OUTPUT_DIR)