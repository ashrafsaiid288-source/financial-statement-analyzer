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

@st.cache_data
def load_uploaded_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.columns = [col.strip().lower() for col in df.columns]
    return df

st.sidebar.markdown("## Control Panel")
source = st.sidebar.radio("Select Data Source:", ["Use Demo Data", "Upload CSV File"])

cols_needed = {"date", "type", "category", "amount"}

if source == "Upload CSV File":
    file = st.sidebar.file_uploader("Upload Financial CSV", type=["csv"])
    if file is not None:
        df = load_uploaded_data(file)
        if not cols_needed.issubset(df.columns):
            st.sidebar.error(f"Error: Missing columns. Expected: {cols_needed}")
            st.stop()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["date", "amount"])
        df["type"] = df["type"].str.strip().str.title()
    else:
        st.sidebar.info("Upload a CSV file to start.")
        st.stop()
else:
    df = get_demo_data()

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
t_min, t_max = df["date"].min(), df["date"].max()
picked_dates = st.sidebar.date_input("Date Range", value=(t_min, t_max))

if len(picked_dates) == 2:
    df = df[(df["date"] >= pd.to_datetime(picked_dates[0])) & (df["date"] <= pd.to_datetime(picked_dates[1]))]

all_cats = sorted(df["category"].unique())
picked_cats = st.sidebar.multiselect("Categories", options=all_cats, default=all_cats)
df = df[df["category"].isin(picked_cats)]

if df.empty:
    st.warning("No data matches the selected criteria.")
    st.stop()

rev_data = df[df["type"] == "Revenue"]
exp_data = df[df["type"] == "Expense"]

total_rev = rev_data["amount"].sum()
total_exp = exp_data["amount"].sum()
net_profit = total_rev - total_exp
net_margin = (net_profit / total_rev * 100) if total_rev else 0

cogs_labels = [c for c in exp_data["category"].unique() if "cogs" in c.lower() or "cost of" in c.lower()]
cogs_val = exp_data[exp_data["category"].isin(cogs_labels)]["amount"].sum() if cogs_labels else 0
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

    with right_col:
        st.markdown("### Expense Sources")
        if not exp_data.empty:
            e_pie = exp_data.groupby("category")["amount"].sum()
            fig_e = px.pie(values=e_pie.values, names=e_pie.index, hole=0.7)
            fig_e.update_traces(marker=dict(colors=px.colors.sequential.Burg))
            fig_e.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_e, use_container_width=True)

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