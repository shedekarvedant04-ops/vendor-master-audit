# ============================================================
# DYNAMIC VENDOR MASTER AUDIT – FINAL COMPLETE SCRIPT
# ============================================================
# FEATURES:
# 1. Excel upload
# 2. Dynamic column mapping (add / remove)
# 3. PAN & GST format validation
# 4. Duplicate & missing checks
# 5. Level 1: Severity & Risk Scoring
# 6. Dynamic Exception Selection
# 7. Dashboard reacts to selected exception
# 8. Level 3: Top risky vendors, drill-down, exception analytics
# ============================================================
import streamlit as st
import pandas as pd
import re
import os
from difflib import SequenceMatcher
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from itertools import permutations

# ------------------------------------------------------------
# PAGE SETUP
# ------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "main"
st.set_page_config(page_title="Dynamic Vendor Master Audit", layout="wide")

if "show_exception_selector" not in st.session_state:
    st.session_state.show_exception_selector = False
# ------------------------------------------------------------
# SOFT PASTEL CSS + CENTERING
# ------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

html, body, #root, .appview-container, .main {
    height: 100%;
    margin: 0;
    background: linear-gradient(135deg, #a8edea, #fed6e3);
    background-size: 400% 400%;
    animation: pastelFade 20s ease infinite;
    font-family: 'Inter', sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
}

@keyframes pastelFade {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

.block-container {
    background: rgba(255, 255, 255, 0.85);
    max-width: 900px;
    width: 90vw;
    border-radius: 15px;
    padding: 30px 40px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    color: #334e68;
}

h1, h2, h3, h4 {
    color: #2c3e50;
    font-weight: 600;
    margin-bottom: 0.3em;
}

h1 {
    font-size: 2.8rem;
    text-align: center;
    margin-bottom: 0.5em;
}

h2 {
    font-size: 1.8rem;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
}

.stButton>button {
    background: #3b82f6;
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 25px;
    font-weight: 600;
    font-size: 1.1rem;
    transition: background-color 0.3s ease, box-shadow 0.3s ease;
    box-shadow: 0 3px 8px rgba(59,130,246,0.4);
    cursor: pointer;
}

.stButton>button:hover {
    background: #2563eb;
    box-shadow: 0 6px 15px rgba(37,99,235,0.6);
}

.stSelectbox>div>div>div>select, 
.stTextInput>div>input {
    background-color: #f9fafb;
    color: #334e68;
    border-radius: 8px;
    border: 1.5px solid #cbd5e1;
    padding: 8px 14px;
    font-weight: 500;
    font-size: 1rem;
    transition: border-color 0.3s ease;
    width: 100%;
}

.stSelectbox>div>div>div>select:focus,
.stTextInput>div>input:focus {
    border-color: #3b82f6;
    outline: none;
    box-shadow: 0 0 8px rgba(59,130,246,0.5);
}

label, .stTextInput>label, .stSelectbox>label {
    color: #334e68;
    font-weight: 600;
    font-size: 1.1rem;
    margin-bottom: 4px;
    display: block;
}

.stDataFrame>div {
    border-radius: 12px;
    border: 1px solid #cbd5e1;
    background: white !important;
    box-shadow: 0 4px 12px rgba(50, 50, 93, 0.1);
    margin-top: 15px;
}

.stDataFrame table {
    border-collapse: separate;
    border-spacing: 0 6px;
}

.stDataFrame thead tr th {
    background: #3b82f6 !important;
    color: white !important;
    font-weight: 700;
    border-radius: 8px 8px 0 0 !important;
    padding: 12px !important;
    text-align: left !important;
}

.stDataFrame tbody tr td {
    padding: 12px !important;
    background: #f9fafb;
    color: #334e68;
    font-weight: 500;
    border-bottom: 8px solid transparent;
    transition: background-color 0.25s ease;
}

.stDataFrame tbody tr:hover td {
    background-color: #dbeafe !important;
    color: #1e40af;
}

.stAlert {
    margin-top: 15px;
    color: #2563eb;
    font-weight: 600;
    font-size: 1.1rem;
    background: #dbeafe;
    border-radius: 8px;
    padding: 10px 20px;
    border: 1px solid #2563eb;
}  
/* ---- Developer Watermark ---- */
#developer-watermark {
    position: fixed;
    bottom: 12px;
    right: 18px;
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.45);
    letter-spacing: 0.5px;
    z-index: 9999;
    pointer-events: none;
    user-select: none;
}
</style>
""", unsafe_allow_html=True)

st.title("🧾 Dynamic Vendor Master Audit Tool")
st.markdown(
    '<div id="developer-watermark">Developed by :- Vedant Shedekar</div>',
    unsafe_allow_html=True
)
# ------------------------------------------------------------
# Exception File
# ------------------------------------------------------------
REQUEST_DB = "exception_requests.csv"

# ---------------- INITIALIZE REQUEST DB SAFELY ----------------
if "req_df" not in st.session_state:

    if os.path.exists(REQUEST_DB):
        req_df = pd.read_csv(REQUEST_DB)
    else:
        req_df = pd.DataFrame(
            columns=[
                "exception_key",
                "exception_text",
                "count",
                "status",
                "last_updated"
            ]
        )
        req_df.to_csv(REQUEST_DB, index=False)

    # Clean bad rows ONCE
    req_df = req_df[req_df["exception_text"].notna()]
    req_df = req_df[req_df["exception_text"].str.strip() != ""]

    st.session_state.req_df = req_df

# ---------------- ALWAYS READ FROM SESSION ----------------
req_df = st.session_state.req_df

pending_count = req_df[req_df["status"] == "PENDING"].shape[0]

# ------------------------------------------------------------
# REQUEST BUTTON (TOP RIGHT)
# ------------------------------------------------------------
nav_l, nav_r  = st.columns([2, 8])
with nav_l:
    if st.button(f"📝 Requests ({pending_count})"):
        st.session_state.page = "requests"
# ------------------------------------------------------------
# HELPER FUNCTIONS – VALIDATION LOGIC
# ------------------------------------------------------------
def similarity(a, b):
    a = "" if pd.isna(a) else str(a)
    b = "" if pd.isna(b) else str(b)
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def log_exception_request(user_text, threshold=0.70):
    """
    Stores new exception request.
    If similar request exists → increments count.
    """
    req_df = st.session_state.req_df.copy()

    matched = False

    for idx, row in req_df.iterrows():
        score = similarity(user_text, row["exception_text"])

        if score >= threshold and row["status"] == "PENDING":
            req_df.loc[idx, "count"] += 1
            req_df.loc[idx, "last_updated"] = datetime.now()
            matched = True
            break

    if not matched:
        req_df = pd.concat(
            [req_df, pd.DataFrame([{
                "exception_key": user_text.replace(" ", "_").lower(),
                "exception_text": user_text,
                "count": 1,
                "status": "PENDING",
                "last_updated": datetime.now()
            }])],
            ignore_index=True
        )

    st.session_state.req_df = req_df
    req_df.to_csv(REQUEST_DB, index=False)

def generate_cross_exceptions(df, field_map):
    """
    Creates cross-field inconsistency exceptions:
    Same X → Different Y for all field combinations
    """
    norm = normalize_labels(field_map)
    fields = list(norm.keys())

    for base, compare in permutations(fields, 2):
        base_col = norm[base]
        compare_col = norm[compare]

        # Safety checks
        if base_col not in df.columns or compare_col not in df.columns:
            continue

        col_name = f"Same_{base.upper()}_Different_{compare.upper()}"

        df[col_name] = (
            df.groupby(base_col)[compare_col]
              .transform("nunique")
              .gt(1)
            & df[base_col].notna()
            & (df[base_col].astype(str).str.strip() != "")
        )

    return df

def extract_pan_from_gst(gst):
    """Extract PAN portion from GSTIN"""
    try:
        gst = str(gst).upper().strip()
        return gst[2:12] if len(gst) >= 12 else None
    except:
        return None

def is_missing_contact(contact):
    if pd.isna(contact):
        return True

    contact = str(contact).strip()
    return contact == ""

def is_invalid_contact(contact):
    if pd.isna(contact):
        return False  # handled separately

    contact = str(contact).strip()

    if contact == "":
        return False  # handled separately

    contact = re.sub(r"[^\d]", "", contact)

    if len(contact) < 10 or len(contact) > 15:
        return True

    if len(set(contact)) == 1:
        return True

    return False

def is_missing_email(email):
    if pd.isna(email):
        return True
    return str(email).strip() == ""

def is_invalid_email(email):
    if pd.isna(email):
        return True

    email = str(email).strip().lower()

    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"

    return not bool(re.match(pattern, email))

def validate_pan(pan):
    """PAN format validation"""
    if pd.isna(pan) or str(pan).strip() == "":
        return None
    return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", str(pan).strip().upper()))

def validate_gst(gst):
    """GST format validation"""
    if pd.isna(gst) or str(gst).strip() == "":
        return None
    return bool(re.match(
        r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9]{1}Z[0-9A-Z]{1}$",
        str(gst).strip().upper()
    ))

def normalize_labels(field_map):
    """Normalize mapping labels"""
    return {k.strip().lower(): v for k, v in field_map.items()}

def sanitize_sheet_name(name):
    name = name.replace("--", "").replace(" ", "_")
    return name[:31]  # Excel sheet name limit

# ------------------------------------------------------------
# EXCEPTION REQUEST REGISTRY (DEVELOPER BACKLOG)
# ------------------------------------------------------------
# def log_exception_request(desc):
#     try:
#         df = pd.read_csv("exception_requests.csv")
#     except:
#         df = pd.DataFrame(columns=["Exception", "Request_Count"])

#     if desc in df["Exception"].values:
#         df.loc[df["Exception"] == desc, "Request_Count"] += 1
#     else:
#         df = pd.concat(
#             [df, pd.DataFrame([[desc, 1]], columns=df.columns)],
#             ignore_index=True
#         )

#     df.to_csv("exception_requests.csv", index=False)

# ------------------------------------------------------------
# CORE AUDIT RULE ENGINE
# ------------------------------------------------------------
def apply_rules(df, field_map):
    norm = normalize_labels(field_map)

    # Missing & Duplicate checks
    for label, col in field_map.items():
        if col not in df.columns:
            continue

        df[f"Missing_{label}"] = (
            df[col].isna() | (df[col].astype(str).str.strip() == "")
        )

        df[f"Duplicate_{label}"] = (
            df[col].notna()
            & (df[col].astype(str).str.strip() != "")
            & df[col].duplicated(keep=False) & df[col].notna()
        )

    # PAN validation
    if "pan" in norm:
        df["Invalid_PAN"] = df[norm["pan"]].apply(validate_pan) == False

    # GST validation
    if "gst" in norm:
        df["Invalid_GST"] = df[norm["gst"]].apply(validate_gst) == False

    # PAN–GST mismatch
    if "pan" in norm and "gst" in norm:
        df["GST_PAN_Mismatch"] = (
            df[norm["gst"]].apply(extract_pan_from_gst).notna()
            & df[norm["pan"]].notna()
            & (
                df[norm["pan"]].astype(str).str.upper().str.strip()
                != df[norm["gst"]].apply(extract_pan_from_gst)
            )
        )
    # -------- BEHAVIORAL / RISK --------
    if "status" in norm:
        df["Inactive_But_Configured"] = (
            df[norm["status"]].astype(str).str.lower().str.contains("inactive")
        )
    if "contact" in norm:
        df["Missing_Contact"] = df[norm["contact"]].apply(is_missing_contact)
        df["Invalid_Contact"] = df[norm["contact"]].apply(is_invalid_contact)

    if "email" in norm:
        df["Invalid_Email"] = df[norm["email"]].apply(is_invalid_email)
        df["Missing_Email"] = df[norm["email"]].apply(is_missing_email)

    df = generate_cross_exceptions(df, field_map)
    return df
    

# ------------------------------------------------------------
# LEVEL 1 – SEVERITY & RISK SCORING
# ------------------------------------------------------------
def classify_severity(row):
    if row.get("Invalid_PAN") or row.get("Invalid_GST"):
        return "Critical"
    if row.get("GST_PAN_Mismatch"):
        return "Critical"
    
    for col in row.index:
        if col.startswith("Duplicate_") and row[col]:
            return "High"
        if col.startswith("Missing_") and row[col]:
            if "pan" in col.lower() or "gst" in col.lower():
                return "High"
            if "contact" in col.lower():
                return "High"
            if "email" in col.lower():
                return "Medium"
            return "Medium"
        if col.startswith("Invalid_") and row[col]:
            if "pan" in col.lower() or "gst" in col.lower():
                return "Medium"
            if "contact" in col.lower():
                return "Medium"
            if "email" in col.lower():
                return "Low"
            return "Medium"

    return "No Issue"

def risk_score(severity):
    return {"Critical": 30, "High": 20, "Medium": 10}.get(severity, 0)

def risk_level(score):
    if score >= 60:
        return "High Risk"
    if score >= 30:
        return "Medium Risk"
    if score > 0:
        return "Low Risk"
    return "No Risk"

# ------------------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------------------
uploaded_file = st.file_uploader(
    "📤 Upload Vendor Master Excel",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file:

    # 🔐 SAVE FILE BYTES (CRITICAL FOR STREAMLIT CLOUD)
    st.session_state["file_bytes"] = uploaded_file.getvalue()
    st.session_state["file_name"] = uploaded_file.name

    # ---------- HANDLE CSV ----------
    if uploaded_file.name.lower().endswith(".csv"):

        df = pd.read_csv(BytesIO(st.session_state["file_bytes"]))
        st.session_state.raw_df = df
        st.success("CSV file uploaded successfully")

    # ---------- HANDLE EXCEL ----------
    else:
        excel_file = pd.ExcelFile(BytesIO(st.session_state["file_bytes"]))
        sheet_names = excel_file.sheet_names

        selected_sheet = st.selectbox(
            "📄 Select Sheet to Audit",
            sheet_names
        )

        df = pd.read_excel(
            BytesIO(st.session_state["file_bytes"]),
            sheet_name=selected_sheet
        )

        st.session_state.raw_df = df
        st.success(f"Sheet '{selected_sheet}' loaded successfully")

    # ---------- PREVIEW ----------
    st.dataframe(st.session_state.raw_df.head())

    # 🔑 DEFINE COLUMNS ONCE
    df = st.session_state.raw_df
    columns = df.columns.tolist()

    # --------------------------------------------------------
    # DYNAMIC COLUMN MAPPING
    # --------------------------------------------------------
    if "mappings" not in st.session_state:
        st.session_state.mappings = [
            {"label": "", "column": None},
            {"label": "", "column": None},
            {"label": "", "column": None},
            {"label": "", "column": None},
        ]

    st.subheader("🛠️ Column Mapping")

    selected_cols = []
    remove_idx = None

    for i, m in enumerate(st.session_state.mappings):
        c1, c2, c3 = st.columns([3, 6, 1])

        with c1:
            m["label"] = st.text_input("Field Name", m["label"], key=f"lbl_{i}")

        with c2:
            options = ["-- Select Column --"] + [
                c for c in columns if c not in selected_cols or c == m["column"]
            ]
            sel = st.selectbox("Column", options, key=f"col_{i}")
            m["column"] = None if sel == "-- Select Column --" else sel
            if m["column"]:
                selected_cols.append(m["column"])

        with c3:
            if st.button("❌", key=f"rm_{i}"):
                remove_idx = i

    if remove_idx is not None:
        st.session_state.mappings.pop(remove_idx)
        st.session_state["_refresh"] = True
        st.rerun()

    if st.button("➕ Add Mapping"):
        st.session_state.mappings.append({"label": "", "column": None})
        st.session_state["_refresh"] = True
        st.rerun()

    # --------------------------------------------------------
    # RUN AUDIT
    # --------------------------------------------------------
    if st.button("🔍 Run Validation"):
        field_map = {
            m["label"]: m["column"]
            for m in st.session_state.mappings
            if m["label"] and m["column"]
        }

        audit_df = apply_rules(df.copy(), field_map)
        audit_df["Severity"] = audit_df.apply(classify_severity, axis=1)
        audit_df["Risk_Score"] = audit_df["Severity"].apply(risk_score)
        audit_df["Risk_Level"] = audit_df["Risk_Score"].apply(risk_level)

        st.session_state.audit_df = audit_df
        st.session_state.exception_cols = [
            c for c in audit_df.columns if audit_df[c].dtype == bool
        ]

    # --------------------------------------------------------
    # DYNAMIC EXCEPTION SELECTION & DASHBOARD
    # --------------------------------------------------------
    if "audit_df" in st.session_state:
        audit_df = st.session_state.audit_df
        exception_cols = st.session_state.exception_cols

        st.subheader("🎯 Dynamic Exception Selection")

        selected_exception = st.selectbox(
            "Select Exception Type",
            ["-- All Exceptions --"] + exception_cols + ["➕ New Exception Request"]
        )

        if selected_exception == "➕ New Exception Request":
            txt = st.text_area("Describe exception")
            if st.button("Submit Request"):
                if txt.strip():
                    log_exception_request(txt.strip())
                    st.success("Exception logged for developer review")
            st.stop()

        # Build exception dataset
        if selected_exception == "-- All Exceptions --":
            dashboard_df = audit_df[audit_df[exception_cols].any(axis=1)]
        else:
            dashboard_df = audit_df[audit_df[selected_exception]]

        st.subheader("🚨 Exception Output Dataset")
        st.dataframe(dashboard_df)
        # ----------------------------------------------------
        # DOWNLOAD EXCEPTION OUTPUT DATASET
        # ----------------------------------------------------
        st.subheader("⬇️ Download Selected Exception Report")

        download_buffer = BytesIO()

        with pd.ExcelWriter(download_buffer) as writer:
            dashboard_df.to_excel(
                writer,
                index=False,
                sheet_name="Exception_Report"
            )

        st.download_button(
            label="📥 Download Excel Report",
            data=download_buffer.getvalue(),
            file_name=f"Exception_Report_{selected_exception.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.subheader("📦 Bulk Exception Download")

        if st.button("📥 Download Selected Exception Workbook"):
            st.session_state.show_exception_selector = True

        # ----------------------------------------------------
        # EXCEPTION CHECKLIST (ON-DEMAND)
        # ----------------------------------------------------
        if st.session_state.show_exception_selector:

            st.markdown("### ☑️ Select Exceptions to Include")

            valid_exception_map = {
                exc: audit_df[audit_df[exc]]
                for exc in exception_cols
                if audit_df[exc].any()
            }

            if not valid_exception_map:
                st.warning("No exceptions with data available for download.")
                st.session_state.show_exception_selector = False
                st.stop()

            # Init selection state
            if "selected_exceptions" not in st.session_state:
                st.session_state.selected_exceptions = list(valid_exception_map.keys())

            # ---- SELECT ALL / DESELECT ALL ----
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Select All", key="select_all_btn"):
                    for exc in valid_exception_map.keys():
                        st.session_state[f"chk_{exc}"] = True

            with col2:
                if st.button("❌ Deselect All", key="deselect_all_btn"):
                    for exc in valid_exception_map.keys():
                        st.session_state[f"chk_{exc}"] = False

            include_all = st.checkbox(
                "Include All Exceptions (Combined)",
                value=True,
                key="include_all_exc"
            )

            st.markdown("---")

            # Individual checkboxes
            selected = []

            for exc in valid_exception_map.keys():
                if st.checkbox(
                    exc,
                    key=f"chk_{exc}",
                    value=st.session_state.get(f"chk_{exc}", True)
                ):
                    selected.append(exc)

            st.session_state.selected_exceptions = selected

            st.markdown("### ⬇️ Generate Workbook")

            if st.button("📂 Generate in Single Workbook", key="gen_excel"):

                if not selected and not include_all:
                    st.warning("Please select at least one exception.")
                    st.stop()

                buffer = BytesIO()

                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

                    if include_all:
                        all_df = audit_df[audit_df[list(valid_exception_map.keys())].any(axis=1)]
                        if not all_df.empty:
                            all_df.to_excel(writer, index=False, sheet_name="All_Exceptions")

                    for exc in selected:
                        df_exc = valid_exception_map.get(exc)
                        if df_exc is not None and not df_exc.empty:
                            df_exc.to_excel(writer, index=False, sheet_name=exc[:31])
                
                file_base = uploaded_file.name.rsplit(".", 1)[0]
                
                st.session_state.excel_file_bytes = buffer.getvalue()

                st.download_button(
                    "⬇️ Download Excel File",
                    data=st.session_state.excel_file_bytes,
                    file_name=f"All_Exceptions_{file_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.session_state.download_completed = True
                
            if st.button("📂 Generate in Multiple Workbooks", key="gen_multi_excel"):

                if not selected:
                    st.warning("Please select at least one exception.")
                    st.stop()

                from zipfile import ZipFile
                zip_buffer = BytesIO()

                file_base = uploaded_file.name.rsplit(".", 1)[0]

                with ZipFile(zip_buffer, "w") as zip_file:

                    for exc in selected:
                        df_exc = valid_exception_map.get(exc)

                        if df_exc is None or df_exc.empty:
                            continue

                        excel_buffer = BytesIO()

                        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                            df_exc.to_excel(
                                writer,
                                index=False,
                                sheet_name=exc[:31]
                            )

                        zip_file.writestr(
                            f"{exc}_{file_base}.xlsx",
                            excel_buffer.getvalue()
                        )

                st.download_button(
                    label="⬇️ Download Multiple Workbooks (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"Selected_Exceptions_{file_base}.zip",
                    mime="application/zip"
                )
                
                st.session_state.download_completed = True

            if st.button("❌ Cancel Download", key="cancel_bulk_download"):

                st.session_state.show_exception_selector = False
                st.session_state.selected_exceptions = []
                st.session_state.download_completed = False

                for exc in valid_exception_map.keys():
                    st.session_state.pop(f"chk_{exc}", None)

                st.session_state.pop("excel_ready", None)
                st.session_state.pop("excel_file_bytes", None)

                st.rerun()

        # Stop dashboard if no records
        if dashboard_df.empty:
            st.warning("No records found for the selected exception.")
            st.stop()

        # ----------------------------------------------------
        # LEVEL 3 – DASHBOARD (DYNAMIC)
        # ----------------------------------------------------
        st.subheader("📊 Executive Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Vendors", len(dashboard_df))
        c2.metric("Critical Vendors", (dashboard_df["Severity"] == "Critical").sum())
        c3.metric("High Risk Vendors", (dashboard_df["Risk_Level"] == "High Risk").sum())
        c4.metric("Medium Risk Vendors", (dashboard_df["Risk_Level"] == "Medium Risk").sum())

        # Top Risky Vendors
        st.subheader("🔥 Top Risky Vendors")
        st.dataframe(dashboard_df.sort_values("Risk_Score", ascending=False).head(10))

        # Drill-down
        st.subheader("🔎 Drill-Down Analysis")
        f1, f2 = st.columns(2)

        with f1:
            risk_filter = st.selectbox(
                "Risk Level",
                ["All"] + sorted(dashboard_df["Risk_Level"].unique())
            )

        with f2:
            severity_filter = st.selectbox(
                "Severity",
                ["All"] + sorted(dashboard_df["Severity"].unique())
            )

        filtered_df = dashboard_df.copy()

        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["Risk_Level"] == risk_filter]

        if severity_filter != "All":
            filtered_df = filtered_df[filtered_df["Severity"] == severity_filter]

        st.dataframe(filtered_df)
        
        # DEEP RISK SCORING
        st.subheader("⚠️ Deep Risk Scoring")
        dashboard_df["Composite_Risk"] = (
            dashboard_df[exception_cols].sum(axis=1)
            .clip(upper=10)
            * dashboard_df["Risk_Score"]
        )
        st.dataframe(dashboard_df[["Composite_Risk"]].describe())

        # Exception analytics
        st.subheader("📌 Exception Analytics")

        exc_summary = {
            col: int(dashboard_df[col].sum())
            for col in exception_cols
        }

        exc_df = (
            pd.DataFrame.from_dict(exc_summary, orient="index", columns=["Exception Count"])
            .sort_values("Exception Count", ascending=False)
        )

        st.dataframe(exc_df)
        
        # AUTO INSIGHTS
        
        st.subheader("🧠 Auto Insights")
        insights = []
        if (dashboard_df["Severity"] == "Critical").mean() > 0.2:
            insights.append("High proportion of critical vendors detected.")
        if dashboard_df["Composite_Risk"].mean() > 50:
            insights.append("Overall vendor master risk is elevated.")

        if insights:
            for i in insights:
                st.warning(i)
        else:
            st.success("No major risk patterns detected.")
else:
    st.info("Please upload an Excel file to begin the audit.")
# ------------------------------------------------------------
# REQUEST PAGE
# ------------------------------------------------------------
if st.session_state.page == "requests":

    st.subheader("📌 Pending Exception Requests")

    req_df = pd.read_csv(REQUEST_DB)
    pending_df = req_df[req_df["status"] == "PENDING"]

    if pending_df.empty:
        st.info("No pending exception requests.")
    else:
        st.dataframe(
            pending_df[["exception_text", "count", "last_updated"]],
            use_container_width=True
        )

    # ---------------- ADMIN CONTROLS ----------------
    st.subheader("🔒 Admin Controls")

    admin_pwd = st.text_input("Admin Password", type="password")

    if admin_pwd == "admin123":  # CHANGE IN PROD

        selected_req = st.selectbox(
            "Select Request",
            pending_df["exception_text"].tolist()
            if not pending_df.empty else []
        )

        c1, c2 = st.columns(2)

        with c1:
            if st.button("✔ Mark Done") and selected_req:
                req_df.loc[
                    req_df["exception_text"] == selected_req, "status"
                ] = "DONE"
                req_df.to_csv(REQUEST_DB, index=False)
                st.success("Marked as DONE")
                st.rerun()

        with c2:
            if st.button("🗑 Delete") and selected_req:
                req_df = req_df[
                    req_df["exception_text"] != selected_req
                ]
                req_df.to_csv(REQUEST_DB, index=False)
                st.success("Request Deleted")
                st.rerun()

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "main"

    st.stop()
    