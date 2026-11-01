"""Simple database functions for the marketing campaign EDA project."""

import pandas as pd
import pymysql

from config import database_settings


def create_customer_table(cursor):
    """Create the table once. ID is the primary key, so duplicate customers are blocked."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS marketing_campaign_data (
            ID BIGINT PRIMARY KEY,
            Year_Birth SMALLINT NOT NULL,
            Education VARCHAR(50) NOT NULL,
            Marital_Status VARCHAR(50) NOT NULL,
            Income DECIMAL(14,2) NULL,
            Kidhome TINYINT NOT NULL,
            Teenhome TINYINT NOT NULL,
            Dt_Customer DATE NOT NULL,
            Recency TINYINT NOT NULL,
            MntWines BIGINT NOT NULL,
            MntFruits BIGINT NOT NULL,
            MntMeatProducts BIGINT NOT NULL,
            MntFishProducts BIGINT NOT NULL,
            MntSweetProducts BIGINT NOT NULL,
            MntGoldProds BIGINT NOT NULL,
            NumDealsPurchases TINYINT NOT NULL,
            NumWebPurchases TINYINT NOT NULL,
            NumCatalogPurchases TINYINT NOT NULL,
            NumStorePurchases TINYINT NOT NULL,
            NumWebVisitsMonth TINYINT NOT NULL,
            AcceptedCmp3 TINYINT NOT NULL,
            AcceptedCmp4 TINYINT NOT NULL,
            AcceptedCmp5 TINYINT NOT NULL,
            AcceptedCmp1 TINYINT NOT NULL,
            AcceptedCmp2 TINYINT NOT NULL,
            Response TINYINT NOT NULL,
            Complain TINYINT NOT NULL,
            Country VARCHAR(100) NOT NULL,
            Reference_Date DATE NOT NULL,
            Age_At_Reference_Year SMALLINT NOT NULL,
            Customer_Tenure_Days INT NOT NULL,
            Total_Spend BIGINT NOT NULL,
            Total_Purchases INT NOT NULL,
            Children TINYINT NOT NULL,
            Previous_Campaigns_Accepted TINYINT NOT NULL,
            Any_Campaign_Accepted TINYINT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def fetch_campaign_data() -> pd.DataFrame:
    """Read the customer table using the existing .env database configuration."""
    connection = pymysql.connect(**database_settings())
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM marketing_campaign_data")
            columns = [column[0] for column in cursor.description]
            records = cursor.fetchall()
    finally:
        connection.close()

    data = pd.DataFrame.from_records(records, columns=columns)
    # MySQL DECIMAL and DATE values need pandas types for charts and filters.
    if "Income" in data:
        data["Income"] = pd.to_numeric(data["Income"], errors="coerce")
    for column in ["Dt_Customer", "Reference_Date"]:
        if column in data:
            data[column] = pd.to_datetime(data[column], errors="coerce")
    return data


def store_cleaned_data(cleaned_data):
    """Store cleaned data. Existing IDs are skipped so reruns do not add duplicates."""
    database = database_settings()
    data_to_store = cleaned_data.copy()
    data_to_store["ID"] = data_to_store["ID"].astype(int)
    for column in ["Dt_Customer", "Reference_Date"]:
        data_to_store[column] = pd.to_datetime(data_to_store[column]).dt.date

    # The EDA file can add analysis-only columns (for example, customer segments).
    # Store only fields defined in the normalized SQL table.
    database_columns = [
        "ID", "Year_Birth", "Education", "Marital_Status", "Income", "Kidhome", "Teenhome", "Dt_Customer",
        "Recency", "MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts", "MntSweetProducts", "MntGoldProds",
        "NumDealsPurchases", "NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases", "NumWebVisitsMonth",
        "AcceptedCmp3", "AcceptedCmp4", "AcceptedCmp5", "AcceptedCmp1", "AcceptedCmp2", "Response", "Complain",
        "Country", "Reference_Date", "Age_At_Reference_Year", "Customer_Tenure_Days", "Total_Spend", "Total_Purchases",
        "Children", "Previous_Campaigns_Accepted", "Any_Campaign_Accepted",
    ]
    missing_database_columns = [column for column in database_columns if column not in data_to_store.columns]
    if missing_database_columns:
        raise ValueError(f"Cannot store data; required columns are missing: {missing_database_columns}")
    data_to_store = data_to_store[database_columns]

    columns = data_to_store.columns.tolist()
    column_names = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_query = f"INSERT IGNORE INTO marketing_campaign_data ({column_names}) VALUES ({placeholders})"
    rows = [tuple(None if pd.isna(value) else value for value in row) for row in data_to_store.itertuples(index=False, name=None)]

    connection = pymysql.connect(**database)
    try:
        with connection.cursor() as cursor:
            create_customer_table(cursor)
            cursor.executemany(insert_query, rows)
            inserted_rows = cursor.rowcount
            cursor.execute("SELECT COUNT(*) AS total_rows FROM marketing_campaign_data")
            total_rows = cursor.fetchone()["total_rows"]
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return inserted_rows, total_rows
