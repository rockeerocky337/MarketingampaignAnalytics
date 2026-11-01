"""Notebook-style exploratory data analysis for the marketing campaign CSV.

Open this file in VS Code and run each ``# %%`` cell, or run it from a terminal.
The source DataFrame (``raw``) is never changed. ``df`` is the working copy.
"""

# %% [markdown]
# # Marketing Campaign EDA
# This script uses only columns found in the supplied CSV. It reports quality issues
# first and never silently deletes rows or fills missing values.

# %% 1. Imports and setup
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sys

from database import store_cleaned_data

DATA_FILE = Path(__file__).with_name("marketing_campaign_data.csv")
OUTPUT_FILE = Path(__file__).with_name("marketing_campaign_data_cleaned.csv")
STORE_IN_DATABASE = True  # Requested: load the reviewed EDA data into MySQL.

sns.set_theme(style="whitegrid", palette="deep")
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 140)


def show_table(table: pd.DataFrame | pd.Series, rows: int = 15) -> None:
    """Show a small table in notebooks and print it when run as a script."""
    result = table.head(rows)
    try:
        from IPython.display import display
        display(result)
    except ImportError:
        print(result)


def existing_columns(data: pd.DataFrame, candidates: list[str]) -> list[str]:
    """Return candidates that are present in the current data."""
    return [column for column in candidates if column in data.columns]


# %% 2. Load the data
# `raw` is preserved. Work only with the independent copy named `df`.
raw = pd.read_csv(DATA_FILE)
df = raw.copy()
print(f"Loaded {len(raw):,} rows from {DATA_FILE.name}.")


# %% 3. Inspect the data
print("First five rows:")
show_table(df.head())
print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]:,} columns")
print("\nColumn names:\n", df.columns.tolist())
print("\nData types:\n", df.dtypes)
print("\nNumeric summary statistics:")
show_table(df.describe().T.round(2), rows=len(df.columns))


# %% 4. Missing-value counts and percentages
def missing_value_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate missingness without changing data values."""
    counts = data.isna().sum()
    return pd.DataFrame(
        {"missing_count": counts, "missing_percent": (counts / len(data) * 100).round(2)}
    ).sort_values(["missing_count", "missing_percent"], ascending=False)


missing_summary = missing_value_summary(df)
print("Missing-value summary:")
show_table(missing_summary, rows=len(missing_summary))


# %% 5. Check duplicate rows and customer IDs
print(f"Duplicate complete rows: {int(df.duplicated().sum()):,}")
id_candidates = [c for c in df.columns if c.lower() in {"id", "customer_id", "customerid"}]
id_column = id_candidates[0] if id_candidates else None
if id_column:
    print(f"ID column: {id_column}")
    print(f"Missing IDs: {int(df[id_column].isna().sum()):,}")
    print(f"Repeated IDs: {int(df[id_column].duplicated().sum()):,}")
    repeated_ids = df.loc[df[id_column].duplicated(keep=False)].sort_values(id_column)
    if not repeated_ids.empty:
        print("Repeated ID records: investigate before deciding which record to keep.")
        show_table(repeated_ids)
else:
    print("No customer ID column was found, so ID checks were skipped.")


# %% 6. Easy text cleaning: spaces, empty values, and category-label variations
def clean_text_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Trim text and standardise labels that differ only by spaces or letter case."""
    log = []
    for column in data.select_dtypes(include=["object", "string"]).columns:
        original = data[column].astype("string")
        cleaned = original.str.strip().str.replace(r"\s+", " ", regex=True)
        empty_count = int(cleaned.eq("").sum())
        cleaned = cleaned.mask(cleaned.eq(""), pd.NA)

        # "single", "Single", and " SINGLE " become one label. The first
        # non-empty spelling found in the file is retained as the display label.
        key = cleaned.str.casefold()
        label_lookup = cleaned.groupby(key, dropna=True).first()
        standardised = key.map(label_lookup).astype("string")
        changed_labels = int((cleaned.notna() & cleaned.ne(standardised)).sum())
        data[column] = standardised
        log.append(
            {
                "column": column,
                "empty_strings_to_missing": empty_count,
                "category_labels_standardised": changed_labels,
                "unique_labels_before": original.nunique(dropna=True),
                "unique_labels_after": data[column].nunique(dropna=True),
            }
        )
    return pd.DataFrame(log)


cleaning_log = clean_text_columns(df)
print("Easy cleaning log:")
show_table(cleaning_log, rows=len(cleaning_log))
print("Only spacing and letter-case variations are standardised. Different business categories are not merged automatically.")


# %% 7. Convert expected numeric and date columns; reveal invalid values
expected_numeric = [
    "ID", "Year_Birth", "Income", "Kidhome", "Teenhome", "Recency",
    "MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts", "MntSweetProducts", "MntGoldProds",
    "NumDealsPurchases", "NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases", "NumWebVisitsMonth",
    "AcceptedCmp1", "AcceptedCmp2", "AcceptedCmp3", "AcceptedCmp4", "AcceptedCmp5", "Response", "Complain",
]
numeric_columns = existing_columns(df, expected_numeric)
invalid_numeric_values = {}
for column in numeric_columns:
    source = df[column].copy()
    converted = pd.to_numeric(source, errors="coerce")
    invalid_mask = source.notna() & converted.isna()
    if invalid_mask.any():
        invalid_numeric_values[column] = pd.DataFrame({"source_value": source[invalid_mask]})
    df[column] = converted

if invalid_numeric_values:
    print("Invalid non-empty numeric values found. They are now missing in df for investigation:")
    for column, values in invalid_numeric_values.items():
        print(f"\n{column}:")
        show_table(values)
else:
    print("No invalid non-empty values were found in the expected numeric columns.")

date_column = "Dt_Customer" if "Dt_Customer" in df.columns else None
if date_column:
    source_date = df[date_column].copy()
    df[date_column] = pd.to_datetime(source_date, errors="coerce")
    invalid_dates = source_date.notna() & df[date_column].isna()
    if invalid_dates.any():
        print("Invalid non-empty date values found. They are now missing in df for investigation:")
        show_table(pd.DataFrame({"source_value": source_date[invalid_dates]}))
    else:
        print(f"{date_column} converted to datetime; no invalid non-empty values were found.")
else:
    print("No Dt_Customer column was found, so date conversion was skipped.")


# %% 7. Confirm data types: dates, numbers, and categories
# Numeric conversion is complete above. These category fields are now stored as pandas categories.
category_columns_for_type = existing_columns(df, ["Education", "Marital_Status", "Country"])
for column in category_columns_for_type:
    df[column] = df[column].astype("category")

integer_like_columns = existing_columns(
    df,
    ["ID", "Year_Birth", "Kidhome", "Teenhome", "Recency", "NumDealsPurchases", "NumWebPurchases",
     "NumCatalogPurchases", "NumStorePurchases", "NumWebVisitsMonth", "AcceptedCmp1", "AcceptedCmp2",
     "AcceptedCmp3", "AcceptedCmp4", "AcceptedCmp5", "Response", "Complain"],
)
type_audit = pd.DataFrame(
    {
        "column": df.columns,
        "data_type": df.dtypes.astype(str).values,
        "intended_use": [
            "date" if column == date_column else
            "categorical" if column in category_columns_for_type else
            "integer / count / flag" if column in integer_like_columns else
            "numeric amount" if column in numeric_columns else
            "other" for column in df.columns
        ],
    }
)
print("Data-type audit after cleaning and conversion:")
show_table(type_audit, rows=len(type_audit))


# %% [markdown]
# ## Missing-value decisions
# This workflow does **not** fill or delete missing values. Choose a policy only after
# understanding the field: investigate missing IDs; consider median Income only for a
# justified analysis; use an explicit Unknown category when it is meaningful; and do
# not treat campaign or spending blanks as zero unless the data documentation confirms it.
print("No values were filled and no rows were deleted. df retains every source record.")



# %% 8. Create useful features with stated assumptions
spend_columns = existing_columns(df, ["MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts", "MntSweetProducts", "MntGoldProds"])
purchase_columns = existing_columns(df, ["NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases"])
campaign_columns = existing_columns(df, ["AcceptedCmp1", "AcceptedCmp2", "AcceptedCmp3", "AcceptedCmp4", "AcceptedCmp5"])

if spend_columns:
    df["Total_Spend"] = df[spend_columns].sum(axis=1, min_count=len(spend_columns))
if purchase_columns:
    df["Total_Purchases"] = df[purchase_columns].sum(axis=1, min_count=len(purchase_columns))
if {"Kidhome", "Teenhome"}.issubset(df.columns):
    df["Children"] = df["Kidhome"] + df["Teenhome"]
if campaign_columns:
    df["Previous_Campaigns_Accepted"] = df[campaign_columns].sum(axis=1, min_count=len(campaign_columns))
if "Previous_Campaigns_Accepted" in df and "Response" in df:
    df["Any_Campaign_Accepted"] = ((df["Previous_Campaigns_Accepted"] > 0) | (df["Response"] == 1)).astype("Int64")

reference_date = pd.NaT
if date_column and df[date_column].notna().any():
    # Latest source signup date is a fixed, reproducible reference instead of today's date.
    reference_date = df[date_column].max()
    df["Reference_Date"] = reference_date
    df["Customer_Tenure_Days"] = (reference_date - df[date_column]).dt.days
    if "Year_Birth" in df:
        df["Age_At_Reference_Year"] = reference_date.year - df["Year_Birth"]
    print(f"Reference date: {reference_date.date()} (latest valid Dt_Customer in this CSV).")
    print("Age is approximate because the source contains only Year_Birth, not full birth dates.")

# Bands make customer profiles easier to compare in the dashboard and SQL summaries.
if "Age_At_Reference_Year" in df:
    df["Age_Band"] = pd.cut(
        df["Age_At_Reference_Year"],
        bins=[0, 29, 39, 49, 59, 120],
        labels=["Under 30", "30-39", "40-49", "50-59", "60+"],
    )
if "Income" in df:
    df["Income_Band"] = pd.cut(
        df["Income"],
        bins=[-np.inf, 25000, 50000, 75000, np.inf],
        labels=["Up to 25k", "25k-50k", "50k-75k", "75k+"],
    )

# Rule-based flags required by the project brief. These are transparent business rules.
if "Income" in df:
    df["High_Income"] = (df["Income"] > 75000).astype("Int64")
if "Age_At_Reference_Year" in df:
    df["Young_Customer"] = (df["Age_At_Reference_Year"] < 30).astype("Int64")
if "NumWebVisitsMonth" in df:
    df["High_Web_Engagement"] = (df["NumWebVisitsMonth"] > 5).astype("Int64")
if "Children" in df:
    df["Family_Customer"] = (df["Children"] > 0).astype("Int64")
if "Total_Spend" in df:
    high_spender_cutoff = df["Total_Spend"].quantile(0.90)
    df["High_Spender"] = (df["Total_Spend"] > high_spender_cutoff).astype("Int64")
    print(f"High-spender rule: Total_Spend greater than the 90th percentile ({high_spender_cutoff:,.2f}).")



# %% 9. Numerical EDA: descriptive statistics, histograms, and box plots
id_exclusions = {c for c in [id_column, "ID"] if c}
numeric_for_eda = [c for c in df.select_dtypes(include="number").columns if c not in id_exclusions]
print("Descriptive statistics for meaningful numeric columns:")
show_table(df[numeric_for_eda].describe().T.round(2), rows=len(numeric_for_eda))

plot_numeric_columns = existing_columns(df, ["Income", "Total_Spend", "Total_Purchases", "Recency"])
if plot_numeric_columns:
    fig, axes = plt.subplots(2, len(plot_numeric_columns), figsize=(5 * len(plot_numeric_columns), 8))
    axes = np.atleast_2d(axes)
    for index, column in enumerate(plot_numeric_columns):
        sns.histplot(data=df, x=column, bins=30, kde=True, ax=axes[0, index], color="steelblue")
        axes[0, index].set(title=f"Distribution of {column}", xlabel=column)
        sns.boxplot(data=df, x=column, ax=axes[1, index], color="lightseagreen")
        axes[1, index].set(title=f"Box plot of {column}", xlabel=column)
    plt.suptitle("Numerical distributions and possible extreme values", y=1.02)
    plt.tight_layout()
    plt.show()
    print("Histograms show distribution shape. Box plots make unusually low or high values visible.")


# %% 10. Categorical EDA: frequency tables and count plots
category_columns = existing_columns(df, ["Education", "Marital_Status", "Country"])
for column in category_columns:
    frequency = df[column].value_counts(dropna=False).rename_axis(column).reset_index(name="customer_count")
    frequency["percent"] = (frequency["customer_count"] / len(df) * 100).round(2)
    print(f"\nFrequency table for {column}:")
    show_table(frequency, rows=20)

    labels = df[column].value_counts(dropna=False).head(15).index
    chart_data = df[df[column].isin(labels)]
    plt.figure(figsize=(10, max(4, len(labels) * 0.35)))
    sns.countplot(data=chart_data, y=column, order=labels, color="cornflowerblue")
    plt.title(f"Customer count by {column} (top 15 labels)")
    plt.xlabel("Customers")
    plt.ylabel(column)
    plt.tight_layout()
    plt.show()
    print("This chart shows group size. It does not show campaign success by itself.")


# %% 11. Relationships: scatter plot, grouped summaries, and a correlation heatmap
if {"Income", "Total_Spend"}.issubset(df.columns):
    plt.figure(figsize=(8, 5))
    sns.scatterplot(data=df, x="Income", y="Total_Spend", hue="Response" if "Response" in df else None, alpha=0.45, s=25)
    plt.title("Income and total product spending")
    plt.xlabel("Income")
    plt.ylabel("Total spend")
    plt.tight_layout()
    plt.show()
    print("The scatter plot checks whether higher reported income tends to occur with higher spending.")

group_column = "Country" if "Country" in df.columns else ("Education" if "Education" in df.columns else None)
summary_columns = existing_columns(df, ["Total_Spend", "Total_Purchases", "Income", "Response"])
if group_column and summary_columns:
    grouped = df.groupby(group_column, dropna=False)[summary_columns].mean().round(2).sort_values(summary_columns[0], ascending=False)
    print(f"\nAverage measures by {group_column}:")
    show_table(grouped, rows=20)
    print("Compare group sizes before making a decision from a group average.")

correlation_columns = existing_columns(df, ["Income", "Recency", "Total_Spend", "Total_Purchases", "NumWebVisitsMonth", "Response", "Children", "Customer_Tenure_Days"])
if len(correlation_columns) >= 2:
    plt.figure(figsize=(9, 7))
    sns.heatmap(df[correlation_columns].corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title("Correlation of meaningful numeric variables")
    plt.tight_layout()
    plt.show()
    print("Correlation measures linear association, not proof of cause and effect. Numeric IDs are excluded.")


# %% 12. Potential outliers using the IQR method
def iqr_outlier_summary(data: pd.DataFrame, column: str) -> tuple[pd.DataFrame, pd.Series]:
    """Calculate IQR limits and flag records outside them without removing any."""
    values = data[column].dropna()
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (data[column] < lower) | (data[column] > upper)
    summary = pd.Series({"Q1": q1, "Q3": q3, "IQR": iqr, "lower_bound": lower, "upper_bound": upper, "outlier_count": int(mask.sum())})
    return data.loc[mask].copy(), summary


for column in existing_columns(df, ["Income", "Total_Spend", "Total_Purchases"]):
    outliers, summary = iqr_outlier_summary(df, column)
    print(f"\nIQR outlier check for {column}:")
    show_table(summary.to_frame("value"), rows=len(summary))
    print("A flag means the value is far from the middle 50%; it can be a valuable or valid rare customer, so no rows are removed.")
    if not outliers.empty:
        display_columns = list(dict.fromkeys(existing_columns(outliers, [id_column, column, "Income", "Total_Spend", "Country"])))
        show_table(outliers[display_columns], rows=10)


# %% 13. Customer segmentation
# Segments are descriptive groups for EDA, not a prediction model.
if "Total_Spend" in df and df["Total_Spend"].nunique(dropna=True) >= 4:
    df["Spend_Segment"] = pd.qcut(
        df["Total_Spend"], q=4, labels=["Low spend", "Medium spend", "High spend", "Very high spend"]
    )

if {"Total_Spend", "Total_Purchases"}.issubset(df.columns):
    spend_midpoint = df["Total_Spend"].median()
    purchase_midpoint = df["Total_Purchases"].median()
    response_condition = df["Response"].eq(1) if "Response" in df else pd.Series(False, index=df.index)
    df["Customer_Segment"] = np.select(
        [
            (df["Total_Spend"] >= spend_midpoint) & response_condition,
            (df["Total_Spend"] >= spend_midpoint) & ~response_condition,
            (df["Total_Purchases"] >= purchase_midpoint),
        ],
        ["High-value responders", "High-value non-responders", "Frequent purchasers"],
        default="Lower activity customers",
    )
    segment_summary = (
        df.groupby("Customer_Segment", observed=True)
        [["Total_Spend", "Total_Purchases"]]
        .agg(["count", "mean"])
        .round(2)
    )
    print("Customer-segment summary:")
    show_table(segment_summary, rows=len(segment_summary))

    plt.figure(figsize=(9, 5))
    segment_order = df["Customer_Segment"].value_counts().index
    sns.countplot(data=df, y="Customer_Segment", order=segment_order, color="mediumpurple")
    plt.title("Customer segments based on spending, purchases, and response")
    plt.xlabel("Customers")
    plt.ylabel("Segment")
    plt.tight_layout()
    plt.show()
    print("Use high-value non-responders as a starting point for a targeted campaign review.")


# %% 14. Main findings, data quality, and business-insight starting points
print("\nComputed EDA recap:")
print(f"Rows retained for analysis: {len(df):,}")
print(f"Complete duplicate rows: {int(df.duplicated().sum()):,}")
print(f"Missing cells after conversion: {int(df.isna().sum().sum()):,}")
if "Response" in df:
    print(f"Latest campaign response rate: {df['Response'].mean():.2%}")
if spend_columns:
    product_totals = df[spend_columns].sum().sort_values(ascending=False)
    print(f"Highest total-spend product category: {product_totals.index[0]} ({product_totals.iloc[0]:,.2f})")
if group_column and "Response" in df:
    response_rate = df.groupby(group_column, dropna=False)["Response"].mean().sort_values(ascending=False)
    print(f"Highest response rate by {group_column}: {response_rate.index[0]} ({response_rate.iloc[0]:.2%})")
print("Use the computed summaries and charts to form business recommendations. Investigate missing, invalid, duplicate, and outlier records before altering them.")


# %% 15. Export the cleaned working dataset to CSV
# df has trimmed text, converted types, and derived features, while preserving all rows.
df.to_csv(OUTPUT_FILE, index=False)
print(f"Exported {len(df):,} rows to {OUTPUT_FILE.name}")


# %% Optional: store the reviewed EDA data in MySQL using database.py
if STORE_IN_DATABASE:
    inserted_rows, total_rows = store_cleaned_data(df)
    print(f"MySQL load complete: {inserted_rows:,} new rows; {total_rows:,} rows in marketing_campaign_data.")
else:
    print("MySQL load skipped. Set STORE_IN_DATABASE = True after reviewing the EDA output.")
