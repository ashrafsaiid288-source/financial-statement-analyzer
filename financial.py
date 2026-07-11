import re
import difflib
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Financial Analyzer Ultra Dark", layout="wide", initial_sidebar_state="expanded")

# كود CSS بيجبر المتصفح يقلب كل حاجة دارك ويخلي الشكل عصري جدا
st.markdown("""
    <style>
    /* إجبار خلفية التطبيق بالكامل على اللون الداكن */
    .stApp {
        background-color: #0b0f19 !important;
        color: #e2e8f0 !important;
    }
    
    /* خلفية القائمة الجانبية */
    [data-testid="stSidebar"] {
        background-color: #111827 !important;
    }
    
    /* تصميم الكروت (Glassmorphism) */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        padding: 24px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5) !important;
        transition: transform 0.3s ease, border-color 0.3s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px) !important;
        border-color: #00ff9d !important;
    }
    
    /* تظبيط ألوان نصوص الكروت */
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
    }
    
    /* تظبيط شكل التبويبات (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0 0;
        border: 1px solid #334155;
        border-bottom: none;
        color: #94a3b8;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        border-top: 2px solid #38bdf8 !important;
    }
    
    /* الفواصل العرضية */
    hr {
        border-color: #334155 !important;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def get_demo_data():
    rng = np.random.default_rng(42)
    start_date = datetime(2025, 1, 1)
    data_list = []
    
    rev_cats = ["Product Sales", "Service Fees", "Other Income"]
    exp_cats = ["COGS", "Salaries", "Marketing", "Rent", "Utilities", "Misc"]

    for month_idx in range(12):
        current_month = start_date + timedelta(days=30 * month_idx)
        
        for cat in rev_cats:
            base_val = {"Product Sales": 180000, "Service Fees": 60000, "Other Income": 8000}[cat]
            tx_count = rng.integers(15, 30)
            for _ in range(tx_count):
                amt = max(500, rng.normal(base_val / tx_count, (base_val / tx_count) * 0.3))
                data_list.append({
                    "date": current_month + timedelta(days=int(rng.integers(0, 28))),
                    "type": "Revenue", "category": cat, "amount": round(amt, 2)
                })
                
        for cat in exp_cats:
            base_val = {"COGS": 90000, "Salaries": 70000, "Marketing": 20000, "Rent": 15000, "Utilities": 5000, "Misc": 7000}[cat]
            tx_count = rng.integers(5, 15)
            for _ in range(tx_count):
                amt = max(200, rng.normal(base_val / tx_count, (base_val / tx_count) * 0.25))
                data_list.append({
                    "date": current_month + timedelta(days=int(rng.integers(0, 28))),
                    "type": "Expense", "category": cat, "amount": round(amt, 2)
                })

    anomalies = [start_date + timedelta(days=int(d)) for d in rng.choice(range(360), 4, replace=False)]
    for d in anomalies:
        data_list.append({
            "date": d, "type": "Expense", "category": "Misc",
            "amount": round(rng.uniform(25000, 45000), 2)
        })

    final_df = pd.DataFrame(data_list)
    final_df["date"] = pd.to_datetime(final_df["date"])
    return final_df.sort_values("date").reset_index(drop=True)


# =====================================================================================
# SMART COLUMN DETECTION
# بدل ما نطلب أعمدة ثابتة (date, type, category, amount) بالاسم الحرفي،
# بنحاول نكتشفها تلقائيًا من أي اسم قريب (إنجليزي أو عربي)، ولو فشلنا بنسيب
# اليوزر يربط الأعمدة يدويًا من قائمة منسدلة.
# =====================================================================================

COLUMN_ALIASES = {
    "date": ["date", "transaction date", "transactiondate", "trans_date", "day",
             "posting date", "التاريخ", "تاريخ"],
    "type": ["type", "transaction type", "kind", "flow", "direction", "نوع", "النوع",
             "نوع العملية"],
    "category": ["category", "cat", "subcategory", "description", "desc", "account",
                 "label", "الفئة", "فئة", "التصنيف", "الوصف"],
    "amount": ["amount", "value", "amt", "total", "sum", "price", "قيمة", "المبلغ",
               "مبلغ", "القيمة"],
}

TYPE_VALUE_ALIASES = {
    "Revenue": ["revenue", "income", "credit", "in", "sale", "sales", "deposit",
                "دخل", "إيراد", "ايراد", "وارد"],
    "Expense": ["expense", "cost", "debit", "out", "expenditure", "outflow",
                "مصروف", "مصاريف", "منصرف", "صادر"],
}


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06FF]", "", str(s).strip().lower())


def auto_map_columns(df: pd.DataFrame) -> dict:
    """Try to map each raw column in df to one of our standard names
    (date/type/category/amount) using exact alias matches first, then
    fuzzy string matching as a fallback. Returns {standard_name: raw_col or None}."""
    raw_cols = list(df.columns)
    normalized_lookup = {_normalize(c): c for c in raw_cols}

    mapping = {}
    used_raw_cols = set()

    # Pass 1: exact alias matches
    for standard, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            key = _normalize(alias)
            if key in normalized_lookup and normalized_lookup[key] not in used_raw_cols:
                found = normalized_lookup[key]
                break
        if found:
            mapping[standard] = found
            used_raw_cols.add(found)
        else:
            mapping[standard] = None

    # Pass 2: fuzzy matching for anything still unmapped
    remaining_cols = [c for c in raw_cols if c not in used_raw_cols]
    for standard, raw_col in mapping.items():
        if raw_col is not None or not remaining_cols:
            continue
        all_aliases = COLUMN_ALIASES[standard] + [standard]
        best_match, best_score = None, 0.0
        for col in remaining_cols:
            for alias in all_aliases:
                score = difflib.SequenceMatcher(None, _normalize(col), _normalize(alias)).ratio()
                if score > best_score:
                    best_match, best_score = col, score
        if best_match and best_score >= 0.72:
            mapping[standard] = best_match
            used_raw_cols.add(best_match)
            remaining_cols = [c for c in raw_cols if c not in used_raw_cols]

    return mapping


def looks_like_period_header(col_name: str) -> bool:
    """Detects headers like '2024', 'Jan-2026', 'Q1 2025', '01/2026' that
    indicate a 'wide' financial statement layout (one column per period)."""
    s = str(col_name).strip()
    patterns = [
        r"^\d{4}$",                                   # 2024
        r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\-/ ]\d{2,4}$",  # Jan-2026
        r"^q[1-4][\-/ ]?\d{2,4}$",                     # Q1-2025
        r"^\d{1,2}[\-/]\d{4}$",                        # 01/2026
    ]
    return any(re.match(p, s, flags=re.IGNORECASE) for p in patterns)


def melt_wide_format(df: pd.DataFrame, id_cols: list, period_cols: list) -> pd.DataFrame:
    """Converts a 'wide' statement (one column per period) into the long
    transaction format the app needs (date, type, category, amount)."""
    melted = df.melt(id_vars=id_cols, value_vars=period_cols,
                      var_name="period", value_name="amount")
    melted["date"] = pd.to_datetime(melted["period"], errors="coerce")
    # لو مقدرش يفهم التاريخ من العمود (زي "2024" لوحدها)، حاول يضيف يناير كبداية للسنة
    still_bad = melted["date"].isna()
    if still_bad.any():
        melted.loc[still_bad, "date"] = pd.to_datetime(
            melted.loc[still_bad, "period"].astype(str) + "-01-01", errors="coerce"
        )
    return melted


def normalize_type_values(series: pd.Series) -> tuple[pd.Series, list]:
    """Maps arbitrary 'type' text (income/دخل/credit/...) to Revenue/Expense.
    Returns the normalized series plus a list of values it could not classify."""
    def classify(val):
        v = _normalize(val)
        if v in ("revenue", "expense"):
            return "Revenue" if v == "revenue" else "Expense"
        for standard, aliases in TYPE_VALUE_ALIASES.items():
            if any(_normalize(a) in v or v in _normalize(a) for a in aliases):
                return standard
        return None

    normalized = series.astype(str).map(classify)
    unclassified = sorted(series[normalized.isna()].astype(str).unique().tolist())
    return normalized, unclassified


@st.cache_data
def read_raw_csv(uploaded_file):
    return pd.read_csv(uploaded_file)


st.sidebar.markdown("## Control Panel")
source = st.sidebar.radio("Select Data Source:", ["Use Demo Data", "Upload CSV File"])

STANDARD_COLS = ["date", "type", "category", "amount"]
VALID_TYPES = {"Revenue", "Expense"}

if source == "Upload CSV File":
    file = st.sidebar.file_uploader("Upload Financial CSV", type=["csv"])
    if file is None:
        st.sidebar.info("Upload a CSV file to start.")
        st.stop()

    raw_df = read_raw_csv(file)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Column Mapping")

    auto_mapping = auto_map_columns(raw_df)

    # لو مفيش عمود amount ولا date ظاهر، وفي عناوين شكلها فترات زمنية (سنين/شهور)،
    # يبقى الملف على الأرجح "عريض" (قايمة دخل تقليدية) مش "طويل" (transactions).
    wide_period_cols = [c for c in raw_df.columns if looks_like_period_header(c)]
    is_probably_wide = (auto_mapping.get("amount") is None
                         and auto_mapping.get("date") is None
                         and len(wide_period_cols) >= 2)

    working_df = None

    if is_probably_wide:
        st.sidebar.info(
            "الملف ده شكله 'عريض' (كل عمود = سنة/شهر). هنحوّله تلقائيًا لصيغة معاملات."
        )
        non_period_cols = [c for c in raw_df.columns if c not in wide_period_cols]
        id_cols = st.sidebar.multiselect(
            "اختر عمود/أعمدة الوصف (زي Category أو Item)",
            options=non_period_cols,
            default=non_period_cols[:1] if non_period_cols else []
        )
        chosen_periods = st.sidebar.multiselect(
            "اختر أعمدة الفترات الزمنية (سنين/شهور)",
            options=wide_period_cols,
            default=wide_period_cols
        )
        if not id_cols or not chosen_periods:
            st.sidebar.warning("اختار على الأقل عمود وصف وعمود فترة واحد عشان نكمل.")
            st.stop()

        melted = melt_wide_format(raw_df, id_cols, chosen_periods)
        # في الشكل العريض مفيش عمود "type" غالبًا، فبنسيب اليوزر يحدد الفئات
        # اللي تعتبر Revenue واللي تعتبر Expense.
        desc_col = id_cols[0]
        all_items = sorted(melted[desc_col].astype(str).unique().tolist())
        st.sidebar.markdown("#### حدد نوع كل بند")
        revenue_items = st.sidebar.multiselect(
            "دي بنود إيرادات (Revenue)", options=all_items,
            default=[i for i in all_items if re.search(r"revenue|sale|income|إيراد|دخل", i, re.I)]
        )
        expense_items = [i for i in all_items if i not in revenue_items]

        melted["type"] = np.where(melted[desc_col].astype(str).isin(revenue_items), "Revenue", "Expense")
        melted["category"] = melted[desc_col]
        working_df = melted[["date", "type", "category", "amount"]].copy()

    else:
        missing = [c for c in STANDARD_COLS if auto_mapping.get(c) is None]
        if missing:
            st.sidebar.warning(
                "معرفناش نلاقي كل الأعمدة المطلوبة تلقائيًا. اربط الأعمدة يدويًا:"
            )
            for col in missing:
                choice = st.sidebar.selectbox(
                    f"العمود اللي يمثل '{col}'",
                    options=["-- اختر --"] + list(raw_df.columns),
                    key=f"map_{col}"
                )
                if choice != "-- اختر --":
                    auto_mapping[col] = choice

        still_missing = [c for c in STANDARD_COLS if auto_mapping.get(c) is None]
        if still_missing:
            st.sidebar.error(f"لسه ناقص ربط الأعمدة دي: {still_missing}")
            st.stop()

        working_df = raw_df[[auto_mapping[c] for c in STANDARD_COLS]].copy()
        working_df.columns = STANDARD_COLS

    df = working_df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    original_type_text = df["type"].astype(str)
    df["type"], unclassified_types = normalize_type_values(df["type"])

    if unclassified_types:
        st.sidebar.markdown("#### تصنيف قيم غير معروفة في عمود Type")
        manual_type_map = {}
        for val in unclassified_types:
            picked = st.sidebar.selectbox(
                f"القيمة '{val}' تتصنف إزاي؟",
                options=["تجاهل", "Revenue", "Expense"],
                key=f"typeval_{val}"
            )
            if picked != "تجاهل":
                manual_type_map[val] = picked

        for val, standard in manual_type_map.items():
            df.loc[original_type_text == val, "type"] = standard

    rows_before = len(df)
    bad_dates = df["date"].isna().sum()
    bad_amounts = df["amount"].isna().sum()
    df = df.dropna(subset=["date", "amount"])

    invalid_type_rows = df[~df["type"].isin(VALID_TYPES)]
    if not invalid_type_rows.empty:
        st.sidebar.warning(
            f"تم تجاهل {len(invalid_type_rows)} صف بقيم 'type' غير قابلة للتصنيف."
        )
        df = df[df["type"].isin(VALID_TYPES)]

    if bad_dates or bad_amounts:
        st.sidebar.warning(
            f"تم تجاهل صفوف فيها تواريخ أو مبالغ غير صالحة "
            f"({bad_dates} تاريخ غير صالح، {bad_amounts} مبلغ غير صالح)."
        )

    if df.empty:
        st.sidebar.error(
            f"بعد التنظيف، لم يتبقَّ أي صف صالح من أصل {rows_before} صف في الملف. "
            "راجع ربط الأعمدة وقيم النوع (type)."
        )
        st.stop()
else:
    df = get_demo_data()

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
t_min, t_max = df["date"].min(), df["date"].max()
picked_dates = st.sidebar.date_input("Date Range", value=(t_min, t_max))

# الإصلاح 1: تنبيه المستخدم لو اختار تاريخ واحد بس بدل range كامل
if isinstance(picked_dates, (tuple, list)) and len(picked_dates) == 2:
    df = df[(df["date"] >= pd.to_datetime(picked_dates[0])) & (df["date"] <= pd.to_datetime(picked_dates[1]))]
else:
    st.sidebar.warning("من فضلك اختار تاريخ البداية والنهاية معًا لتطبيق الفلترة الزمنية.")

all_cats = sorted(df["category"].astype(str).unique())
picked_cats = st.sidebar.multiselect("Categories", options=all_cats, default=all_cats)
df = df[df["category"].astype(str).isin(picked_cats)]

if df.empty:
    st.warning("No data matches the selected criteria.")
    st.stop()

rev_data = df[df["type"] == "Revenue"]
exp_data = df[df["type"] == "Expense"]

total_rev = rev_data["amount"].sum()
total_exp = exp_data["amount"].sum()
net_profit = total_rev - total_exp
net_margin = (net_profit / total_rev * 100) if total_rev else 0

# الإصلاح 3: السماح باختيار عمود/فئات الـ COGS يدويًا بدل الاعتماد على auto-detect هش
st.sidebar.markdown("---")
st.sidebar.markdown("### COGS Settings")
auto_detected_cogs = [
    c for c in exp_data["category"].astype(str).unique()
    if "cogs" in c.lower() or "cost of" in c.lower()
]
all_exp_cats = sorted(exp_data["category"].astype(str).unique())
cogs_labels = st.sidebar.multiselect(
    "اختر الفئات اللي تمثّل COGS (تكلفة البضاعة المباعة)",
    options=all_exp_cats,
    default=auto_detected_cogs,
    help="لو الفئة عندك اسمها مختلف زي 'Direct Costs'، اختارها يدويًا هنا."
)
cogs_val = exp_data[exp_data["category"].astype(str).isin(cogs_labels)]["amount"].sum() if cogs_labels else 0
gross_profit = total_rev - cogs_val
gross_margin = (gross_profit / total_rev * 100) if total_rev else 0

monthly_rev = rev_data.groupby(rev_data["date"].dt.to_period("M"))["amount"].sum()
growth_rate = None
if len(monthly_rev) >= 2:
    growth_rate = ((monthly_rev.iloc[-1] - monthly_rev.iloc[-2]) / monthly_rev.iloc[-2]) * 100

st.title("Nexus Financial Analytics")
st.markdown("Advanced, secure, and fully dark-mode optimized financial interface.")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Revenue", f"${total_rev:,.0f}")
kpi2.metric("Total Expenses", f"${total_exp:,.0f}")
kpi3.metric("Net Profit", f"${net_profit:,.0f}", delta=f"{net_margin:.1f}% Margin")
kpi4.metric("Gross Margin", f"{gross_margin:.1f}%" if cogs_labels else "N/A")
kpi5.metric("MoM Growth", f"{growth_rate:.1f}%" if growth_rate is not None else "N/A")

st.markdown("<hr>", unsafe_allow_html=True)

tab_overview, tab_breakdown, tab_anomalies = st.tabs([
    "Trend Overview", 
    "Breakdown", 
    "AI Flagging"
])

COLOR_REV = "#00e676"
COLOR_EXP = "#ff1744"

with tab_overview:
    trend_df = df.copy()
    trend_df["month"] = trend_df["date"].dt.to_period("M").astype(str)
    grouped_trend = trend_df.groupby(["month", "type"])["amount"].sum().reset_index()

    bar_chart = px.bar(
        grouped_trend, x="month", y="amount", color="type", barmode="group",
        color_discrete_map={"Revenue": COLOR_REV, "Expense": COLOR_EXP},
    )
    bar_chart.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(bar_chart, use_container_width=True)

with tab_breakdown:
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.markdown("### Revenue Sources")
        if not rev_data.empty:
            r_pie = rev_data.groupby("category")["amount"].sum()
            fig_r = px.pie(values=r_pie.values, names=r_pie.index, hole=0.7)
            fig_r.update_traces(marker=dict(colors=px.colors.sequential.Tealgrn))
            fig_r.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_r, use_container_width=True)
        else:
            st.info("لا توجد بيانات إيرادات ضمن الفلاتر الحالية.")

    with right_col:
        st.markdown("### Expense Sources")
        if not exp_data.empty:
            e_pie = exp_data.groupby("category")["amount"].sum()
            fig_e = px.pie(values=e_pie.values, names=e_pie.index, hole=0.7)
            fig_e.update_traces(marker=dict(colors=px.colors.sequential.Burg))
            fig_e.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_e, use_container_width=True)
        else:
            st.info("لا توجد بيانات مصروفات ضمن الفلاتر الحالية.")

with tab_anomalies:
    st.markdown("### Unusual Transactions Detector")
    
    def get_outliers(dataset, threshold=2.5):
        frames = []
        for category, group in dataset.groupby("category"):
            if len(group) < 4: continue
            m_val, s_val = group["amount"].mean(), group["amount"].std()
            if s_val == 0 or np.isnan(s_val): continue
            z = (group["amount"] - m_val) / s_val
            matched = group[z.abs() > threshold].copy()
            matched["z_score"] = z[z.abs() > threshold].round(2)
            frames.append(matched)
        return pd.concat(frames) if frames else pd.DataFrame(columns=list(dataset.columns) + ["z_score"])

    detected_outliers = get_outliers(df)

    if detected_outliers.empty:
        st.success("All transactions are normal.")
    else:
        st.warning(f"Flagged {len(detected_outliers)} unusual transactions.")
        st.dataframe(detected_outliers.sort_values("z_score", key=abs, ascending=False), use_container_width=True, hide_index=True)

        scatter = go.Figure()
        scatter.add_trace(go.Scatter(
            x=df["date"], y=df["amount"], mode="markers", 
            marker=dict(color="#4A5568", size=6), name="Normal"
        ))
        scatter.add_trace(go.Scatter(
            x=detected_outliers["date"], y=detected_outliers["amount"], mode="markers", 
            marker=dict(color="#ff1744", size=12, symbol="cross"), name="Anomaly"
        ))
        scatter.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(scatter, use_container_width=True)
