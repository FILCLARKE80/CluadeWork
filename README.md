# Analytics App

A flexible CSV analytics application built with Streamlit. Upload any flat CSV file and walk through a guided workflow: data profiling, type casting, quality analysis, and interactive visualisation with auto-generated narratives.

## Features

- **CSV Upload** — auto-detects separator and encoding
- **Data Profiling** — column statistics, null analysis, outlier detection, duplicate detection
- **Data Quality** — highlights missing values, mixed types, whitespace issues, outliers
- **Type Casting** — review detected types and override per-column with confirmation
- **Metric/Dimension Selection** — flexible assignment of columns as measures or categories
- **Visualisations** — Bar, Line, Pie, Scatter, Sankey, Heatmap, Histogram, Box Plot, Treemap, Data Table
- **Narrative Generation** — automatic plain-English summary of selected data slices
- **Filtering** — dynamic per-dimension filters
- **Export** — download aggregated results as CSV

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

A sample CSV is included at `sample_data/sales_sample.csv` for testing.

## Project Structure

```
app.py                          # Main Streamlit entry point
analytics_app/
  modules/
    data_ingestion.py           # CSV upload and parsing
    data_profiler.py            # Profiling and quality detection
    type_caster.py              # Type casting with user confirmation
    analysis.py                 # Metric/dimension selection UI
    visualizations.py           # Chart rendering (Plotly)
    narrative.py                # Auto-generated data narratives
sample_data/
  sales_sample.csv              # Example dataset
.streamlit/
  config.toml                   # Streamlit theme and server config
requirements.txt                # Python dependencies
```
