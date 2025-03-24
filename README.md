# Multi-API Data Collector

A command-line utility for collecting and storing data from multiple API sources (Bee AI, Limitless, OpenWeatherMap, Billboard, and IMDB) into a database and JSON files, with support for importing and enriching Netflix viewing history.

## Overview

This tool connects to multiple services (Bee AI, Limitless, OpenWeatherMap, Billboard Charts, and IMDB), retrieves various types of personal data and contextual information, and stores them in both a PostgreSQL database and JSON files organized by API provider. It also supports importing Netflix viewing history from CSV files and enriching it with data from IMDB.

### Data Types Collected

**From Bee AI:**
- Conversations (with summaries, locations, and timestamps)
- Facts (text snippets with timestamps)
- ~~Todos~~ (disabled as per user request)

**From Limitless:**
- Lifelogs (timestamped entries with content)

**From OpenWeatherMap:**
- Weather data (based on location coordinates from Bee conversations or default location)

**From Billboard Charts API:**
- Chart data (Hot 100, Billboard 200, etc.)
- Chart entries with rank, title, artist, and other metadata

**From IMDB API:**
- Movie and TV show information
- Used to enrich Netflix viewing history

**From Netflix:**
- Viewing history (imported from CSV export)
- Series and movie details with intelligent series deduplication

## Requirements

- Python 3.8+
- Required Python packages:
  - beeai (for Bee API integration)
  - sqlalchemy (for database operations)
  - psycopg2-binary (for PostgreSQL support)
  - python-dateutil (for date parsing)
  - aiohttp (for async API requests)
  - pyyaml (for configuration file parsing)
  - pytz (for timezone handling)
  - flask (for potential future web interface)

## Installation

1. Ensure Python 3.8+ is installed
2. Install required packages:
   ```
   pip install beeai sqlalchemy psycopg2-binary python-dateutil aiohttp pyyaml pytz flask
   ```
3. Set up environment variables for API access:
   ```
   export BEE_API_KEY="your_bee_api_key"
   export LIMITLESS_API_KEY="your_limitless_api_key"
   export OPENWEATHER_API_KEY="your_openweather_api_key"
   export BILLBOARD_API_KEY="your_billboard_api_key"  # From RapidAPI - Billboard Charts API
   export IMDB_API_KEY="your_imdb_api_key"            # From RapidAPI - IMDB API
   ```

4. Configure default location in `config.yml` (optional):
   ```yaml
   # Default location to use when no coordinates are available from Bee API
   default_location:
     name: "San Francisco"  # Human-readable name of the location
     latitude: 37.7749      # Latitude coordinate
     longitude: -122.4194   # Longitude coordinate

   # Weather settings
   weather:
     units: "metric"        # Units for weather data: metric, imperial, or standard
     max_age_hours: 24      # Maximum age of weather data before fetching new data
   ```

## Usage

Run the CLI tool to fetch and store data from all sources:

```bash
python app.py
```

The tool will:
1. Connect to all APIs using the provided credentials
2. Fetch all available data of each type (conversations, facts, lifelogs)
3. Process location data from Bee API conversations or use default location
4. Fetch weather data for locations with coordinates
5. Check if Billboard chart data needs to be updated (updates once a week)
6. Store the data in a PostgreSQL database with deduplication
7. Save the deduplicated data to JSON files in the `data` directory if debug mode is enabled

### Netflix Operations

Import Netflix viewing history from a CSV file:

```bash
python app.py --netflix-csv path/to/NetflixViewingHistory.csv
```

Enrich Netflix data with IMDB information:

```bash
python app.py --enrich-netflix --enrich-limit 50
```

Remove duplicate Netflix series entries:

```bash
python app.py --deduplicate-netflix
```

Enable debug mode to save data to JSON files:

```bash
python app.py --debug
```

You can combine multiple operations:

```bash
python app.py --netflix-csv path/to/NetflixViewingHistory.csv --enrich-netflix --debug
```

## Data Storage

### Database

Data is stored in a PostgreSQL database with the following tables:
- `bee_conversations`: Conversation records from Bee API with location coordinates
- `bee_facts`: Fact records from Bee API
- `bee_todos`: Todo records from Bee API (disabled but schema preserved)
- `limitless_lifelogs`: Lifelog records from Limitless API
- `weather_data`: Weather records from OpenWeatherMap API
- `billboard_chart_items`: Chart data from Billboard Charts API
- `netflix_history_items`: Netflix viewing history with dates and parsed episode information
- `netflix_title_info`: Enriched Netflix title data with IMDB information

Each table includes the raw data as JSON along with extracted fields for easy querying.

### JSON Files

Data is also stored in JSON files within the `data` directory when debug mode is enabled:
- `data/bee/`: Contains JSON files for Bee API data
  - `conversations_TIMESTAMP.json`
  - `facts_TIMESTAMP.json`
- `data/limitless/`: Contains JSON files for Limitless API data
  - `lifelogs_TIMESTAMP.json`
- `data/openweather/`: Contains JSON files for OpenWeatherMap API data
  - `weather_TIMESTAMP.json`
- `data/billboard/`: Contains JSON files for Billboard Charts API data
  - `hot100_TIMESTAMP.json`
- `data/netflix/`: Contains JSON files for Netflix viewing history
  - `netflix_history_TIMESTAMP.json`
- `data/imdb/`: Contains JSON files for IMDB title data
  - `imdb_search_TIMESTAMP.json`

## Additional Scripts

### General Utilities
- `update_lifelog_timestamps.py`: Updates timestamps for existing Limitless lifelogs in the database
- `check_api_key.py`: Tests connectivity with the Bee API
- `check_limitless_api_key.py`: Tests connectivity with the Limitless API
- `check_billboard_api_key.py`: Tests connectivity with the Billboard Charts API
- `check_imdb_api_key.py`: Tests connectivity with the IMDB API
- `config_loader.py`: Loads configuration settings from config.yml

### Netflix Utilities
- `clean_netflix_titles.py`: Removes special characters from Netflix titles for better matching
- `clean_netflix_episode_titles.py`: Cleans episode indicators from Netflix series titles
- `deduplicate_netflix_series.py`: Ensures only one episode per series is kept in the database
- `remove_duplicate_netflix_series.py`: Removes duplicate series from previous imports
- `netflix_importer.py`: Core module for importing and enriching Netflix viewing history
- `test_netflix_imdb.py`: Tests IMDB search with Netflix titles
- `test_netflix_enrichment.py`: Tests enriching Netflix data with IMDB information

## Configuration

The `config.yml` file allows customization of the application's behavior:

1. **Default Location**: If Bee API conversations don't include coordinates, the application will fall back to this location for weather data.
   ```yaml
   default_location:
     name: "San Francisco"
     latitude: 37.7749
     longitude: -122.4194
   ```

2. **Weather Settings**: Configure units and caching behavior for weather data.
   ```yaml
   weather:
     units: "metric"        # metric, imperial, or standard
     max_age_hours: 24      # Hours before refreshing cached weather data
   ```

## Troubleshooting

### API Connection Issues
If you encounter API connection issues:
1. Verify your API keys are correctly set as environment variables
2. Run the API key check scripts to test connectivity
3. Check your network connection and any firewall settings

### Weather Data Issues
If you're not seeing weather data:
1. Check that your OPENWEATHER_API_KEY is correctly set
2. Verify that either Bee API conversations include coordinates or you've set up a default location in config.yml
3. Check the log output for any API errors from OpenWeatherMap

### Netflix Import Issues
If you're having problems with Netflix viewing history import:
1. Ensure your CSV file is in the correct format (with "Title" and "Date" columns)
2. Check if your CSV file uses a different date format than expected
3. Run with the `--debug` flag to see more detailed error messages
4. For duplicate series issues, run `python app.py --deduplicate-netflix` to clean up the database

### IMDB Enrichment Issues
If Netflix enrichment with IMDB data isn't working well:
1. Verify your IMDB_API_KEY is correctly set
2. Check that your internet connection is stable (IMDB API can be rate-limited)
3. Try adjusting the `--enrich-limit` parameter to process fewer titles at once
4. For specific titles that aren't matching correctly, check the title format in your CSV file

## License

[Specify your license information here]