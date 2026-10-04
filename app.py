import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO, StringIO
from pathlib import Path
import re

st.set_page_config(page_title="Universal CSV Analyzer", page_icon="📊", layout="wide")
st.title("📊 Universal CSV Analyzer")
st.caption("Upload one or many CSV files and get automatic summaries, charts, data-quality checks, filters, and downloadable reports.")

st.sidebar.header("📂 Import CSV Files")
uploads = st.sidebar.file_uploader(
    "Choose one or more CSV files",
    type=["csv"],
    accept_multiple_files=True,
    help="Works with different CSV schemas. Social media columns get specialized engagement analysis."
)

def read_csv_safely(file):
    """Read CSV with common encoding/delimiter fallbacks."""
    file_bytes = file.getvalue()
    last_error = None
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(BytesIO(file_bytes), encoding=encoding, sep=None, engine="python")
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read this CSV: {last_error}")

def clean_column_names(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def infer_types(df):
    """Conservatively convert numeric-looking text columns."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object":
            s = df[col].astype(str).str.strip()
            # Convert only when most non-empty values are numeric-like.
            cleaned = s.str.replace(",", "", regex=False).str.replace(r"^\$", "", regex=True)
            numeric = pd.to_numeric(cleaned, errors="coerce")
            nonempty = s.ne("") & s.ne("nan") & s.ne("None")
            if nonempty.sum() and numeric[nonempty].notna().mean() >= 0.85:
                df[col] = numeric
    return df

def make_download(df, name="analysis.csv"):
    return df.to_csv(index=False).encode("utf-8-sig")

def detect_social_columns(df):
    lower = {str(c).strip().lower(): c for c in df.columns}
    aliases = {
        "postid": ["postid", "post_id", "post id", "id"],
        "posttype": ["posttype", "post_type", "post type", "contenttype", "content_type"],
        "posttime": ["posttime", "post_time", "post time", "time", "timestamp", "datetime", "date"],
        "likes": ["likes", "like", "like_count"],
        "comments": ["comments", "comment", "comment_count"],
        "shares": ["shares", "share", "share_count"],
        "followers": ["followerscount", "followers_count", "followers count", "followers", "follower_count"]
    }
    found = {}
    for key, names in aliases.items():
        for name in names:
            if name in lower:
                found[key] = lower[name]
                break
    return found

if not uploads:
    st.info("Upload any CSV file from the sidebar to begin. You can select multiple CSV files at once.")
    st.markdown("### What this app does automatically")
    st.markdown("""
    - Displays the dataset and column types
    - Calculates row/column counts, missing values, duplicates, and descriptive statistics
    - Detects numeric, categorical, and date/time columns
    - Lets you filter rows and choose chart columns
    - Creates histograms, bar charts, line charts, box plots, and scatter plots
    - Exports cleaned data, filtered data, and a text analysis report
    - Detects social media metrics and calculates weighted engagement when matching columns exist
    """)
    st.stop()

# Tabs apply to the currently selected CSV; files are listed in the selector.
file_names = [f.name for f in uploads]
selected_name = st.sidebar.selectbox("Analyze file", file_names)
selected_file = next(f for f in uploads if f.name == selected_name)

try:
    original_df = clean_column_names(read_csv_safely(selected_file))
except Exception as exc:
    st.error(f"Unable to load {selected_name}: {exc}")
    st.stop()

if original_df.empty and len(original_df.columns) == 0:
    st.error("The CSV appears to be empty or has no readable header.")
    st.stop()

df = infer_types(original_df)
social = detect_social_columns(df)

# Sidebar operations
st.sidebar.subheader("🔎 Filter Data")
filter_col = st.sidebar.selectbox("Filter column", ["(None)"] + list(df.columns))
filtered_df = df.copy()
if filter_col != "(None)":
    vals = df[filter_col].dropna().unique().tolist()
    if len(vals) <= 100:
        chosen = st.sidebar.multiselect("Keep values", vals, default=vals)
        filtered_df = df[df[filter_col].isin(chosen)].copy()
    else:
        st.sidebar.caption("This column has many unique values. Use the table search/download or choose another filter column.")
    if pd.api.types.is_numeric_dtype(df[filter_col]):
        numeric_range = st.sidebar.slider(
            "Numeric range",
            min_value=float(df[filter_col].min()),
            max_value=float(df[filter_col].max()),
            value=(float(df[filter_col].min()), float(df[filter_col].max()))
        )
        filtered_df = filtered_df[
            pd.to_numeric(filtered_df[filter_col], errors="coerce").between(*numeric_range)
        ]

tab_overview, tab_data, tab_quality, tab_stats, tab_charts, tab_social, tab_export = st.tabs([
    "🏠 Overview", "🧾 Data Table", "🧹 Data Quality", "📈 Statistics",
    "📊 Charts", "📣 Social Analysis", "⬇️ Export"
])

with tab_overview:
    st.subheader(f"Overview: {selected_name}")
    a, b, c, d = st.columns(4)
    a.metric("Rows", f"{len(df):,}")
    b.metric("Columns", f"{len(df.columns):,}")
    c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
    d.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
    st.markdown("### Data preview")
    st.dataframe(df.head(100), use_container_width=True)
    st.markdown("### Detected column types")
    type_table = pd.DataFrame({
        "Column": df.columns,
        "Detected type": [str(df[c].dtype) for c in df.columns],
        "Unique values": [int(df[c].nunique(dropna=True)) for c in df.columns],
        "Missing values": [int(df[c].isna().sum()) for c in df.columns]
    })
    st.dataframe(type_table, use_container_width=True)

with tab_data:
    st.subheader("Dataset and row filtering")
    st.write(f"Showing {len(filtered_df):,} of {len(df):,} rows.")
    st.dataframe(filtered_df, use_container_width=True, height=420)
    st.download_button(
        "Download filtered CSV",
        data=make_download(filtered_df),
        file_name=f"{Path(selected_name).stem}_filtered.csv",
        mime="text/csv"
    )
    st.markdown("### Optional data cleaning")
    missing_action = st.selectbox(
        "Handle missing values for cleaned export",
        ["Keep as-is", "Drop rows with any missing value", "Fill numeric missing values with column median", "Fill missing values with 0 or 'Unknown'"]
    )
    cleaned = filtered_df.copy()
    if missing_action == "Drop rows with any missing value":
        cleaned = cleaned.dropna()
    elif missing_action == "Fill numeric missing values with column median":
        for col in cleaned.select_dtypes(include=np.number).columns:
            cleaned[col] = cleaned[col].fillna(cleaned[col].median())
    elif missing_action == "Fill missing values with 0 or 'Unknown'":
        for col in cleaned.columns:
            if pd.api.types.is_numeric_dtype(cleaned[col]):
                cleaned[col] = cleaned[col].fillna(0)
            else:
                cleaned[col] = cleaned[col].fillna("Unknown")
    st.download_button(
        "Download cleaned CSV",
        data=make_download(cleaned),
        file_name=f"{Path(selected_name).stem}_cleaned.csv",
        mime="text/csv"
    )

with tab_quality:
    st.subheader("Data quality report")
    quality = pd.DataFrame({
        "Column": df.columns,
        "Data type": [str(df[c].dtype) for c in df.columns],
        "Missing count": [int(df[c].isna().sum()) for c in df.columns],
        "Missing %": [(df[c].isna().mean() * 100).round(2) for c in df.columns],
        "Unique values": [int(df[c].nunique(dropna=True)) for c in df.columns]
    })
    st.dataframe(quality, use_container_width=True)
    st.write(f"Exact duplicate rows: **{df.duplicated().sum():,}**")
    st.write(f"Completely empty rows: **{df.isna().all(axis=1).sum():,}**")
    st.download_button(
        "Download data quality report",
        data=quality.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{Path(selected_name).stem}_quality_report.csv",
        mime="text/csv"
    )

with tab_stats:
    st.subheader("Descriptive statistics")
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=np.number).columns.tolist()
    if numeric_cols:
        st.markdown("### Numeric columns")
        st.dataframe(df[numeric_cols].describe().T, use_container_width=True)
        st.markdown("### Correlation matrix")
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr(numeric_only=True)
            fig, ax = plt.subplots(figsize=(max(6, len(numeric_cols)), max(4, len(numeric_cols) * 0.65)))
            sns.heatmap(corr, annot=len(numeric_cols) <= 10, fmt=".2f", cmap="coolwarm", ax=ax)
            ax.set_title("Numeric Feature Correlations")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("At least two numeric columns are needed for a correlation matrix.")
    else:
        st.info("No numeric columns were detected.")
    if categorical_cols:
        st.markdown("### Categorical summaries")
        cat_summary = pd.DataFrame({
            "Column": categorical_cols,
            "Unique values": [df[c].nunique(dropna=True) for c in categorical_cols],
            "Most common value": [
                (df[c].mode(dropna=True).iloc[0] if not df[c].mode(dropna=True).empty else "N/A")
                for c in categorical_cols
            ]
        })
        st.dataframe(cat_summary, use_container_width=True)

with tab_charts:
    st.subheader("Build charts from any CSV")
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    all_cols = list(df.columns)
    chart_type = st.selectbox("Chart type", [
        "Histogram", "Bar chart (category counts)", "Bar chart (mean numeric value)",
        "Line chart", "Scatter plot", "Box plot"
    ])
    if chart_type == "Histogram":
        x = st.selectbox("Numeric column", numeric_cols, key="hist_x") if numeric_cols else None
        if x:
            fig, ax = plt.subplots()
            sns.histplot(df[x].dropna(), kde=True, ax=ax)
            ax.set_title(f"Distribution of {x}")
            st.pyplot(fig)
            plt.close(fig)
    elif chart_type == "Bar chart (category counts)":
        x = st.selectbox("Category column", all_cols, key="count_x")
        counts = df[x].astype(str).value_counts().head(30)
        fig, ax = plt.subplots()
        counts.plot(kind="bar", ax=ax)
        ax.set_title(f"Top category counts: {x}")
        ax.set_ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig)
        plt.close(fig)
    elif chart_type == "Bar chart (mean numeric value)":
        if numeric_cols:
            x = st.selectbox("Group by", all_cols, key="mean_group")
            y = st.selectbox("Numeric value", numeric_cols, key="mean_value")
            grouped = df.groupby(x, dropna=False)[y].mean().sort_values(ascending=False).head(30)
            fig, ax = plt.subplots()
            grouped.plot(kind="bar", ax=ax)
            ax.set_title(f"Average {y} by {x}")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No numeric columns are available.")
    elif chart_type == "Line chart":
        if numeric_cols:
            x = st.selectbox("X-axis", all_cols, key="line_x")
            y = st.selectbox("Y-axis numeric column", numeric_cols, key="line_y")
            temp = df[[x, y]].dropna()
            if len(temp):
                try:
                    temp = temp.sort_values(x)
                except Exception:
                    pass
                fig, ax = plt.subplots()
                ax.plot(temp[x].astype(str), temp[y], marker="o")
                ax.set_title(f"{y} across {x}")
                plt.xticks(rotation=45, ha="right")
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("No numeric columns are available.")
    elif chart_type == "Scatter plot":
        if len(numeric_cols) >= 2:
            x = st.selectbox("X-axis", numeric_cols, key="scatter_x")
            y = st.selectbox("Y-axis", [c for c in numeric_cols if c != x] or numeric_cols, key="scatter_y")
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
            ax.set_title(f"{y} vs {x}")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("At least two numeric columns are needed for a scatter plot.")
    elif chart_type == "Box plot":
        if numeric_cols:
            y = st.selectbox("Numeric column", numeric_cols, key="box_y")
            x = st.selectbox("Optional grouping column", ["(None)"] + all_cols, key="box_x")
            fig, ax = plt.subplots()
            if x != "(None)":
                sns.boxplot(data=df, x=x, y=y, ax=ax)
                plt.xticks(rotation=45, ha="right")
            else:
                sns.boxplot(y=df[y], ax=ax)
            ax.set_title(f"Distribution and outliers: {y}")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No numeric columns are available.")

with tab_social:
    st.subheader("Social Media Engagement Analysis")
    required_social = ["likes", "comments", "shares", "followers"]
    if all(k in social for k in required_social):
        likes_col, comments_col, shares_col, followers_col = (
            social["likes"], social["comments"], social["shares"], social["followers"]
        )
        social_df = df.copy()
        for col in [likes_col, comments_col, shares_col, followers_col]:
            social_df[col] = pd.to_numeric(social_df[col], errors="coerce")
        social_df["TotalEngagement"] = (
            social_df[likes_col] + 2 * social_df[comments_col] + 3 * social_df[shares_col]
        )
        social_df["EngagementRate"] = np.where(
            social_df[followers_col] > 0,
            social_df["TotalEngagement"] / social_df[followers_col] * 100,
            np.nan
        )
        k1, k2, k3 = st.columns(3)
        k1.metric("Total weighted engagement", f"{social_df['TotalEngagement'].sum(skipna=True):,.0f}")
        k2.metric("Average weighted engagement", f"{social_df['TotalEngagement'].mean():,.2f}")
        k3.metric("Average engagement rate", f"{social_df['EngagementRate'].mean():.2f}%")
        st.markdown("### Calculated social metrics")
        st.dataframe(social_df, use_container_width=True)
        if "posttype" in social:
            type_col = social["posttype"]
            perf = social_df.groupby(type_col).agg(
                AverageEngagement=("TotalEngagement", "mean"),
                AverageEngagementRate=("EngagementRate", "mean"),
                Posts=("TotalEngagement", "count")
            ).sort_values("AverageEngagement", ascending=False)
            st.markdown("### Performance by post type")
            st.dataframe(perf.round(2), use_container_width=True)
            fig, ax = plt.subplots()
            perf["AverageEngagement"].plot(kind="bar", ax=ax)
            ax.set_title("Average Weighted Engagement by Post Type")
            ax.set_ylabel("Average engagement")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)
            plt.close(fig)
            if not perf.empty:
                st.success(f"Highest average engagement format: **{perf.index[0]}**.")
        time_col = social.get("posttime")
        if time_col:
            parsed = pd.to_datetime(social_df[time_col].astype(str), errors="coerce")
            if parsed.notna().any():
                social_df["PostingHour"] = parsed.dt.hour
                hourly = social_df.groupby("PostingHour")["TotalEngagement"].mean().dropna()
                if not hourly.empty:
                    st.markdown("### Average engagement by posting hour")
                    fig, ax = plt.subplots()
                    hourly.plot(kind="bar", ax=ax)
                    ax.set_title("Average Weighted Engagement by Posting Hour")
                    st.pyplot(fig)
                    plt.close(fig)
                    st.write(f"Best hour in this dataset: **{int(hourly.idxmax()):02d}:00**.")
                else:
                    st.caption("Could not parse the time column into hours. Use formats like 18:00 or a standard date/time.")
        st.download_button(
            "Download social engagement analysis CSV",
            data=make_download(social_df),
            file_name=f"{Path(selected_name).stem}_social_analysis.csv",
            mime="text/csv"
        )
        st.caption("Engagement formula used: Likes + (Comments × 2) + (Shares × 3). Engagement rate = Total Engagement / Followers × 100.")
    else:
        st.info(
            "This CSV does not contain all recognized social-media metric columns. "
            "General analysis and charts are still available. For specialized social analysis, "
            "include columns equivalent to Likes, Comments, Shares, and FollowersCount."
        )
        st.write("Columns detected:", ", ".join(map(str, df.columns)))

with tab_export:
    st.subheader("Export your analysis")
    report_lines = [
        f"CSV Analysis Report: {selected_name}",
        "=" * 60,
        f"Rows: {len(df)}",
        f"Columns: {len(df.columns)}",
        f"Missing cells: {int(df.isna().sum().sum())}",
        f"Duplicate rows: {int(df.duplicated().sum())}",
        "",
        "Column types:"
    ]
    for col in df.columns:
        report_lines.append(
            f"- {col}: {df[col].dtype}; unique={df[col].nunique(dropna=True)}; missing={df[col].isna().sum()}"
        )
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if numeric_cols:
        report_lines.extend(["", "Numeric descriptive statistics:", df[numeric_cols].describe().to_string()])
    st.download_button(
        "Download analysis report (.txt)",
        data="\n".join(report_lines).encode("utf-8"),
        file_name=f"{Path(selected_name).stem}_analysis_report.txt",
        mime="text/plain"
    )
    st.download_button(
        "Download imported data as CSV",
        data=make_download(df),
        file_name=f"{Path(selected_name).stem}_imported.csv",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.caption("Tip: select another uploaded file from 'Analyze file' to switch analyses.")
