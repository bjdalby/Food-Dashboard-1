
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

# ---------- Data loading & automatic detection ----------

def find_column(df, keywords):
    """Find the most likely column based on its name."""
    columns = list(df.columns)

    # Exact matches first
    for keyword in keywords:
        for column in columns:
            if str(column).strip().lower() == keyword.lower():
                return column

    # Partial matches
    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).strip().lower():
                return column

    return None


def detect_columns(df):
    """Automatically identify common restaurant data columns."""

    return {
        "date": find_column(
            df,
            [
                "date",
                "order date",
                "business date",
                "transaction date",
                "order_date",
                "business_date",
            ],
        ),

        "time": find_column(
            df,
            [
                "time",
                "order time",
                "transaction time",
                "order_time",
                "transaction_time",
                "time period",
                "time_period",
            ],
        ),

        "orders": find_column(
            df,
            [
                "orders",
                "number of orders",
                "number_of_orders",
                "order count",
                "order_count",
                "transactions",
                "transaction count",
                "total orders",
                "total_orders",
            ],
        ),

        "items": find_column(
            df,
            [
                "items",
                "items per order",
                "avg items",
                "average items",
                "avg_no_items",
                "average items per order",
            ],
        ),

        "bump": find_column(
            df,
            [
                "bump time",
                "bump_time",
                "avg bump time",
                "average bump time",
                "avg_bump_time",
                "kitchen time",
                "prep time",
                "preparation time",
            ],
        ),
    }


def prepare_data(df, detected):
    """Convert different restaurant formats into the dashboard format."""

    data = df.copy()

    # ---------- Date ----------

    date_col = detected["date"]

    if date_col is None:
        for column in data.columns:
            converted = pd.to_datetime(
                data[column],
                errors="coerce"
            )

            if converted.notna().mean() >= 0.70:
                date_col = column
                detected["date"] = column
                break

    if date_col is None:
        return None, "I couldn't identify a date column."

    date_values = pd.to_datetime(
        data[date_col],
        errors="coerce"
    )

    # ---------- Time ----------

    time_col = detected["time"]

    if time_col is not None:

        time_values = pd.to_datetime(
            data[time_col],
            errors="coerce"
        )

        if time_values.notna().mean() >= 0.70:

            # Time column contains full datetime values
            if time_values.dt.hour.notna().any():
                date_values = date_values.fillna(
                    time_values.dt.normalize()
                )

                hour_values = time_values.dt.hour

            else:
                hour_values = pd.Series(
                    index=data.index,
                    dtype="float64"
                )

        else:

            # Try extracting the hour from values such as:
            # 8:00 - 8:14
            # 14:30
            # 2:30 PM

            hour_values = pd.to_numeric(
                data[time_col]
                .astype(str)
                .str.extract(r"(\d{1,2})[:.]")[0],
                errors="coerce"
            )

    else:

        # The date column may contain both date and time.
        combined_values = pd.to_datetime(
            data[date_col],
            errors="coerce"
        )

        hour_values = combined_values.dt.hour

    # ---------- Orders ----------

    orders_col = detected["orders"]

    if orders_col is not None:

        data["Number_Of_Orders"] = pd.to_numeric(
            data[orders_col],
            errors="coerce"
        ).fillna(0)

    else:

        # If each row represents one order,
        # treat each row as one order.
        data["Number_Of_Orders"] = 1

    # ---------- Items ----------

    items_col = detected["items"]

    if items_col is not None:

        data["Avg_No_Items"] = pd.to_numeric(
            data[items_col],
            errors="coerce"
        )

    else:

        data["Avg_No_Items"] = pd.NA

    # ---------- Bump time ----------

    bump_col = detected["bump"]

    if bump_col is not None:

        data["Avg_Bump_Time"] = pd.to_numeric(
            data[bump_col],
            errors="coerce"
        )

    else:

        data["Avg_Bump_Time"] = pd.NA

    # ---------- Standard dashboard columns ----------

    data["Date"] = date_values

    data["Hour"] = pd.to_numeric(
        hour_values,
        errors="coerce"
    )

    data["Hour"] = data["Hour"].fillna(0).astype(int)

    data["Day_Of_Week"] = (
        data["Date"]
        .dt.day_name()
        .str[:3]
    )

    data["Month"] = (
        data["Date"]
        .dt.strftime("%b")
    )

    data["Month_Num"] = (
        data["Date"]
        .dt.month
    )

    data["Date_Label"] = (
        data["Date"]
        .dt.strftime("%b %d, %Y")
    )

    data = data.dropna(
        subset=["Date"]
    )

    return data, None


# ---------- Upload Excel file ----------

uploaded = st.sidebar.file_uploader(
    "Upload restaurant Excel file",
    type=["xlsx"]
)

if uploaded is None:
    st.info(
        "Upload the Excel workbook in the sidebar to begin."
    )
    st.stop()


# ---------- Choose Excel sheet ----------

excel_file = pd.ExcelFile(uploaded)

selected_sheet = st.sidebar.selectbox(
    "Choose data sheet",
    excel_file.sheet_names
)


# ---------- Read raw data ----------

raw_df = pd.read_excel(
    uploaded,
    sheet_name=selected_sheet
)


# ---------- Automatically detect columns ----------

detected = detect_columns(raw_df)

# ---------- Data Mapping ----------

st.sidebar.subheader("🔧 Data Mapping")

available_columns = [
    "— Not available —"
] + list(raw_df.columns)


def mapping_dropdown(label, detected_column):
    if detected_column in available_columns:
        default_index = available_columns.index(detected_column)
    else:
        default_index = 0

    return st.sidebar.selectbox(
        label,
        available_columns,
        index=default_index
    )


date_column = mapping_dropdown(
    "📅 Date",
    detected["date"]
)

time_column = mapping_dropdown(
    "🕐 Time",
    detected["time"]
)

orders_column = mapping_dropdown(
    "📦 Orders",
    detected["orders"]
)

items_column = mapping_dropdown(
    "🛍️ Items per Order",
    detected["items"]
)

bump_column = mapping_dropdown(
    "⏱️ Bump Time",
    detected["bump"]
)


# ---------- Prepare standardized data ----------

selected_columns = {
    "date": None if date_column == "— Not available —" else date_column,
    "time": None if time_column == "— Not available —" else time_column,
    "orders": None if orders_column == "— Not available —" else orders_column,
    "items": None if items_column == "— Not available —" else items_column,
    "bump": None if bump_column == "— Not available —" else bump_column,
}

df, data_error = prepare_data(
    raw_df,
    selected_columns
)

if data_error:

    st.error(data_error)

    st.write(
        "Columns found in this sheet:"
    )

    st.write(
        list(raw_df.columns)
    )

    st.stop()


# ---------- Data quality ----------

st.sidebar.subheader("Data Check")

st.sidebar.success(
    f"✓ {len(df):,} usable rows"
)

invalid_dates = len(raw_df) - len(df)

if invalid_dates > 0:

    st.sidebar.warning(
        f"⚠ {invalid_dates:,} rows have invalid or missing dates."
    )


# ---------- Outlier detection ----------

df["Is_Bump_Outlier"] = False

if df["Avg_Bump_Time"].notna().sum() >= 5:

    q1 = df["Avg_Bump_Time"].quantile(0.25)
    q3 = df["Avg_Bump_Time"].quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    df["Is_Bump_Outlier"] = (
        (df["Avg_Bump_Time"] < lower_bound) |
        (df["Avg_Bump_Time"] > upper_bound)
    )

outlier_count = int(
    df["Is_Bump_Outlier"].sum()
)

if outlier_count > 0:

    st.sidebar.warning(
        f"⚠ {outlier_count:,} potential bump-time outliers"
    )

    include_outliers = st.sidebar.checkbox(
        "Include potential outliers",
        value=True
    )

    if not include_outliers:

        df = df[
            ~df["Is_Bump_Outlier"]
        ].copy()

else:

    st.sidebar.success(
        "✓ No obvious bump-time outliers"
    )


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
