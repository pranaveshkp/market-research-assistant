# Tableau Dashboard Guide

The dashboard is built in **Tableau Public** (free, runs natively on Mac and Windows) from `data/output/market_data.xlsx`, which `python -m src.clean` creates.

## Connect
1. Open Tableau Public → **Connect → Microsoft Excel** → `data/output/market_data.xlsx`.
2. Drag **market_facts** onto the canvas.
3. For the company chart, add a second source: **Data → New Data Source → Microsoft Excel** → same file → drag **company_events**.

## Sheets

| Sheet | Build | Filters |
|---|---|---|
| **Capacity Over Time** | Columns: `Year` (continuous dimension) · Rows: `MAX(Value)` · Color: `Technology` · Marks: Line | Metric = installed_capacity, Unit = GW, Region = Global, Year 2008–2025, exclude "Other" |
| **Top 10 Countries** | Rows: `Region` · Columns: `MAX(Value)` · Label: `MAX(Value)` · sorted descending | Metric = installed_capacity, Unit = GW, Technology = All renewables, Region excludes Global and non-country regions, Top 10 by MAX(Value) |
| **Technology Mix** | Marks: Pie · Color: `Technology` · Angle: `MAX(Value)` · Label: Technology + Percent of Total | Metric = installed_capacity, Unit = GW, Region = Global, one year, individual technologies only (not "All renewables") |
| **Company Activity** | Rows: `Event Type` · Columns: `company_events (Count)` · Color: `Event Type` | — |

**Why MAX and not SUM:** the same figure often appears in more than one source. MAX avoids double-counting.

## Data quality checks
- Hover suspicious points (sudden drops, huge spikes). Add `Description` and `Source` to **Tooltip** to see what the figure really was.
- Right-click wrong points → **Exclude**. Typical errors: a country's figure tagged as global, or a forecast mixed in with actuals.

## Dashboard and publish
1. **New Dashboard** → Size: Automatic → drag in the four sheets.
2. Add **Technology** and **Region** filters → Apply to Worksheets → All Using This Data Source.
3. Add a title text box: "Renewable Energy Market Overview."
4. **File → Save to Tableau Public As…** and copy the link into the README.
5. Save a screenshot as `docs/screenshots/dashboard.png`.
