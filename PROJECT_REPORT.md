# Marketing campaign analytics report

## Problem

The business needs to understand customer spending, channel behaviour, campaign acceptance, and priority audiences for future campaigns.

## Data and method

The project analyses 56,000 customer records from `marketing_campaign_data.csv`. The workflow preserves the original data as `raw` and creates a working copy, `df`, for cleaning and analysis.

Cleaning checks include missing-value counts, duplicate rows, missing or repeated IDs, whitespace cleanup, category-label standardisation, numeric and date conversion, invalid-value reporting, and IQR outlier flags. No records are silently deleted and no missing values are imputed without a documented business decision.

## Feature engineering

The analysis derives:

- `Age_At_Reference_Year` and `Customer_Tenure_Days`, using the latest valid customer date as the reference date.
- `Total_Spend`, `Total_Purchases`, and `Children`.
- `Age_Band` and `Income_Band` for reporting filters.
- Transparent rule-based flags: high income, young customer, high web engagement, family customer, and high spender.
- `Customer_Segment`, combining spending, purchasing, and campaign response.

## Verified findings

- The dataset contains 56,000 records, no missing cells after conversion, and no complete duplicate rows.
- Overall latest-campaign response rate is **14.76%**.
- `MntMeatProducts` is the highest total-spend product category, with **15,024,465** total monetary units.
- Australia has the highest latest-campaign response rate at **20.19%**.
- The largest derived segment is **High-value non-responders** (21,972 customers), followed by **Lower activity customers** (19,475 customers).
- There are 6,028 high-value responders and 8,525 frequent purchasers.

## Recommendations

1. Review high-value non-responders first. They already spend substantially but did not accept the latest campaign, so targeted offers or different channels may improve conversion.
2. Use the product-spend chart to package high-spend categories with complementary products, beginning with meat products.
3. Compare web, store, catalog, and deal purchases for responders and non-responders before choosing a campaign channel.
4. Test campaigns by country and income band, using sufficient group sizes before acting on a higher response rate.
5. Investigate frequent website visitors who do not respond. They may need better website offers, timing, or message relevance.
6. Keep IQR outliers for review instead of removing them automatically, because they can represent valuable customers.

## Reproducibility

1. Run `python marketing_campaign_eda.py` to regenerate the cleaned CSV and load the SQL table.
2. Run the statements in `analytics_queries.sql` to create the view and KPI summaries.
3. Run `streamlit run app.py` to open the interactive dashboard.
