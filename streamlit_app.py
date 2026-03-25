"""
Blinkit KPI Dashboard

A comprehensive dashboard for Blinkit's operational metrics covering:
- Order performance (revenue, order count, AOV)
- Delivery performance (on-time %, avg delivery time, delay reasons)
- Marketing performance (ROAS, conversions, spend efficiency)
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="Blinkit KPI Dashboard",
    page_icon=":material/shopping_cart:",
    layout="wide",
)


# =============================================================================
# Snowflake Connection
# =============================================================================


def get_connection():
    try:
        return st.connection("snowflake")
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        st.info(
            "Configure your connection in `.streamlit/secrets.toml` "
            "or via environment variables."
        )
        st.stop()


# =============================================================================
# Data Loading
# =============================================================================


@st.cache_data(ttl=600, show_spinner="Loading orders...")
def load_orders() -> pd.DataFrame:
    conn = get_connection()
    df = conn.query("""
        SELECT
            ORDER_ID,
            CUSTOMER_ID,
            ORDER_DATE,
            DELIVERY_STATUS,
            ORDER_TOTAL,
            PAYMENT_METHOD,
            STORE_ID
        FROM BLINKIT_DW.RAW.BLINKIT_ORDERS
    """)
    df.columns = df.columns.str.lower()
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@st.cache_data(ttl=600, show_spinner="Loading delivery data...")
def load_delivery() -> pd.DataFrame:
    conn = get_connection()
    df = conn.query("""
        SELECT
            d.ORDER_ID,
            d.DELIVERY_PARTNER_ID,
            d.DELIVERY_TIME_MINUTES,
            d.DISTANCE_KM,
            d.DELIVERY_STATUS,
            d.REASONS_IF_DELAYED,
            o.ORDER_DATE
        FROM BLINKIT_DW.RAW.BLINKIT_DELIVERY_PERFORMANCE d
        JOIN BLINKIT_DW.RAW.BLINKIT_ORDERS o ON d.ORDER_ID = o.ORDER_ID
    """)
    df.columns = df.columns.str.lower()
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@st.cache_data(ttl=600, show_spinner="Loading marketing data...")
def load_marketing() -> pd.DataFrame:
    conn = get_connection()
    df = conn.query("""
        SELECT
            CAMPAIGN_ID,
            CAMPAIGN_NAME,
            DATE,
            TARGET_AUDIENCE,
            CHANNEL,
            IMPRESSIONS,
            CLICKS,
            CONVERSIONS,
            SPEND,
            REVENUE_GENERATED,
            ROAS
        FROM BLINKIT_DW.RAW.BLINKIT_MARKETING_PERFORMANCE
    """)
    df.columns = df.columns.str.lower()
    df["date"] = pd.to_datetime(df["date"])
    return df


# =============================================================================
# Filtering
# =============================================================================


def apply_date_filter(df: pd.DataFrame, date_col: str, start: date, end: date) -> pd.DataFrame:
    mask = (df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)
    return df[mask]


# =============================================================================
# Load Data
# =============================================================================

orders_raw = load_orders()
delivery_raw = load_delivery()
marketing_raw = load_marketing()


# =============================================================================
# Sidebar Filters
# =============================================================================

with st.sidebar:
    st.header(":material/filter_list: Filters")

    # Date range
    min_date = orders_raw["order_date"].min().date()
    max_date = orders_raw["order_date"].max().date()
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    st.divider()

    # Order filters
    st.subheader("Order Filters")
    all_statuses = sorted(orders_raw["delivery_status"].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "Delivery Status",
        options=all_statuses,
        default=all_statuses,
    )

    all_payments = sorted(orders_raw["payment_method"].dropna().unique().tolist())
    selected_payments = st.multiselect(
        "Payment Method",
        options=all_payments,
        default=all_payments,
    )

    st.divider()

    # Marketing filters
    st.subheader("Marketing Filters")
    all_channels = sorted(marketing_raw["channel"].dropna().unique().tolist())
    selected_channels = st.multiselect(
        "Channel",
        options=all_channels,
        default=all_channels,
    )

    all_audiences = sorted(marketing_raw["target_audience"].dropna().unique().tolist())
    selected_audiences = st.multiselect(
        "Target Audience",
        options=all_audiences,
        default=all_audiences,
    )

    st.divider()
    if st.button(":material/restart_alt: Reset Filters", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# =============================================================================
# Apply Filters
# =============================================================================

orders = apply_date_filter(orders_raw, "order_date", start_date, end_date)
orders = orders[orders["delivery_status"].isin(selected_statuses)]
orders = orders[orders["payment_method"].isin(selected_payments)]

delivery = apply_date_filter(delivery_raw, "order_date", start_date, end_date)
delivery = delivery[delivery["delivery_status"].isin(selected_statuses)]

marketing = apply_date_filter(marketing_raw, "date", start_date, end_date)
marketing = marketing[marketing["channel"].isin(selected_channels)]
marketing = marketing[marketing["target_audience"].isin(selected_audiences)]


# =============================================================================
# Page Header
# =============================================================================

st.markdown("# :material/shopping_cart: Blinkit KPI Dashboard")
st.caption(
    f"Data from **{start_date.strftime('%b %d, %Y')}** to "
    f"**{end_date.strftime('%b %d, %Y')}** | "
    f"**{len(orders):,}** orders in view"
)


# =============================================================================
# KPI Row - Orders
# =============================================================================

st.markdown("### :material/receipt_long: Order Performance")

total_revenue = orders["order_total"].sum()
total_orders = len(orders)
avg_order_value = orders["order_total"].mean() if total_orders > 0 else 0
unique_customers = orders["customer_id"].nunique()

# Sparkline data: daily revenue
daily_rev = (
    orders.groupby(orders["order_date"].dt.date)["order_total"]
    .sum()
    .sort_index()
    .tolist()
)
daily_orders = (
    orders.groupby(orders["order_date"].dt.date)["order_id"]
    .count()
    .sort_index()
    .tolist()
)

with st.container(horizontal=True):
    st.metric(
        "Total Revenue",
        f"${total_revenue:,.0f}",
        border=True,
        chart_data=daily_rev[-30:] if daily_rev else None,
        chart_type="area",
    )
    st.metric(
        "Total Orders",
        f"{total_orders:,}",
        border=True,
        chart_data=daily_orders[-30:] if daily_orders else None,
        chart_type="bar",
    )
    st.metric(
        "Avg Order Value",
        f"${avg_order_value:,.2f}",
        border=True,
    )
    st.metric(
        "Unique Customers",
        f"{unique_customers:,}",
        border=True,
    )


# =============================================================================
# Order Charts Row
# =============================================================================

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("**Revenue Over Time**")
        if not orders.empty:
            rev_by_month = (
                orders.assign(month=orders["order_date"].dt.to_period("M").dt.to_timestamp())
                .groupby("month")["order_total"]
                .sum()
                .reset_index()
            )
            chart = (
                alt.Chart(rev_by_month)
                .mark_area(opacity=0.6, line=True, color="#4A90D9")
                .encode(
                    x=alt.X("month:T", title=None),
                    y=alt.Y("order_total:Q", title="Revenue ($)"),
                    tooltip=[
                        alt.Tooltip("month:T", title="Month", format="%b %Y"),
                        alt.Tooltip("order_total:Q", title="Revenue", format="$,.0f"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data for selected filters.")

with col2:
    with st.container(border=True):
        st.markdown("**Orders by Payment Method**")
        if not orders.empty:
            pay_dist = orders["payment_method"].value_counts().reset_index()
            pay_dist.columns = ["payment_method", "count"]
            chart = (
                alt.Chart(pay_dist)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color("payment_method:N", title="Payment Method"),
                    tooltip=[
                        alt.Tooltip("payment_method:N", title="Method"),
                        alt.Tooltip("count:Q", title="Orders", format=","),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data for selected filters.")


# =============================================================================
# KPI Row - Delivery
# =============================================================================

st.markdown("### :material/local_shipping: Delivery Performance")

on_time_count = len(delivery[delivery["delivery_status"] == "On Time"])
delayed_count = len(delivery[delivery["delivery_status"] == "Delayed"])
cancelled_count = len(delivery[delivery["delivery_status"] == "Cancelled"])
total_deliveries = len(delivery)
on_time_pct = (on_time_count / total_deliveries * 100) if total_deliveries > 0 else 0
avg_delivery_time = delivery["delivery_time_minutes"].mean() if total_deliveries > 0 else 0
avg_distance = delivery["distance_km"].mean() if total_deliveries > 0 else 0

with st.container(horizontal=True):
    st.metric(
        "On-Time Rate",
        f"{on_time_pct:.1f}%",
        border=True,
    )
    st.metric(
        "Avg Delivery Time",
        f"{avg_delivery_time:.1f} min",
        border=True,
    )
    st.metric(
        "Avg Distance",
        f"{avg_distance:.1f} km",
        border=True,
    )
    st.metric(
        "Delayed Orders",
        f"{delayed_count:,}",
        border=True,
    )
    st.metric(
        "Cancelled Orders",
        f"{cancelled_count:,}",
        border=True,
    )


# =============================================================================
# Delivery Charts Row
# =============================================================================

col3, col4 = st.columns(2)

with col3:
    with st.container(border=True):
        st.markdown("**Delivery Status Distribution**")
        if not delivery.empty:
            status_dist = delivery["delivery_status"].value_counts().reset_index()
            status_dist.columns = ["delivery_status", "count"]
            color_scale = alt.Scale(
                domain=["On Time", "Delayed", "Cancelled"],
                range=["#2ecc71", "#f39c12", "#e74c3c"],
            )
            chart = (
                alt.Chart(status_dist)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("delivery_status:N", title=None, sort="-y"),
                    y=alt.Y("count:Q", title="Orders"),
                    color=alt.Color("delivery_status:N", scale=color_scale, title=None, legend=None),
                    tooltip=[
                        alt.Tooltip("delivery_status:N", title="Status"),
                        alt.Tooltip("count:Q", title="Orders", format=","),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data for selected filters.")

with col4:
    with st.container(border=True):
        st.markdown("**Top Delay Reasons**")
        delayed = delivery[delivery["reasons_if_delayed"].notna()]
        if not delayed.empty:
            reasons = delayed["reasons_if_delayed"].value_counts().head(6).reset_index()
            reasons.columns = ["reason", "count"]
            chart = (
                alt.Chart(reasons)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#f39c12")
                .encode(
                    x=alt.X("count:Q", title="Count"),
                    y=alt.Y("reason:N", title=None, sort="-x"),
                    tooltip=[
                        alt.Tooltip("reason:N", title="Reason"),
                        alt.Tooltip("count:Q", title="Count", format=","),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No delayed orders in selected filters.")


# =============================================================================
# KPI Row - Marketing
# =============================================================================

st.markdown("### :material/campaign: Marketing Performance")

total_spend = marketing["spend"].sum()
total_mkt_revenue = marketing["revenue_generated"].sum()
total_impressions = marketing["impressions"].sum()
total_clicks = marketing["clicks"].sum()
total_conversions = marketing["conversions"].sum()
avg_roas = (total_mkt_revenue / total_spend) if total_spend > 0 else 0
ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
conv_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

with st.container(horizontal=True):
    st.metric("Ad Spend", f"${total_spend:,.0f}", border=True)
    st.metric("Revenue Generated", f"${total_mkt_revenue:,.0f}", border=True)
    st.metric("ROAS", f"{avg_roas:.2f}x", border=True)
    st.metric("CTR", f"{ctr:.2f}%", border=True)
    st.metric("Conversion Rate", f"{conv_rate:.2f}%", border=True)


# =============================================================================
# Marketing Charts Row
# =============================================================================

col5, col6 = st.columns(2)

with col5:
    with st.container(border=True):
        st.markdown("**Spend vs Revenue by Channel**")
        if not marketing.empty:
            channel_perf = (
                marketing.groupby("channel")[["spend", "revenue_generated"]]
                .sum()
                .reset_index()
            )
            melted = channel_perf.melt(
                id_vars=["channel"],
                value_vars=["spend", "revenue_generated"],
                var_name="metric",
                value_name="amount",
            )
            melted["metric"] = melted["metric"].map(
                {"spend": "Spend", "revenue_generated": "Revenue"}
            )
            chart = (
                alt.Chart(melted)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("channel:N", title=None),
                    y=alt.Y("amount:Q", title="Amount ($)"),
                    color=alt.Color("metric:N", title=None),
                    xOffset="metric:N",
                    tooltip=[
                        alt.Tooltip("channel:N", title="Channel"),
                        alt.Tooltip("metric:N", title="Metric"),
                        alt.Tooltip("amount:Q", title="Amount", format="$,.0f"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data for selected filters.")

with col6:
    with st.container(border=True):
        st.markdown("**ROAS by Target Audience**")
        if not marketing.empty:
            audience_roas = (
                marketing.groupby("target_audience")
                .agg(total_spend=("spend", "sum"), total_rev=("revenue_generated", "sum"))
                .reset_index()
            )
            audience_roas["roas"] = audience_roas["total_rev"] / audience_roas["total_spend"].replace(0, 1)
            chart = (
                alt.Chart(audience_roas)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#8e44ad")
                .encode(
                    x=alt.X("target_audience:N", title=None),
                    y=alt.Y("roas:Q", title="ROAS"),
                    tooltip=[
                        alt.Tooltip("target_audience:N", title="Audience"),
                        alt.Tooltip("roas:Q", title="ROAS", format=".2f"),
                        alt.Tooltip("total_spend:Q", title="Spend", format="$,.0f"),
                        alt.Tooltip("total_rev:Q", title="Revenue", format="$,.0f"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data for selected filters.")


# =============================================================================
# Marketing Trend
# =============================================================================

with st.container(border=True):
    st.markdown("**Marketing Spend & Revenue Trend**")
    if not marketing.empty:
        mkt_monthly = (
            marketing.assign(month=marketing["date"].dt.to_period("M").dt.to_timestamp())
            .groupby("month")[["spend", "revenue_generated"]]
            .sum()
            .reset_index()
        )
        melted = mkt_monthly.melt(
            id_vars=["month"],
            value_vars=["spend", "revenue_generated"],
            var_name="metric",
            value_name="amount",
        )
        melted["metric"] = melted["metric"].map(
            {"spend": "Spend", "revenue_generated": "Revenue"}
        )
        chart = (
            alt.Chart(melted)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:T", title=None),
                y=alt.Y("amount:Q", title="Amount ($)"),
                color=alt.Color("metric:N", title=None),
                tooltip=[
                    alt.Tooltip("month:T", title="Month", format="%b %Y"),
                    alt.Tooltip("metric:N", title="Metric"),
                    alt.Tooltip("amount:Q", title="Amount", format="$,.0f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No data for selected filters.")


# =============================================================================
# Detailed Data Tables
# =============================================================================

st.markdown("### :material/table_chart: Detailed Data")

tab1, tab2, tab3 = st.tabs(["Orders", "Delivery", "Marketing"])

with tab1:
    st.dataframe(
        orders,
        column_config={
            "order_total": st.column_config.NumberColumn("Order Total", format="$%.2f"),
            "order_date": st.column_config.DatetimeColumn("Order Date", format="MMM DD, YYYY HH:mm"),
        },
        hide_index=True,
        use_container_width=True,
    )

with tab2:
    st.dataframe(
        delivery,
        column_config={
            "delivery_time_minutes": st.column_config.NumberColumn("Delivery Time (min)", format="%.1f"),
            "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.1f"),
            "order_date": st.column_config.DatetimeColumn("Order Date", format="MMM DD, YYYY HH:mm"),
        },
        hide_index=True,
        use_container_width=True,
    )

with tab3:
    st.dataframe(
        marketing,
        column_config={
            "spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
            "revenue_generated": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "roas": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "date": st.column_config.DatetimeColumn("Date", format="MMM DD, YYYY"),
        },
        hide_index=True,
        use_container_width=True,
    )
