# Marketing Campaign Analytics

This project analyses customer demographics, spending, purchase channels, and campaign response. It includes a guided EDA workflow, a MySQL load, reusable SQL KPI queries, a Streamlit dashboard, and a project report.

## Files

- `marketing_campaign_eda.py` - notebook-style loading, cleaning, feature engineering, EDA, rule-based segmentation, CSV export, and MySQL load.
- `database.py` - creates and loads the MySQL customer table and provides the dashboard read query.
- `analytics_queries.sql` - dashboard view and analytical KPI queries.
- `app.py` - interactive Streamlit dashboard backed by MySQL, with filters and CSV download.
- `PROJECT_REPORT.md` - findings and data-backed recommendations.
- `marketing_campaign_data_cleaned.csv` - cleaned EDA export with analysis-only bands and segment columns.

 Run dashboard: `streamlit run app.py`

## Setup

```powershell
python -m pip install -r requirements.txt
```

Configure `.env` with the local MySQL details:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=marketing_campaign_analytics
```

## Run the EDA and database load

```powershell
python marketing_campaign_eda.py
```

The script keeps `raw` unchanged, uses `df` as a working copy, reports quality issues, creates derived columns, performs EDA and segmentation, exports the cleaned CSV, and writes the SQL-table fields to MySQL.

## Run SQL analysis

Run `analytics_queries.sql` in phpMyAdmin or a MySQL client after the Python load. It creates `vw_customer_segments` and provides KPI, country/income, high-value, and under-served audience queries.

## Run dashboard

The dashboard reads `marketing_campaign_data` from MySQL using the existing `.env` settings in `config.py`. Start MySQL and load the table through the EDA script or notebook database-loading step before opening the app. The cleaned CSV is not required to run the dashboard.

```powershell
streamlit run app.py
```

The dashboard includes filters for Country, Education, Marital Status, Age Band, Income Band, and campaign response. It shows KPI cards, segment response, product spend, income-versus-spend, purchase-channel behaviour, under-served web audiences, a filtered data table, and a CSV download.

Dashboard queries are cached for 60 seconds; an interaction after expiry fetches fresh data. Use **Refresh data** to reload immediately. Age/income bands and customer segments are calculated from SQL records using the EDA rules before filters are applied.
