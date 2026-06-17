import pandas as pd
import glob
import os

# ---------------------------
# Settings
# ---------------------------
ldap_folder = "Data/r4.2/LDAP/"
file_access_path = "Data/r4.2/file.csv"
max_len_content_snippet = 800

# ---------------------------
# LDAP: alle Monatsdateien einlesen
# ---------------------------
ldap_files = glob.glob(os.path.join(ldap_folder, "**/*.csv"), recursive=True)
ldap = pd.concat([pd.read_csv(f, dtype=str) for f in ldap_files], ignore_index=True)
ldap = ldap[["user_id", "department", "role"]].drop_duplicates(subset=["user_id"])

# ---------------------------
# file.csv laden
# ---------------------------
files = pd.read_csv(file_access_path, dtype=str)
files["date"] = pd.to_datetime(files["date"], errors="coerce", dayfirst=False)

# ---------------------------
# Join
# ---------------------------
merged = files.merge(ldap, how="left", left_on="user", right_on="user_id")

# ---------------------------
# Denominators
# ---------------------------
total_employees = max(ldap["user_id"].nunique(), 1)
total_departments = max(ldap["department"].nunique(), 1)
total_roles = max(ldap["role"].nunique(), 1)

# ---------------------------
# Content Snippet Funktion
# ---------------------------
def pick_content_snippet(series, max_len=800):
    s = series.dropna().astype(str)
    if s.empty:
        return ""
    txt = max(s, key=len)
    return " ".join(txt.split())[:max_len]

def uniq_sorted_list(x):
    return sorted(pd.Series(x).dropna().astype(str).unique().tolist())

# ---------------------------
# Aggregation pro filename
# ---------------------------
features = merged.groupby("filename", dropna=False).agg(
    content_snippet=("content", lambda s: pick_content_snippet(s, max_len_content_snippet)),
    unique_user_count=("user", "nunique"),
    access_frequency=("filename", "size"),
    unique_dept_count=("department", "nunique"),
    accessing_roles=("role", uniq_sorted_list),
    accessing_departments=("department", uniq_sorted_list),
).reset_index()

# ---------------------------
# Time Features
# ---------------------------
time_features = merged.groupby("filename").agg(
    first_access=("date", "min"),
    last_access=("date", "max"),
).reset_index()
time_features["access_span_days"] = (
    time_features["last_access"] - time_features["first_access"]
).dt.days

features = features.merge(time_features, on="filename", how="left")

# ---------------------------
# Role Features
# ---------------------------
role_counts = merged.groupby("filename")["role"].nunique().reset_index()
role_counts.columns = ["filename", "unique_role_count"]
features = features.merge(role_counts, on="filename", how="left")

# ---------------------------
# Top User Ratio
# ---------------------------
def top_user_ratio(group):
    counts = group.value_counts(normalize=True)
    return round(counts.iloc[0], 4) if not counts.empty else 1.0

top_user = merged.groupby("filename")["user"].apply(top_user_ratio).reset_index()
top_user.columns = ["filename", "top_user_access_ratio"]
features = features.merge(top_user, on="filename", how="left")

# ---------------------------
# Removing extra hex from Content Snippet
# ---------------------------

import re

def clean_content_snippet(text):
    if not isinstance(text, str):
        return ""
    # Remove hex sequences like D0-CF-11-E0 or D0CF11E0
    text = re.sub(r'\b([0-9A-Fa-f]{2}-){2,}[0-9A-Fa-f]{2}\b', '', text)
    text = re.sub(r'\b[0-9A-Fa-f]{8,}\b', '', text)
    # Clean up extra whitespace left behind
    text = " ".join(text.split()).strip()
    return text

features["content_snippet"] = features["content_snippet"].apply(clean_content_snippet)

# ---------------------------
# Flags
# ---------------------------
features["single_department_file"] = (features["unique_dept_count"] == 1).astype(int)

# ---------------------------
# Totals + Ratios
# ---------------------------
features["total_employees"] = total_employees
features["total_departments"] = total_departments
features["total_roles"] = total_roles
features["access_ratio"] = features["unique_user_count"] / total_employees
features["dept_ratio"] = features["unique_dept_count"] / total_departments
features["role_ratio"] = features["unique_role_count"] / total_roles

# ---------------------------
# File Extension
# ---------------------------
features["file_extension"] = features["filename"].str.extract(r'(\.[^.]+)$')[0].str.lower().fillna("unknown")


# ---------------------------
# Column Order
# ---------------------------
features = features[[
    "filename",
    "file_extension",
    "content_snippet",
    "access_frequency",
    "unique_user_count",        "total_employees",      "access_ratio",
    "unique_dept_count",        "total_departments",    "dept_ratio",
    "unique_role_count",        "total_roles",          "role_ratio",
    "accessing_roles",
    "accessing_departments",
    "top_user_access_ratio",
    "single_department_file",
    "first_access",
    "last_access",
    "access_span_days",
]]

# ---------------------------
# Output
# ---------------------------
output_path = "file_profiles.csv"
features.to_csv(output_path, index=False, encoding="utf-8")
print(f"Done. {len(features)} file profiles written to {output_path}")