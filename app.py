
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Restaurant Order Analytics",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🍽️ Restaurant Order Analytics")
st.caption("Interactive analysis of order volume, timing, and kitchen performance.")

# ---------- Data loading ----------
@st.cache_data
def load_data(file_or_path, sheet_name):
    if isinstance(file_or_path, str):
        df = pd.read_excel(file_or_path, sheet_name=sheet_name)
    else:
        df = pd.read_excel(file_or_path, sheet_name=sheet_name)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Number_Of_Orders"] = pd.to_numeric(df["Number_Of_Orders"], errors="coerce").fillna(0)
    df["Avg_No_Items"] = pd.to_numeric(df["Avg_No_Items"], errors="coerce")
    df["Avg_Bump_Time"] = pd.to_numeric(df["Avg_Bump_Time"], errors="coerce")
    df["Low_Bump"] = pd.to_numeric(df["Low_Bump"], errors="coerce")
    df["High_Bump"] = pd.to_numeric(df["High_Bump"], errors="coerce")
    df["Day_Of_Week"] = df["Day_Of_Week"].fillna("")
    df["Hour"] = pd.to_numeric(
        df["Time_Period"].astype(str).str.extract(r"(\d+):\d+")[0],
        errors="coerce"
    )
    # Convert 12-hour-looking times to a useful numeric hour where possible.
    # The source uses labels such as "8:00 - 8:14", so the extracted hour is sufficient.
    df["Hour"] = df["Hour"].fillna(0).astype(int)
    df["Month"] = df["Date"].dt.strftime("%b")
    df["Month_Num"] = df["Date"].dt.month
    df["Date_Label"] = df["Date"].dt.strftime("%b %d, %Y")
    return df.dropna(subset=["Date"])


uploaded = st.sidebar.file_uploader(
    "Upload restaurant Excel file",
    type=["xlsx"]
)

if uploaded:
    excel_file = pd.ExcelFile(uploaded)

    selected_sheet = st.sidebar.selectbox(
        "Choose data sheet",
        excel_file.sheet_names
    )

    df = load_data(uploaded, selected_sheet)

# ---------- Sidebar ----------
st.sidebar.header("Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

days = ["All"] + [d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in df["Day_Of_Week"].unique()]
selected_day = st.sidebar.selectbox("Day of week", days)

hour_values = sorted(df["Hour"].dropna().unique().tolist())
hour_options = ["All"] + [int(h) for h in hour_values]
selected_hour = st.sidebar.selectbox("Hour", hour_options)

view = st.sidebar.radio("Time resolution", ["15-minute", "Daily"])

filtered = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy()

if selected_day != "All":
    filtered = filtered[filtered["Day_Of_Week"] == selected_day]

if selected_hour != "All":
    filtered = filtered[filtered["Hour"] == selected_hour]

if filtered.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ---------- KPI calculations ----------
total_orders = filtered["Number_Of_Orders"].sum()
weighted_items = (filtered["Avg_No_Items"] * filtered["Number_Of_Orders"]).sum()
avg_items = weighted_items / total_orders if total_orders else 0
avg_bump = filtered["Avg_Bump_Time"].mean()
peak_row = filtered.groupby("Hour", as_index=False)["Number_Of_Orders"].sum().sort_values(
    "Number_Of_Orders", ascending=False
).head(1)

peak_hour = f"{int(peak_row.iloc[0]['Hour'])}:00" if not peak_row.empty else "—"

def fmt_seconds(seconds):
    if pd.isna(seconds):
        return "—"
    seconds = int(round(seconds))
    return f"{seconds // 60}m {seconds % 60:02d}s"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Orders", f"{total_orders:,.0f}")
c2.metric("Avg. Items / Order", f"{avg_items:.1f}")
c3.metric("Avg. Bump Time", fmt_seconds(avg_bump))
c4.metric("Peak Hour", peak_hour)

st.divider()

# ---------- Overview charts ----------
left, right = st.columns(2)

with left:
    daily = filtered.groupby("Date", as_index=False)["Number_Of_Orders"].sum()
    fig = px.line(
        daily,
        x="Date",
        y="Number_Of_Orders",
        markers=True,
        title="Orders Over Time",
        labels={"Date": "Date", "Number_Of_Orders": "Orders"},
    )
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

with right:
    by_hour = filtered.groupby("Hour", as_index=False)["Number_Of_Orders"].sum()
    by_hour["Hour Label"] = by_hour["Hour"].astype(str) + ":00"
    fig = px.bar(
        by_hour,
        x="Hour Label",
        y="Number_Of_Orders",
        title="Orders by Hour",
        labels={"Hour Label": "Hour", "Number_Of_Orders": "Orders"},
    )
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_day = filtered.groupby("Day_Of_Week", as_index=False)["Number_Of_Orders"].sum()
    by_day["Day_Of_Week"] = pd.Categorical(by_day["Day_Of_Week"], categories=dow_order, ordered=True)
    by_day = by_day.sort_values("Day_Of_Week")
    fig = px.bar(
        by_day,
        x="Day_Of_Week",
        y="Number_Of_Orders",
        title="Orders by Day of Week",
        labels={"Day_Of_Week": "Day", "Number_Of_Orders": "Orders"},
    )
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

with right:
    by_month = filtered.groupby(["Month_Num", "Month"], as_index=False)["Number_Of_Orders"].sum().sort_values("Month_Num")
    fig = px.bar(
        by_month,
        x="Month",
        y="Number_Of_Orders",
        title="Orders by Month",
        labels={"Month": "Month", "Number_Of_Orders": "Orders"},
    )
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Operations ----------
st.subheader("Kitchen Performance")

perf = filtered.groupby("Hour", as_index=False).agg(
    Avg_Bump_Time=("Avg_Bump_Time", "mean"),
    Orders=("Number_Of_Orders", "sum"),
)
perf["Avg Bump Time (min)"] = perf["Avg_Bump_Time"] / 60
perf["Hour Label"] = perf["Hour"].astype(str) + ":00"

fig = px.line(
    perf,
    x="Hour Label",
    y="Avg Bump Time (min)",
    markers=True,
    title="Average Bump Time by Hour",
    labels={"Hour Label": "Hour", "Avg Bump Time (min)": "Minutes"},
)
fig.update_layout(height=350, margin=dict(l=20, r=20, t=55, b=20))
st.plotly_chart(fig, use_container_width=True)

# ---------- Automatic observations ----------
st.subheader("Key Observations")

obs = []

hour_totals = filtered.groupby("Hour")["Number_Of_Orders"].sum()
if not hour_totals.empty:
    busiest_hour = int(hour_totals.idxmax())
    busiest_orders = hour_totals.max()
    share = busiest_orders / total_orders * 100 if total_orders else 0
    obs.append(f"**Peak ordering period:** {busiest_hour}:00 had the most orders ({busiest_orders:,.0f}, about {share:.1f}% of filtered orders).")

day_totals = filtered.groupby("Day_Of_Week")["Number_Of_Orders"].sum()
if not day_totals.empty:
    busiest_day = day_totals.idxmax()
    obs.append(f"**Busiest day:** {busiest_day} generated {day_totals.max():,.0f} orders in the selected period.")

if len(hour_totals) >= 2:
    slowest_hour = int(hour_totals.idxmin())
    obs.append(f"**Lowest-volume hour:** {slowest_hour}:00 had the fewest orders ({hour_totals.min():,.0f}).")

if not perf.empty:
    worst_bump = perf.loc[perf["Avg_Bump_Time"].idxmax()]
    obs.append(f"**Longest average bump time:** {int(worst_bump['Hour'])}:00 averaged {fmt_seconds(worst_bump['Avg_Bump_Time'])}.")

for x in obs:
    st.markdown("• " + x)

# ---------- Raw data ----------
with st.expander("View filtered data"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)

st.caption("Built from the workbook's 'Actually Cleaned Data' sheet. The dashboard is designed so a standardized restaurant dataset can be swapped in later.")
