"""Interactive dashboard for the marketing campaign analytics project."""

import pandas as pd
import pymysql
import streamlit as st

from database import fetch_campaign_data

st.set_page_config(page_title="Marketing campaign analytics", page_icon=":material/insights:", layout="wide")


@st.cache_data(ttl=60, max_entries=1, show_spinner="Loading customer data...")
def load_data() -> pd.DataFrame:
    """Fetch SQL records and restore the EDA's dashboard-only fields."""
    data = fetch_campaign_data()
    if data.empty:
        return data
    required = {"Age_At_Reference_Year", "Income", "Total_Spend", "Total_Purchases", "Response"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError("Missing dashboard columns: " + ", ".join(sorted(missing)))

    data["Age_Band"] = pd.cut(
        data["Age_At_Reference_Year"],
        bins=[0, 29, 39, 49, 59, 120],
        labels=["Under 30", "30-39", "40-49", "50-59", "60+"],
    )
    data["Income_Band"] = pd.cut(
        data["Income"],
        bins=[-float("inf"), 25000, 50000, 75000, float("inf")],
        labels=["Up to 25k", "25k-50k", "50k-75k", "75k+"],
    )
    # Compute EDA thresholds over the full table, before applying UI filters.
    high_spend = data["Total_Spend"].ge(data["Total_Spend"].median())
    frequent_purchases = data["Total_Purchases"].ge(data["Total_Purchases"].median())
    data["Customer_Segment"] = "Lower activity customers"
    data.loc[frequent_purchases, "Customer_Segment"] = "Frequent purchasers"
    data.loc[high_spend, "Customer_Segment"] = "High-value non-responders"
    data.loc[high_spend & data["Response"].eq(1), "Customer_Segment"] = "High-value responders"
    return data


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    """Apply dashboard filters without changing the cached source data."""
    with st.sidebar:
        st.header("Filters")
        filtered = data.copy()
        for column in ["Country", "Education", "Marital_Status", "Age_Band", "Income_Band"]:
            if column in filtered:
                options = sorted(filtered[column].dropna().astype(str).unique())
                selected = st.multiselect(column.replace("_", " "), options, default=options)
                filtered = filtered[filtered[column].astype(str).isin(selected)]
        if "Response" in filtered:
            response_choice = st.segmented_control(
                "Campaign response", ["All", "Responded", "Did not respond"], default="All"
            )
            if response_choice == "Responded":
                filtered = filtered[filtered["Response"] == 1]
            elif response_choice == "Did not respond":
                filtered = filtered[filtered["Response"] == 0]
    return filtered


st.title("Marketing campaign analytics")
st.caption("Explore customer spending, channel behaviour, campaign response, and rule-based customer segments.")
st.sidebar.button("Refresh data", on_click=load_data.clear, icon=":material/refresh:")
st.sidebar.caption("Loaded from MySQL. Refresh to fetch the latest customer records.")
try:
    raw_dashboard_data = load_data()
except pymysql.MySQLError as error:
    if error.args and error.args[0] == 1146:
        st.error("The customer table is missing. Run the EDA database-loading step first.")
    else:
        st.error("Unable to load customer data from MySQL. Check the database settings in .env and ensure MySQL is running.")
    st.stop()
except ValueError:
    st.error("The database settings or customer table columns are invalid. Check .env and load the table using database.py.")
    st.stop()

if raw_dashboard_data.empty:
    st.info("The customer table is empty. Run the EDA database-loading step, then select Refresh data.")
    st.stop()

data = apply_filters(raw_dashboard_data)

if data.empty:
    st.warning("No customers match the selected filters. Choose at least one value in a filter.")
    st.stop()

response_rate = data["Response"].mean() if "Response" in data else float("nan")
with st.container(horizontal=True):
    st.metric("Customers", f"{len(data):,}", border=True)
    st.metric("Campaign response rate", f"{response_rate:.1%}", border=True)
    st.metric("Average total spend", f"{data['Total_Spend'].mean():,.0f}", border=True)
    st.metric("Average purchases", f"{data['Total_Purchases'].mean():,.1f}", border=True)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Campaign response by customer segment")
        if "Customer_Segment" in data:
            segment_response = data.groupby("Customer_Segment", observed=True)["Response"].mean().sort_values(ascending=False)
            st.bar_chart(segment_response, x_label="Customer segment", y_label="Response rate")
            st.caption("Takeaway: compare response rate with segment size before prioritising a campaign audience.")
with right:
    with st.container(border=True):
        st.subheader("Spending by product")
        product_columns = [column for column in ["MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts", "MntSweetProducts", "MntGoldProds"] if column in data]
        product_spend = data[product_columns].sum().sort_values(ascending=False)
        st.bar_chart(product_spend, x_label="Product category", y_label="Total spend")
        st.caption("Takeaway: product categories with the highest total spend are natural cross-sell candidates.")

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Income and customer spending")
        if {"Income", "Total_Spend"}.issubset(data.columns):
            scatter_data = data[["Income", "Total_Spend", "Response"]].dropna()
            st.scatter_chart(scatter_data, x="Income", y="Total_Spend", color="Response")
            st.caption("Takeaway: inspect whether higher-income customers also appear among higher spenders.")
with right:
    with st.container(border=True):
        st.subheader("Channel purchases by response")
        channel_columns = [column for column in ["NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases", "NumDealsPurchases"] if column in data]
        if channel_columns and "Response" in data:
            channel_summary = data.groupby("Response")[channel_columns].mean().T
            channel_summary.columns = ["Did not respond", "Responded"] if set(channel_summary.columns) == {0, 1} else channel_summary.columns
            st.bar_chart(channel_summary, x_label="Purchase channel", y_label="Average purchases")
            st.caption("Takeaway: compare channel use between responders and non-responders to plan outreach.")

with st.container(border=True):
    st.subheader("Under-served web audience")
    required = {"NumWebVisitsMonth", "Response", "Total_Spend", "Country"}
    if required.issubset(data.columns):
        underserved = (
            data[(data["NumWebVisitsMonth"] > 5) & (data["Response"] == 0)]
            .groupby("Country", dropna=False)
            .agg(customers=("Response", "size"), average_spend=("Total_Spend", "mean"), average_web_visits=("NumWebVisitsMonth", "mean"))
            .sort_values("customers", ascending=False)
            .reset_index()
        )
        st.dataframe(underserved, hide_index=True)
        st.caption("Takeaway: frequent web visitors who did not respond are a candidate group for offer or website-journey testing.")

with st.expander("View filtered customer data"):
    st.dataframe(data, hide_index=True, height=360)

st.download_button(
    "Download filtered customers as CSV",
    data.to_csv(index=False).encode("utf-8"),
    file_name="filtered_marketing_customers.csv",
    mime="text/csv",
)
