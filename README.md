# Blinkit KPI Dashboard

A Streamlit dashboard for Blinkit's operational metrics, powered by Snowflake.

## Features

- **Order Performance** — Total revenue, order count, average order value, unique customers, revenue trends, and payment method distribution.
- **Delivery Performance** — On-time rate, average delivery time, distance metrics, delay reasons, and delivery status breakdown.
- **Marketing Performance** — Ad spend, revenue generated, ROAS, CTR, conversion rate, channel comparisons, and audience-level analysis.
- **Interactive Filters** — Filter by date range, delivery status, payment method, marketing channel, and target audience.
- **Detailed Data Tables** — Explore raw data for orders, delivery, and marketing.

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI framework
- [Snowflake](https://www.snowflake.com/) — Data warehouse
- [Altair](https://altair-viz.github.io/) — Charts and visualizations
- [Pandas](https://pandas.pydata.org/) — Data manipulation

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/DaraAnuj/blinkit-dashboard.git
   cd blinkit-dashboard
   ```

2. Install dependencies:
   ```bash
   pip install streamlit snowflake-connector-python pandas altair
   ```

3. Configure your Snowflake connection in `.streamlit/secrets.toml`:
   ```toml
   [connections.snowflake]
   account = "<your_account>"
   user = "<your_user>"
   password = "<your_password>"
   database = "BLINKIT_DW"
   schema = "RAW"
   ```

4. Run the dashboard:
   ```bash
   streamlit run streamlit_app.py
   ```

## Data Sources

The dashboard reads from three tables in `BLINKIT_DW.RAW`:

| Table | Description |
|-------|-------------|
| `BLINKIT_ORDERS` | Order details including revenue, status, and payment method |
| `BLINKIT_DELIVERY_PERFORMANCE` | Delivery times, distances, statuses, and delay reasons |
| `BLINKIT_MARKETING_PERFORMANCE` | Campaign metrics including spend, impressions, clicks, and ROAS |
