# Billboard Chart Data Update Logic

## Overview

Billboard chart data (Hot 100) is updated weekly, not daily. This document explains how the application manages Billboard data updates to avoid unnecessary API calls.

## How It Works

1. **Weekly Update Check**: The application checks if the stored Billboard chart data is more than 7 days old before attempting to fetch new data.

2. **Data Reuse**: If the existing data is less than 7 days old, the application will use the data from the database instead of making a new API call.

3. **Forced Updates**: If needed, you can force an update regardless of the data age by uncommenting and using the following code in `app.py`:
   ```python
   # Use force_update=True to test the forced update functionality
   hot100_chart = await fetch_billboard_chart("hot-100", force_update=True)
   ```

4. **Historical Data**: To fetch chart data for a specific date, modify the function call to include a date parameter:
   ```python
   # Fetch chart data for a specific date
   hot100_chart = await fetch_billboard_chart("hot-100", date="2025-02-15")
   ```

## Implementation Details

The update logic is controlled by two key functions:

1. `should_update_billboard_chart(chart_name, days_threshold=7)` in `database_handler.py` - Determines if a chart needs updating based on its age.

2. `fetch_billboard_chart(chart_name, date=None, force_update=False)` in `app.py` - Handles the decision to reuse or fetch new data.

## Logs

Look for these log messages to understand what's happening with Billboard data:

- `Using existing chart data for hot-100 from YYYY-MM-DD (less than 7 days old)` - Data is being reused.
- `Chart data for hot-100 from YYYY-MM-DD is more than 7 days old, fetching new data` - New data is being fetched.
- `No existing chart data for hot-100, fetching new data` - First-time fetch.
- `Force update requested for hot-100 chart` - Forced update is occurring.

This optimization reduces API calls while ensuring the application always has relatively current Billboard chart data.