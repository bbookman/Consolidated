# Multi-API Data Collector

A command-line utility for collecting and storing data from multiple API sources (Bee AI, Limitless, and OpenWeatherMap) into a database and JSON files.

## Overview

This tool connects to multiple services (Bee AI, Limitless, and OpenWeatherMap), retrieves various types of personal data and contextual information, and stores them in both a PostgreSQL database and JSON files organized by API provider.

### Data Types Collected

**From Bee AI:**
- Conversations (with summaries, locations, and timestamps)
- Facts (text snippets with timestamps)
- ~~Todos~~ (disabled as per user request)

**From Limitless:**
- Lifelogs (timestamped entries with content)

**From OpenWeatherMap:**
- Weather data (based on location coordinates from Bee conversations or default location)

## Requirements

- Python 3.8+
- Required Python packages:
  - beeai (for Bee API integration)
  - sqlalchemy (for database operations)
  - psycopg2-binary (for PostgreSQL support)
  - python-dateutil (for date parsing)
  - aiohttp (for async API requests)

## Installation

1. Ensure Python 3.8+ is installed
2. Install required packages:
   ```
   pip install beeai sqlalchemy psycopg2-binary python-dateutil aiohttp
   ```
3. Set up environment variables for API access:
   ```
   export BEE_API_KEY="your_bee_api_key"
   export LIMITLESS_API_KEY="your_limitless_api_key"
   export OPENWEATHER_API_KEY="your_openweather_api_key"
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

Run the CLI tool to fetch and store data:

```bash
python app.py
```

The tool will:
1. Connect to all APIs using the provided credentials
2. Fetch all available data of each type (conversations, facts, lifelogs)
3. Process location data from Bee API conversations or use default location
4. Fetch weather data for locations with coordinates
5. Store the data in a PostgreSQL database with deduplication
6. Save the deduplicated data to JSON files in the `data` directory

## Data Storage

### Database

Data is stored in a PostgreSQL database with the following tables:
- `bee_conversations`: Conversation records from Bee API with location coordinates
- `bee_facts`: Fact records from Bee API
- `bee_todos`: Todo records from Bee API (disabled but schema preserved)
- `limitless_lifelogs`: Lifelog records from Limitless API
- `weather_data`: Weather records from OpenWeatherMap API

Each table includes the raw data as JSON along with extracted fields for easy querying.

### JSON Files

Data is also stored in JSON files within the `data` directory:
- `data/bee/`: Contains JSON files for Bee API data
  - `conversations_TIMESTAMP.json`
  - `facts_TIMESTAMP.json`
- `data/limitless/`: Contains JSON files for Limitless API data
  - `lifelogs_TIMESTAMP.json`
- `data/openweather/`: Contains JSON files for OpenWeatherMap API data
  - `weather_TIMESTAMP.json`

## Additional Scripts

- `update_lifelog_timestamps.py`: Updates timestamps for existing Limitless lifelogs in the database
- `check_api_key.py`: Tests connectivity with the Bee API
- `check_limitless_api_key.py`: Tests connectivity with the Limitless API
- `config_loader.py`: Loads configuration settings from config.yml

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

If you encounter API connection issues:
1. Verify your API keys are correctly set as environment variables
2. Run the API key check scripts to test connectivity
3. Check your network connection and any firewall settings

If you're not seeing weather data:
1. Check that your OPENWEATHER_API_KEY is correctly set
2. Verify that either Bee API conversations include coordinates or you've set up a default location in config.yml
3. Check the log output for any API errors from OpenWeatherMap

## License

[Specify your license information here]