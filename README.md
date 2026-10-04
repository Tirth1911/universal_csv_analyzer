# Universal CSV Analyzer

Upload one or many CSV files with different column structures. The app provides general analysis for any readable CSV and specialized social media engagement analysis when recognizable metric columns are present.

## Features

- Import multiple CSV files and switch between them
- Handles common encodings and delimiter detection
- Preview data and detect data types
- Filter data by column values and numeric ranges
- Data quality checks: missing values, duplicates, unique values
- Descriptive statistics and correlation matrix
- Interactive chart selection: histogram, category counts, average-by-group bar chart, line chart, scatter plot, and box plot
- Optional missing-value cleaning and CSV export
- Download filtered data, cleaned data, and text analysis report
- Automatic social media engagement analysis when Likes, Comments, Shares and FollowersCount (or common aliases) exist

## Run on Windows

Open terminal in this folder and run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Run on macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Social media CSV columns

The specialized social analysis recognizes common variants of:
- Likes
- Comments
- Shares
- FollowersCount / Followers

Optional columns: PostType, PostTime.

Formulas:
```text
TotalEngagement = Likes + (Comments × 2) + (Shares × 3)
EngagementRate = (TotalEngagement / FollowersCount) × 100
```

## Notes

- The app does not assume every CSV is a social-media dataset. It runs general analysis for any CSV and only runs social-specific metrics when matching columns are found.
- Date/time columns may be interpreted as text in general analysis. For social posting-time analysis, standard time values such as `18:00` are supported.
- Data edits and cleaning are not written back to your original upload. Download the output CSV to save it.
