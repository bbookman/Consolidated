# Billboard Chart Data Update Logic

## Overview

Billboard chart data (Hot 100) is updated weekly, not daily. This document explains how the application manages Billboard data updates to avoid unnecessary API calls.

## How It Works

1. **Context-Aware Update Policy**: The application first checks if Netflix, Limitless, Bee, or Weather data already exists in the database. If any of these data types exist, the app will use existing Billboard data rather than making a new API call.

2. **Weekly Update Check**: If no other data exists, the application checks if the stored Billboard chart data is more than 7 days old before attempting to fetch new data.

3. **Data Reuse**: If the existing data is less than 7 days old, the application will use the data from the database instead of making a new API call.

4. **Update Control**: The `force_update` parameter controls update behavior:
   - `force_update=True`: Always fetch new data regardless of existing data
   - `force_update=False`: Always use existing data if available, regardless of age
   - `force_update=None` (default): Use standard 7-day update threshold

5. **Historical Data**: To fetch chart data for a specific date, modify the function call to include a date parameter:
   ```python
   # Fetch chart data for a specific date
   hot100_chart = await fetch_billboard_chart("hot-100", date="2025-02-15")
   ```

## Implementation Details

The update logic is controlled by these key functions:

1. `should_update_billboard_chart(chart_name, days_threshold=7)` in `database_handler.py` - Determines if a chart needs updating based on its age.

2. `fetch_billboard_chart(chart_name, date=None, force_update=False)` in `app.py` - Handles the decision to reuse or fetch new data.

3. Several database checks in `run_cli_async()` that determine if other data types exist before deciding on Billboard data retrieval.

## Logs

Look for these log messages to understand what's happening with Billboard data:

- `Found X weather/conversation/lifelog/Netflix records, using existing billboard data if available` - Other data exists, will prioritize existing Billboard data
- `Weather data exists, skipping Billboard API call if data exists` - Weather data exists, avoiding new Billboard API calls
- `Using existing chart data for hot-100 from YYYY-MM-DD` - Data is being reused
- `Chart data for hot-100 from YYYY-MM-DD is more than 7 days old, fetching new data` - New data is being fetched
- `No existing chart data for hot-100, fetching new data` - First-time fetch
- `Force update requested for hot-100 chart` - Forced update is occurring

This optimization reduces API calls while ensuring the application always has Billboard chart data that aligns with other collected data.