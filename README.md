# Multi-API Data Collector

A command-line utility for collecting and storing data from multiple API sources (Bee AI and Limitless) into a database and JSON files.

## Overview

This tool connects to multiple AI services (Bee AI and Limitless), retrieves various types of personal data, and stores them in both a local SQLite database and JSON files organized by API provider.

### Data Types Collected

**From Bee AI:**
- Conversations (with summaries, locations, and timestamps)
- Facts (text snippets with timestamps)
- Todos (tasks with completion status)

**From Limitless:**
- Lifelogs (timestamped entries with content)

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
   ```

## Usage

Run the CLI tool to fetch and store data:

```bash
python app_new.py
```

The tool will:
1. Connect to both APIs using the provided credentials
2. Fetch all available data of each type (conversations, facts, todos, lifelogs)
3. Store the data in a SQLite database with deduplication
4. Save the deduplicated data to JSON files in the `data` directory

## Data Storage

### Database

Data is stored in a SQLite database with the following tables:
- `bee_conversations`: Conversation records from Bee API
- `bee_facts`: Fact records from Bee API
- `bee_todos`: Todo records from Bee API
- `limitless_lifelogs`: Lifelog records from Limitless API

Each table includes the raw data as JSON along with extracted fields for easy querying.

### JSON Files

Data is also stored in JSON files within the `data` directory:
- `data/bee/`: Contains JSON files for Bee API data
  - `conversations_TIMESTAMP.json`
  - `facts_TIMESTAMP.json`
  - `todos_TIMESTAMP.json`
- `data/limitless/`: Contains JSON files for Limitless API data
  - `lifelogs_TIMESTAMP.json`

## Additional Scripts

- `update_lifelog_timestamps.py`: Updates timestamps for existing Limitless lifelogs in the database
- `check_api_key.py`: Tests connectivity with the Bee API
- `check_limitless_api_key.py`: Tests connectivity with the Limitless API

## Troubleshooting

If you encounter API connection issues:
1. Verify your API keys are correctly set as environment variables
2. Run the API key check scripts to test connectivity
3. Check your network connection and any firewall settings

## License

[Specify your license information here]