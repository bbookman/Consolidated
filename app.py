#!/usr/bin/env python3
"""
Multi-API Data Collection CLI

This script provides a command-line interface for collecting and storing data from 
multiple APIs (Bee AI, Limitless, OpenWeatherMap, Billboard) into a database.
Also supports importing Netflix viewing history from CSV files.

When debug mode is enabled, all data is also saved to JSON files in the /data directory.
"""

import sys
import os
import json
import traceback
import logging
import asyncio
import re
from datetime import datetime
import pytz
import argparse
from beeai import Bee

from limitless_api import LimitlessAPI
from openweather_api import OpenWeatherAPI
import netflix_importer
from billboard_api import BillboardAPI
import database_handler as db
import config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variables
app_debug_mode = False  # Default to False, will be set by command line arguments

# Initialize API clients
bee = None
limitless = None
openweather = None
billboard = None

def initialize_apis():
    """Initialize API clients with keys from environment variables"""
    global bee, limitless, openweather, billboard
    
    # Initialize Bee API
    bee_api_key = os.environ.get('BEE_API_KEY')
    if bee_api_key:
        bee = Bee(api_key=bee_api_key)
        logger.info("Bee API client initialized successfully")
    else:
        logger.warning("BEE_API_KEY not found in environment variables")

    # Initialize Limitless API
    limitless_api_key = os.environ.get('LIMITLESS_API_KEY')
    if limitless_api_key:
        limitless = LimitlessAPI(api_key=limitless_api_key)
        logger.info("Limitless API client initialized successfully")
    else:
        logger.warning("LIMITLESS_API_KEY not found in environment variables")
        
    # Initialize OpenWeatherMap API
    openweather_api_key = os.environ.get('OPENWEATHER_API_KEY')
    if openweather_api_key:
        openweather = OpenWeatherAPI(api_key=openweather_api_key)
        logger.info("OpenWeatherMap API client initialized successfully")
    else:
        logger.warning("OPENWEATHER_API_KEY not found in environment variables")
        
    # Initialize Billboard Charts API
    billboard_api_key = os.environ.get('BILLBOARD_API_KEY')
    if billboard_api_key:
        billboard = BillboardAPI(api_key=billboard_api_key)
        logger.info("Billboard Charts API client initialized successfully")
    else:
        logger.warning("BILLBOARD_API_KEY not found in environment variables")

def clean_markdown(text):
    """
    Remove Markdown formatting from text.
    
    Args:
        text: String containing Markdown formatting
        
    Returns:
        String with Markdown formatting removed
    """
    if not text:
        return text
    
    # Handle different types
    if isinstance(text, list):
        return [clean_markdown(item) for item in text]
    if not isinstance(text, str):
        return text
    
    # Remove any duplicate "Summary:" or "Atmosphere:" headings that might exist within the text
    text = re.sub(r'(?i)^Summary:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Atmosphere:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Key Take ?Aways:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Key Takeaways:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Remove section heading variations more thoroughly
    text = re.sub(r'(?i)^#+\s*Summary:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Atmosphere:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Key Take ?Aways:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Key Takeaways:?.*?\n', '', text, flags=re.MULTILINE)
    
    # Remove Markdown headers (e.g., ## Header)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold formatting (e.g., **bold**)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # Remove italic formatting (e.g., *italic*)
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'\1', text)
    
    # Remove bullet points
    text = re.sub(r'^\s*[\*\-•]\s+', '', text, flags=re.MULTILINE)
    
    # Remove Markdown links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules
    text = re.sub(r'^\s*[-_*]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

def format_conversation(conv):
    """Format a conversation object from the Bee API for display/storage"""
    # Extract summary, atmosphere, and key takeaways sections from the summary text
    full_text = conv.get("summary", "")
    
    # Initialize summary, atmosphere, and key takeaways
    summary_text = ""
    atmosphere_text = ""
    key_takeaways_text = ""
    
    # Handle None summary value
    if full_text is None:
        summary_text = "No summary available"
    else:
        # Split the text into sections based on different possible headers
        atmosphere_patterns = [
            r'## Atmosphere\s*\n',
            r'### Atmosphere\s*\n', 
            r'## Atmosphere:',
            r'### Atmosphere:',
            r'\*\*Atmosphere\*\*:?',
            r'Atmosphere:'
        ]
        
        # Define patterns for Key Takeaways
        key_takeaways_patterns = [
            r'## Key Take[aA]ways\s*\n',
            r'### Key Take[aA]ways\s*\n',
            r'## Key Take[aA]ways:',
            r'### Key Take[aA]ways:',
            r'\*\*Key Take[aA]ways\*\*:?',
            r'Key Take[aA]ways:',
            r'## Key Takeaways\s*\n',
            r'### Key Takeaways\s*\n',
            r'## Key Takeaways:',
            r'### Key Takeaways:',
            r'\*\*Key Takeaways\*\*:?',
            r'Key Takeaways:'
        ]
        
        # First, extract Summary section
        summary_patterns = [
            r'## Summary\s*\n',
            r'### Summary\s*\n',
            r'## Summary:',
            r'### Summary:',
            r'\*\*Summary\*\*:?',
            r'Summary:'
        ]
        
        # Try to extract Summary section
        summary_match = None
        for pattern in summary_patterns:
            match = re.search(pattern, full_text)
            if match:
                summary_match = match
                break
        
        # Extract text after summary header
        if summary_match:
            start_idx = summary_match.end()
            # Find where next section starts (if it exists)
            next_section_start = len(full_text)
            for pattern in atmosphere_patterns + key_takeaways_patterns:
                match = re.search(pattern, full_text)
                if match and match.start() > start_idx:
                    next_section_start = min(next_section_start, match.start())
            
            # Extract summary text
            summary_text = full_text[start_idx:next_section_start].strip()
        else:
            # No summary header found, use the whole text
            summary_text = full_text.strip()
        
        # Try to extract Atmosphere section
        atmosphere_match = None
        for pattern in atmosphere_patterns:
            match = re.search(pattern, full_text)
            if match:
                atmosphere_match = match
                break
        
        # Extract text after atmosphere header
        if atmosphere_match:
            start_idx = atmosphere_match.end()
            # Find where next section starts (if any)
            next_section_start = len(full_text)
            for pattern in key_takeaways_patterns + [r'## ', r'### ']:
                match = re.search(pattern, full_text[start_idx:])
                if match:
                    next_section_start = min(next_section_start, start_idx + match.start())
            
            # Extract atmosphere text
            atmosphere_text = full_text[start_idx:next_section_start].strip()
            
        # Try to extract Key Takeaways section
        key_takeaways_match = None
        for pattern in key_takeaways_patterns:
            match = re.search(pattern, full_text)
            if match:
                key_takeaways_match = match
                break
                
        # Extract text after key takeaways header
        if key_takeaways_match:
            start_idx = key_takeaways_match.end()
            # Find where next section starts (if any)
            next_section_start = len(full_text)
            next_section_patterns = [r'## ', r'### ']
            for pattern in next_section_patterns:
                match = re.search(pattern, full_text[start_idx:])
                if match:
                    next_section_start = min(next_section_start, start_idx + match.start())
            
            # Extract key takeaways text
            key_takeaways_text = full_text[start_idx:next_section_start].strip()
    
    # Get address from primary_location if it exists
    address = "No address"
    if conv.get("primary_location") and conv["primary_location"].get("address"):
        address = conv["primary_location"]["address"]
    
    latitude = None
    longitude = None
    if conv.get("primary_location") and conv["primary_location"].get("latitude") and conv["primary_location"].get("longitude"):
        latitude = conv["primary_location"]["latitude"]
        longitude = conv["primary_location"]["longitude"]
    
    # Extract start and end times
    start_time = None
    end_time = None
    created_at = None
    
    if conv.get("start_time"):
        start_time = conv["start_time"]
    if conv.get("end_time"):
        end_time = conv["end_time"]
    if conv.get("created_at"):
        created_at = conv["created_at"]
    
    # Convert key takeaways text to list if it exists
    key_takeaways_list = None
    if key_takeaways_text:
        # Split by newlines and handle bullet points
        key_takeaways_items = key_takeaways_text.strip().split('\n')
        key_takeaways_list = []
        for item in key_takeaways_items:
            # Remove bullet points or dashes if they exist
            cleaned_item = re.sub(r'^[\*\-•]+\s*', '', item.strip())
            if cleaned_item:  # Only add non-empty items
                key_takeaways_list.append(clean_markdown(cleaned_item))
    
    # Clean Markdown from summary and atmosphere text
    summary_text = clean_markdown(summary_text)
    atmosphere_text = clean_markdown(atmosphere_text)
    
    return {
        "Title": f"Conversation on {created_at[:10] if created_at else 'Unknown Date'}",
        "Summary": summary_text,
        "Atmosphere": atmosphere_text,
        "Key Takeaways": key_takeaways_list,
        "Address": address,
        "Start Time": start_time,
        "End Time": end_time,
        "Created At": created_at,
        "Latitude": latitude,
        "Longitude": longitude
    }

def format_fact(fact):
    """Format a fact object from the Bee API for display/storage"""
    return {
        "Text": fact.get("text", "No text available"),
        "Created At": fact.get("created_at", "Unknown date")
    }

def format_todo(todo):
    """Format a todo object from the Bee API for display/storage"""
    return {
        "Task": todo.get("task", "No task description"),
        "Completed": "Yes" if todo.get("completed", False) else "No",
        "Created At": todo.get("created_at", "Unknown date")
    }

def format_lifelog(log):
    """Format a lifelog object from the Limitless API for display/storage"""
    title = "No title available"
    description = "No description available"
    tags = "No tags"
    log_type = "Unknown type"
    created_at = "Unknown date"
    updated_at = None
    
    # Extract title from contents if possible
    contents = log.get("contents", [])
    if contents and isinstance(contents, list):
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "heading1" and item.get("content"):
                title = item.get("content")
                break
    
    # Use metadata or fallback to contents for description
    if log.get("metadata") and log.get("metadata").get("description"):
        description = log.get("metadata").get("description")
    elif contents and len(contents) > 1:
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "heading2" and item.get("content"):
                description = item.get("content")
                break
    
    # Get tags if available
    if log.get("tags") and isinstance(log.get("tags"), list):
        tags = ", ".join(log.get("tags"))
    
    # Get type if available
    if log.get("type"):
        log_type = log.get("type")
    
    # Get timestamps
    if log.get("createdAt"):
        created_at = log.get("createdAt")
    if log.get("updatedAt"):
        updated_at = log.get("updatedAt")
    
    return {
        "Title": title,
        "Description": description,
        "Tags": tags,
        "Type": log_type,
        "Created At": created_at,
        "Updated At": updated_at
    }

async def fetch_all_pages(fetch_func, user_id):
    """
    Fetch all pages of data from a paginated API endpoint
    
    Args:
        fetch_func: The API function to call (e.g., bee.get_conversations)
        user_id: The user ID to fetch data for (typically "me")
        
    Returns:
        A list of all items fetched across all pages
    """
    logger.info(f"Fetching all pages for {fetch_func.__name__} and user {user_id}")
    
    try:
        # Get the first page to determine total pages
        response = await fetch_func(user_id, page=1)
        logger.info(f"First response type: {type(response)}")
        
        # Handle different response formats
        all_items = []
        
        if isinstance(response, dict):
            # Add items from first page
            if 'data' in response and isinstance(response['data'], dict) and 'lifelogs' in response['data']:
                # New API format with data.lifelogs structure
                all_items.extend(response['data']['lifelogs'])
                total_pages = response.get('meta', {}).get('pages', 1)
            else:
                # Standard API format
                item_key = next((key for key in ['conversations', 'facts', 'todos', 'lifelogs'] if key in response), None)
                if item_key:
                    all_items.extend(response[item_key])
                    total_pages = response.get('totalPages', 1)
                else:
                    # Unknown format, just return the response
                    return response
            
            logger.info(f"Found {total_pages} total pages")
            
            # Fetch remaining pages
            for page in range(2, total_pages + 1):
                logger.info(f"Fetching page {page} of {total_pages}")
                page_response = await fetch_func(user_id, page=page)
                
                # Add items from this page
                if 'data' in page_response and isinstance(page_response['data'], dict) and 'lifelogs' in page_response['data']:
                    all_items.extend(page_response['data']['lifelogs'])
                else:
                    item_key = next((key for key in ['conversations', 'facts', 'todos', 'lifelogs'] if key in page_response), None)
                    if item_key:
                        all_items.extend(page_response[item_key])
        
        elif isinstance(response, list):
            # Direct list response
            all_items = response
        
        logger.info(f"Fetched {len(all_items)} items in total")
        return all_items
        
    except Exception as e:
        logger.error(f"Error fetching all pages: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def save_to_file(data, data_type, original_data, debug_mode=False):
    """
    Save data to JSON files in the appropriate API-specific directory if debug mode is enabled
    
    Args:
        data: List of formatted data items (not used - kept for backward compatibility)
        data_type: Type of data (conversations, facts, todos, lifelogs, weather)
        original_data: Raw data from API
        debug_mode: If True, save data to file; if False, skip file creation
    """
    # Log debug mode status for debugging
    print(f"DEBUG INFO - save_to_file called for {data_type} with debug_mode={debug_mode}")
    
    # Skip file creation if debug mode is disabled
    if not debug_mode:
        print(f"Debug mode disabled - skipping JSON file creation for {data_type}")
        return True
        
    # Check if there's any data to save
    if not original_data or (isinstance(original_data, dict) and 
                            all(not original_data.get(k) for k in original_data)):
        logger.info(f"No data to save for {data_type}, skipping file creation")
        return True
        
    try:
        # Determine which API the data is from
        api_name = "bee"
        if data_type == "lifelogs" or data_type.startswith("db_lifelogs"):
            api_name = "limitless"
        elif data_type == "weather" or data_type.startswith("db_weather"):
            api_name = "openweather"
        elif data_type.startswith("billboard_"):
            api_name = "billboard"
        elif data_type.startswith("netflix_"):
            api_name = "netflix"
        elif data_type.startswith("imdb_"):
            api_name = "imdb"
            
        # Create data directory only in debug mode
        # Double-check debug_mode to ensure we never create directories without it
        if debug_mode:
            data_dir = os.path.join("data", api_name)
            os.makedirs(data_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{data_type}_{timestamp}.json"
            filepath = os.path.join(data_dir, filename)
            
            logger.info(f"Using API directory: {os.path.abspath(data_dir)}")
            
            # Check if we should skip saving if the data is the same as the latest file
            last_file = find_latest_file(data_dir, data_type)
            if last_file:
                with open(last_file, 'r') as f:
                    try:
                        existing_data = json.load(f)
                        if existing_data == original_data:
                            logger.info(f"Data for {data_type} is identical to the latest file, not saving")
                            return True
                    except json.JSONDecodeError:
                        # If there's an error parsing the previous file, we'll save a new one
                        pass
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(original_data, f, indent=2)
                
            logger.info(f"Saved {data_type} data to {filepath}")
            return True
        else:
            logger.warning(f"Attempted to create JSON file without debug mode enabled")
            return False
        
    except Exception as e:
        logger.error(f"Error saving {data_type} to file: {str(e)}")
        return False

async def fetch_weather_for_location(latitude, longitude, units="metric"):
    """
    Fetch weather data for a given location and store it in the database.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        units: Units of measurement (metric, imperial, or standard)
        
    Returns:
        Weather data dictionary if successful, None otherwise
    """
    if not openweather:
        logger.warning("OpenWeatherMap API client not initialized - skipping weather fetch")
        return None
        
    try:
        # First check if we already have recent weather data for this location
        existing_weather = db.get_latest_weather_data_for_location(latitude, longitude)
        if existing_weather:
            logger.info(f"Found recent weather data for location ({latitude}, {longitude})")
            return json.loads(existing_weather.raw_data)
            
        # Fetch new weather data from OpenWeatherMap API
        logger.info(f"Fetching weather data for location ({latitude}, {longitude})")
        result = await openweather.get_current_weather(latitude, longitude, units=units)
        
        # Check if we got an error
        if result.get("error"):
            logger.error(f"Error fetching weather data: {result['error']}")
            return None
            
        # Store weather data in database
        weather_data = result.get("weather")
        if weather_data:
            logger.info(f"Storing weather data for location ({latitude}, {longitude})")
            db_result = db.store_weather_data(weather_data)
            logger.info(f"Weather data stored: {db_result['added']} added, {db_result['skipped']} skipped")
            return weather_data
        else:
            logger.warning(f"No weather data returned for location ({latitude}, {longitude})")
            return None
            
    except Exception as e:
        logger.error(f"Error in fetch_weather_for_location: {str(e)}")
        logger.error(traceback.format_exc())
        return None

async def fetch_billboard_chart(chart_name="hot-100", date=None, force_update=False):
    """
    Fetch Billboard chart data and store it in the database.
    Only fetches new data if one of these conditions is met:
    1. No data exists in the database
    2. Data exists but is older than 7 days (and force_update is not set to False)
    3. force_update is explicitly set to True
    
    Args:
        chart_name: Name of the chart to retrieve (hot-100, billboard-200, etc.)
        date: Optional date string in format YYYY-MM-DD for historical chart
        force_update: If True, force fetch new data; if False, never update even if data is old
        
    Returns:
        Chart data dictionary if successful, None otherwise
    """
    if not billboard:
        logger.warning("Billboard API client not initialized - skipping chart fetch")
        return None
        
    try:
        # If a specific date is requested, fetch that date directly
        if date:
            logger.info(f"Specific date requested: {date}, fetching that chart")
            # First check if we already have data for this date
            chart_items = db.get_billboard_chart_items_from_db(chart_name=chart_name, chart_date=date)
            if chart_items and not force_update:
                logger.info(f"Using existing chart data for {chart_name} from {date}")
                # Convert DB objects to dictionary for return
                entries = []
                for item in chart_items:
                    entry_data = json.loads(item.raw_data)
                    entries.append(entry_data)
                    
                return {
                    "chart": {
                        "name": chart_name,
                        "date": date,
                        "entries": entries
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # If we don't have data for this date or force_update is True, fetch it
                return await fetch_specific_chart(chart_name, date)
        
        # Check if we already have the chart data and if it needs updating
        should_update, latest_chart_date = db.should_update_billboard_chart(chart_name)
        
        # If force_update is explicitly False, never update regardless of age
        if force_update is False:
            should_update = False
        
        if latest_chart_date and not should_update and force_update is not True:
            # If we already have data and shouldn't update, use the saved data
            logger.info(f"Using existing chart data for {chart_name} from {latest_chart_date}")
            chart_items = db.get_billboard_chart_items_from_db(chart_name=chart_name, chart_date=latest_chart_date)
            if chart_items:
                # Convert DB objects to dictionary for return
                entries = []
                for item in chart_items:
                    entry_data = json.loads(item.raw_data)
                    entries.append(entry_data)
                    
                return {
                    "chart": {
                        "name": chart_name,
                        "date": latest_chart_date,
                        "entries": entries
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # If we need to update (more than a week old or no data) or force_update is True
        if should_update or force_update is True:
            if force_update is True:
                logger.info(f"Force update requested for {chart_name} chart")
            else:
                if latest_chart_date:
                    logger.info(f"Chart data for {chart_name} from {latest_chart_date} is more than 7 days old, fetching new data")
                else:
                    logger.info(f"No existing chart data for {chart_name}, fetching new data")
                    
            # Fetch new chart data from Billboard API
            return await fetch_specific_chart(chart_name, None)  # None means latest chart
            
    except Exception as e:
        logger.error(f"Error in fetch_billboard_chart: {str(e)}")
        logger.error(traceback.format_exc())
        return None

async def fetch_specific_chart(chart_name, date=None):
    """
    Helper function to fetch specific chart data from Billboard API.
    
    Args:
        chart_name: Name of the chart to retrieve
        date: Optional date string in format YYYY-MM-DD
        
    Returns:
        Chart data dictionary if successful, None otherwise
    """
    try:
        logger.info(f"Fetching {chart_name} chart data{' for date '+date if date else ''}")
        result = await billboard.get_chart(chart_name, date)
        
        # Check if we got an error
        if result.get("error"):
            logger.error(f"Error fetching chart data: {result['error']}")
            return None
            
        # Store chart data in database
        chart_data = result.get("chart")
        if chart_data:
            logger.info(f"Storing chart data for {chart_name}")
            db_result = db.store_billboard_chart_items(result, chart_name)
            logger.info(f"Chart data stored: {db_result['added']} added, {db_result['skipped']} skipped")
            return result
        else:
            logger.warning(f"No chart data returned for {chart_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error in fetch_specific_chart: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def find_latest_file(directory, prefix):
    """Find the most recent file with the given prefix in the directory"""
    try:
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                if f.startswith(prefix) and f.endswith('.json')]
        if not files:
            return None
        return max(files, key=os.path.getmtime)
    except Exception as e:
        logger.error(f"Error finding latest file: {str(e)}")
        return None

async def run_cli_async():
    """
    CLI entry point for the application (async version). Fetches data from API, stores in database,
    and then saves database content to JSON files if debug mode is enabled.
    """
    # Access the global debug mode flag
    global app_debug_mode
    try:
        # Step 1: Fetch data from API and store in database
        print("Fetching conversations from API...")
        conversations = await fetch_all_pages(bee.get_conversations, "me")
        if isinstance(conversations, dict):
            conversations_list = conversations.get('conversations', [])
        else:
            conversations_list = conversations
        print(f"Fetched {len(conversations_list)} conversations")
        
        print("Fetching facts from API...")
        facts = await fetch_all_pages(bee.get_facts, "me")
        if isinstance(facts, dict):
            facts_list = facts.get('facts', [])
        else:
            facts_list = facts
        print(f"Fetched {len(facts_list)} facts")
        
        print("Todos fetching disabled...")
        todos_list = []
        # Comment out todos fetching to avoid API calls to /v1/{userId}/todos endpoint
        # print("Fetching todos from API...")
        # todos = await fetch_all_pages(bee.get_todos, "me")
        # if isinstance(todos, dict):
        #     todos_list = todos.get('todos', [])
        # else:
        #     todos_list = todos
        # print(f"Fetched {len(todos_list)} todos")
        
        # Fetch lifelogs from Limitless API if available
        lifelogs_list = []
        if limitless:
            print("Fetching lifelogs from Limitless API...")
            try:
                # Get the latest lifelog date from the database to use as a filter
                latest_date = db.get_latest_lifelog_date()
                if latest_date:
                    print(f"Found latest lifelog date in database: {latest_date}")
                    print(f"Fetching only lifelogs since {latest_date}...")
                else:
                    print("No existing lifelogs found in database, fetching all available lifelogs...")
                
                # Create a wrapper function that doesn't require user_id parameter
                async def get_lifelogs_wrapper(dummy=None, page=1):
                    return await limitless.get_lifelogs(page=page, date=latest_date)
                
                lifelogs = await fetch_all_pages(get_lifelogs_wrapper, "dummy")
                print(f"Debug - lifelogs type: {type(lifelogs)}")
                
                # Fix case where lifelogs_list is a list with a string like ['lifelogs']
                if isinstance(lifelogs, list) and len(lifelogs) == 1 and isinstance(lifelogs[0], str) and lifelogs[0] == 'lifelogs':
                    print("Detected invalid lifelog list format, replacing with empty list")
                    lifelogs_list = []
                # Normal processing for dictionary response with 'lifelogs' key
                elif isinstance(lifelogs, dict):
                    if 'data' in lifelogs and isinstance(lifelogs['data'], dict) and 'lifelogs' in lifelogs['data']:
                        # New API format
                        lifelogs_list = lifelogs['data']['lifelogs']
                    else:
                        # Standard format
                        lifelogs_list = lifelogs.get('lifelogs', [])
                    print(f"Debug - lifelogs_list type: {type(lifelogs_list)}")
                    print(f"Debug - lifelogs_list content sample: {str(lifelogs_list)[:100]}")
                # Fallback for direct list
                else:
                    # Only use direct list if it contains dictionaries/objects, not strings
                    if isinstance(lifelogs, list) and (not lifelogs or isinstance(lifelogs[0], dict)):
                        lifelogs_list = lifelogs
                    else:
                        lifelogs_list = []
                        print("Unexpected lifelogs format, using empty list")
                    print(f"Debug - lifelogs_list (direct) type: {type(lifelogs_list)}")
                    print(f"Debug - lifelogs_list (direct) content sample: {str(lifelogs_list)[:100]}")
                print(f"Fetched {len(lifelogs_list)} lifelogs")
            except Exception as e:
                print(f"Error fetching lifelogs: {str(e)}")
                print(traceback.format_exc())
        else:
            print("Limitless API client not initialized - skipping lifelogs")
        
        # Step 2: Store in database with deduplication
        print("Storing in database...")
        db_conversations_result = db.store_conversations(conversations_list)
        db_facts_result = db.store_facts(facts_list)
        db_todos_result = db.store_todos(todos_list)
        
        # Store lifelogs if available
        db_lifelogs_result = {"processed": 0, "added": 0, "skipped": 0}
        if lifelogs_list:
            db_lifelogs_result = db.store_lifelogs(lifelogs_list)
        
        # Print database results
        print(f"\nDatabase Results:")
        print(f"Conversations: {db_conversations_result['processed']} processed, {db_conversations_result['added']} added, {db_conversations_result['skipped']} skipped")
        print(f"Facts: {db_facts_result['processed']} processed, {db_facts_result['added']} added, {db_facts_result['skipped']} skipped")
        print(f"Todos: {db_todos_result['processed']} processed, {db_todos_result['added']} added, {db_todos_result['skipped']} skipped")
        print(f"Lifelogs: {db_lifelogs_result['processed']} processed, {db_lifelogs_result['added']} added, {db_lifelogs_result['skipped']} skipped")
        
        # Step 3: Retrieve from database and save to JSON files
        print("\nRetrieving from database and saving to JSON files...")
        
        # Get conversations from database
        print("Processing conversations from database...")
        db_conversations = db.get_conversations_from_db()
        print(f"Retrieved {len(db_conversations)} conversations from database")
        
        # Format data for saving
        formatted_conversations = []
        conversation_raw_data = []
        
        for conv in db_conversations:
            # Convert from SQLAlchemy object to dictionary
            formatted_conv = {
                "Summary": conv.summary if conv.summary else "No summary available",
                "Created At": conv.created_at.isoformat() if conv.created_at else "Unknown",
                "Address": conv.address if conv.address else "No address"
            }
            formatted_conversations.append(formatted_conv)
            
            # Get raw data if available
            if conv.raw_data:
                try:
                    conversation_raw_data.append(json.loads(conv.raw_data))
                except:
                    print(f"Warning: Could not parse raw_data for conversation {conv.id}")
        
        # Save conversations to file if debug mode is enabled
        saved_conv = save_to_file(
            formatted_conversations, 
            'conversations', 
            {'conversations': conversation_raw_data},
            app_debug_mode
        )
        if saved_conv and app_debug_mode:
            print("Successfully processed conversations to JSON")
        elif saved_conv:
            print("Conversations processed (not saved to JSON due to debug mode disabled)")
        
        # Get facts from database
        print("Processing facts from database...")
        db_facts = db.get_facts_from_db()
        print(f"Retrieved {len(db_facts)} facts from database")
        
        # Format data for saving
        formatted_facts = []
        fact_raw_data = []
        
        for fact in db_facts:
            # Convert from SQLAlchemy object to dictionary
            formatted_fact = {
                "Text": fact.text,
                "Created At": fact.created_at.isoformat() if fact.created_at else "Unknown"
            }
            formatted_facts.append(formatted_fact)
            
            # Get raw data if available
            if fact.raw_data:
                try:
                    fact_raw_data.append(json.loads(fact.raw_data))
                except:
                    print(f"Warning: Could not parse raw_data for fact {fact.id}")
        
        # Save facts to file if debug mode is enabled
        saved_facts = save_to_file(
            formatted_facts, 
            'facts', 
            {'facts': fact_raw_data},
            app_debug_mode
        )
        if saved_facts and app_debug_mode:
            print("Successfully processed facts to JSON")
        elif saved_facts:
            print("Facts processed (not saved to JSON due to debug mode disabled)")
        
        # Comment out todos processing 
        print("Todos processing disabled...")
        
        # # Get todos from database
        # print("Processing todos from database...")
        # db_todos = db.get_todos_from_db()
        # print(f"Retrieved {len(db_todos)} todos from database")
        # 
        # # Format data for saving
        # formatted_todos = []
        # todo_raw_data = []
        # 
        # for todo in db_todos:
        #     # Convert from SQLAlchemy object to dictionary
        #     formatted_todo = {
        #         "Task": todo.task,
        #         "Completed": "Yes" if todo.completed else "No",
        #         "Created At": todo.created_at.isoformat() if todo.created_at else "Unknown"
        #     }
        #     formatted_todos.append(formatted_todo)
        #     
        #     # Get raw data if available
        #     if todo.raw_data:
        #         try:
        #             todo_raw_data.append(json.loads(todo.raw_data))
        #         except:
        #             print(f"Warning: Could not parse raw_data for todo {todo.id}")
        # 
        # # Save todos to file if debug mode is enabled
        # saved_todos = save_to_file(
        #     formatted_todos, 
        #     'todos', 
        #     {'todos': todo_raw_data},
        #     app_debug_mode
        # )
        # if saved_todos:
        #     print("Successfully processed todos to JSON")
        
        # Get lifelogs from database if available
        if limitless:
            print("Processing lifelogs from database...")
            db_lifelogs = db.get_lifelogs_from_db()
            print(f"Retrieved {len(db_lifelogs)} lifelogs from database")
            
            # Format data for saving
            formatted_lifelogs = []
            lifelog_raw_data = []
            
            for lifelog in db_lifelogs:
                # Convert from SQLAlchemy object to dictionary
                formatted_lifelog = {
                    "Title": lifelog.title if lifelog.title else "No title available",
                    "Description": lifelog.description if lifelog.description else "No description available",
                    "Type": lifelog.log_type if lifelog.log_type else "Unknown type",
                    "Tags": lifelog.tags if lifelog.tags else "No tags",
                    "Created At": lifelog.created_at.isoformat() if lifelog.created_at else "Unknown",
                    "Updated At": lifelog.updated_at.isoformat() if lifelog.updated_at else "Unknown"
                }
                formatted_lifelogs.append(formatted_lifelog)
                
                # Get raw data if available
                if lifelog.raw_data:
                    try:
                        lifelog_raw_data.append(json.loads(lifelog.raw_data))
                    except:
                        print(f"Warning: Could not parse raw_data for lifelog {lifelog.id}")
            
            # Save lifelogs to file if debug mode is enabled
            saved_lifelogs = save_to_file(
                formatted_lifelogs, 
                'lifelogs', 
                {'lifelogs': lifelog_raw_data},
                app_debug_mode
            )
            if saved_lifelogs and app_debug_mode:
                print("Successfully processed lifelogs to JSON")
            elif saved_lifelogs:
                print("Lifelogs processed (not saved to JSON due to debug mode disabled)")
                
        # Fetch weather data for locations with coordinates
        if openweather:
            print("\nProcessing weather data...")
            try:
                # Step 1: Get all unique dates that have Bee, Netflix, or Limitless data
                data_dates = db.get_dates_with_data()
                if data_dates:
                    print(f"Found {len(data_dates)} unique dates with data")
                    
                    # Step 2: Check which dates need weather data (don't have it already)
                    dates_needing_weather = []
                    for date_str in data_dates:
                        if not db.check_weather_data_exists_for_date(date_str):
                            dates_needing_weather.append(date_str)
                    
                    if dates_needing_weather:
                        print(f"Found {len(dates_needing_weather)} dates that need weather data: {', '.join(dates_needing_weather[:5])}{' and more...' if len(dates_needing_weather) > 5 else ''}")
                        
                        # Get locations with coordinates from Bee conversations
                        conversations_with_coords = db.get_conversations_with_coordinates()
                                
                        # Initialize variables for weather data
                        weather_data_list = []
                        db_weather_results = {"processed": 0, "added": 0, "skipped": 0}
                        
                        if conversations_with_coords:
                            print(f"Found {len(conversations_with_coords)} locations with coordinates")
                            
                            # Process the first 5 locations to avoid API rate limits
                            for i, conv in enumerate(conversations_with_coords[:5]):
                                print(f"Processing location {i+1}/{min(5, len(conversations_with_coords))}: ({conv.latitude}, {conv.longitude})")
                                
                                # Fetch new weather data for this location
                                print(f"Fetching new weather data for location ({conv.latitude}, {conv.longitude})")
                                weather_data = await fetch_weather_for_location(conv.latitude, conv.longitude)
                                if weather_data:
                                    weather_data_list.append(weather_data)
                                    db_weather_results["processed"] += 1
                                    db_weather_results["added"] += 1
                        else:
                            print("No locations with coordinates found in Bee conversations")
                            
                            # Get default location from config file
                            default_location = config_loader.get_default_location()
                            if default_location:
                                lat, lon, name = default_location
                                print(f"Using default location from config: {name} ({lat}, {lon})")
                                
                                # Fetch weather data for default location
                                weather_config = config_loader.get_weather_config()
                                units = weather_config.get("units", "metric")
                                
                                print(f"Fetching new weather data for default location: {name}")
                                weather_data = await fetch_weather_for_location(lat, lon, units=units)
                                if weather_data:
                                    weather_data_list.append(weather_data)
                                    db_weather_results["processed"] += 1
                                    db_weather_results["added"] += 1
                                    print(f"Successfully retrieved weather data for default location: {name}")
                                else:
                                    print(f"Failed to retrieve weather data for default location: {name}")
                            else:
                                print("No default location configured in config.yml, skipping weather data processing")
                    else:
                        print("All dates already have weather data, skipping weather API calls")
                        
                        # Still retrieve existing weather data for JSON export if debug mode is enabled
                        if app_debug_mode:
                            print("Debug mode enabled - retrieving existing weather data for JSON export")
                            existing_weather = db.get_weather_data_from_db()
                            weather_data_list = [json.loads(w.raw_data) for w in existing_weather[:5]]  # Limit to 5 for performance
                            db_weather_results = {"processed": len(weather_data_list), "added": 0, "skipped": 0}
                else:
                    print("No dates with data found, skipping weather data processing")
                
                # Save weather data to file if we have any
                if weather_data_list:
                    print(f"Retrieved {len(weather_data_list)} weather data points")
                    
                    # Save to file if debug mode is enabled
                    saved_weather = save_to_file(
                        weather_data_list,
                        'weather',
                        {'weather': weather_data_list},
                        app_debug_mode
                    )
                    
                    if saved_weather and app_debug_mode:
                        print("Successfully processed weather data to JSON")
                    elif saved_weather:
                        print("Weather data processed (not saved to JSON due to debug mode disabled)")
                else:
                    print("No weather data to process")
            except Exception as e:
                print(f"Error processing weather data: {str(e)}")
                print(traceback.format_exc())
        else:
            print("\nOpenWeatherMap API client not initialized - skipping weather data processing")
        
        # Process Billboard chart data if available
        if billboard:
            print("\nProcessing Billboard chart data...")
            try:
                # Fetch Hot 100 chart
                print("Checking for Billboard Hot 100 chart data...")
                
                # Check if we already have weather, netflix, bee, or lifelog data for recent days
                has_existing_data = False
                has_weather_data = False
                
                # If we have weather data for these locations, we don't need to fetch new billboard data
                db_weather_data = db.get_weather_data_from_db()
                if db_weather_data and len(db_weather_data) > 0:
                    print(f"Found {len(db_weather_data)} weather data records, using existing billboard data if available")
                    has_existing_data = True
                    has_weather_data = True
                
                # Check for conversations
                db_conversations = db.get_conversations_from_db()
                if db_conversations and len(db_conversations) > 0:
                    print(f"Found {len(db_conversations)} conversation records, using existing billboard data if available")
                    has_existing_data = True
                
                # Check for lifelogs
                db_lifelogs = db.get_lifelogs_from_db()
                if db_lifelogs and len(db_lifelogs) > 0:
                    print(f"Found {len(db_lifelogs)} lifelog records, using existing billboard data if available")
                    has_existing_data = True
                
                # Check for Netflix history
                db_netflix = db.get_netflix_history_from_db()
                if db_netflix and len(db_netflix) > 0:
                    print(f"Found {len(db_netflix)} Netflix history records, using existing billboard data if available")
                    has_existing_data = True
                
                # Use force_update=False to prefer existing data if we have other data types
                if has_existing_data:
                    if has_weather_data:
                        print("Weather data exists, skipping Billboard API call if data exists")
                        hot100_chart = await fetch_billboard_chart("hot-100", force_update=False)
                    else:
                        print("Other data types exist, using existing Billboard data if available")
                        hot100_chart = await fetch_billboard_chart("hot-100", force_update=False)
                else:
                    # No data exists, use normal mode which will check based on date
                    print("No existing data found, checking if Billboard data needs updating")
                    hot100_chart = await fetch_billboard_chart("hot-100")
                
                if hot100_chart and hot100_chart.get("chart"):
                    chart_date = hot100_chart.get("chart", {}).get("date", "Unknown")
                    entries_count = len(hot100_chart.get("chart", {}).get("entries", []))
                    print(f"Retrieved Hot 100 chart for {chart_date} with {entries_count} entries")
                    
                    # Create directory if needed and debug mode is enabled
                    if app_debug_mode and not os.path.exists(os.path.join("data", "billboard")):
                        os.makedirs(os.path.join("data", "billboard"), exist_ok=True)
                    
                    # Save chart data to file if debug mode is enabled
                    saved_hot100 = save_to_file(
                        None, 
                        'billboard_hot100', 
                        hot100_chart,
                        app_debug_mode
                    )
                    if saved_hot100 and app_debug_mode:
                        print("Successfully processed Hot 100 chart data to JSON")
                    elif saved_hot100:
                        print("Hot 100 chart data processed (not saved to JSON due to debug mode disabled)")
                else:
                    print("No Hot 100 chart data available")
                    
                # Note: Billboard 200 chart endpoint is not available from this API provider
                    
            except Exception as e:
                print(f"Error processing Billboard chart data: {str(e)}")
                print(traceback.format_exc())
        else:
            print("\nBillboard API client not initialized - skipping chart data")
        
        print("\nData collection complete!")
        
    except Exception as e:
        print(f"Error in CLI data collection: {str(e)}")
        print(traceback.format_exc())

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Multi-API Data Collection CLI")
    parser.add_argument("--debug", 
                      action="store_true", 
                      default=False,
                      help="Enable debug mode: save data to JSON files in /data directory")
    
    # Netflix-related options
    netflix_group = parser.add_argument_group('Netflix operations')
    netflix_group.add_argument("--netflix-csv",
                      type=str,
                      help="Path to Netflix viewing history CSV file to import")
    netflix_group.add_argument("--enrich-netflix",
                      action="store_true",
                      default=False,
                      help="Enrich Netflix data with IMDB information (limit 50 titles)")
    netflix_group.add_argument("--enrich-limit",
                      type=int,
                      default=50,
                      help="Limit number of titles to enrich (default: 50)")
    netflix_group.add_argument("--deduplicate-netflix",
                      action="store_true",
                      default=False,
                      help="Remove duplicate Netflix series entries from the database")
    
    return parser.parse_args()

def run_cli(debug_mode=False):
    """
    CLI entry point for the application. Fetches data from API, stores in database,
    and then saves database content to JSON files if debug mode is enabled.
    
    Args:
        debug_mode: If True, save data to JSON files; if False, skip file creation
    """
    print("Starting Multi-API Data Collector CLI")
    
    # Only delete data directory if debug mode is enabled
    if debug_mode:
        # Delete the data directory if it exists
        data_dir = os.path.join("data")
        if os.path.exists(data_dir):
            print(f"Removing old data directory: {os.path.abspath(data_dir)}")
            import shutil
            try:
                shutil.rmtree(data_dir)
                print("Old data directory removed successfully")
            except Exception as e:
                print(f"Error removing data directory: {str(e)}")
    else:
        print("Debug mode disabled - skipping data directory operations")
    
    # Store debug_mode in a global variable
    global app_debug_mode
    app_debug_mode = debug_mode
    
    initialize_apis()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cli_async())

async def process_netflix_operations(netflix_csv=None, enrich_netflix=False, enrich_limit=50, debug_mode=False):
    """
    Process Netflix-related operations: import CSV and/or enrich with IMDB data
    
    Args:
        netflix_csv: Path to Netflix viewing history CSV file
        enrich_netflix: Whether to enrich Netflix data with IMDB information
        enrich_limit: Maximum number of titles to enrich
        debug_mode: Whether debug mode is enabled
    """
    global app_debug_mode
    app_debug_mode = debug_mode
    # Import Netflix viewing history if CSV file is provided
    if netflix_csv and os.path.exists(netflix_csv):
        print(f"\nImporting Netflix viewing history from {netflix_csv}...")
        import_result = netflix_importer.import_netflix_history(netflix_csv)
        print(f"Import result: {import_result['processed']} processed, "
              f"{import_result['added']} added, "
              f"{import_result['skipped']} skipped, "
              f"{import_result['deduplicated']} deduplicated within import, "
              f"{import_result.get('cross_deduplicated', 0)} deduplicated across imports")
        
        # Save to JSON if debug mode is enabled
        if debug_mode:
            print("Saving imported Netflix history to JSON...")
            json_path = netflix_importer.save_netflix_history_to_json(debug_mode=debug_mode)
            if json_path:
                print(f"Saved Netflix history to {json_path}")
        else:
            print("Debug mode disabled - skipping JSON file creation for Netflix history")
    
    # Enrich Netflix data with IMDB information if requested
    if enrich_netflix:
        print(f"\nEnriching Netflix data with IMDB information (limit: {enrich_limit} titles)...")
        try:
            from imdb_api import IMDBAPI
            
            # Verify IMDB API is configured
            imdb_api = IMDBAPI()
            if not imdb_api.api_key:
                print("ERROR: IMDB API key not found. Skipping Netflix enrichment.")
                print("Set the IMDB_API_KEY environment variable and try again.")
                return
            
            enrich_result = await netflix_importer.enrich_netflix_title_data(limit=enrich_limit)
            print(f"Enrichment result: {enrich_result['processed']} processed, "
                  f"{enrich_result['enriched']} enriched, "
                  f"{enrich_result['skipped']} skipped")
            
            # Save to JSON if debug mode is enabled
            if debug_mode:
                print("Saving enriched Netflix history to JSON...")
                json_path = netflix_importer.save_netflix_history_to_json(debug_mode=debug_mode)
                if json_path:
                    print(f"Saved enriched Netflix history to {json_path}")
            else:
                print("Debug mode disabled - skipping JSON file creation for enriched Netflix history")
            
            # Show sample of enriched titles
            import database_handler as db
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker, scoped_session
            from models import Netflix_History_Item, Netflix_Title_Info
            
            # Create session for querying title info
            DATABASE_URL = os.environ.get('DATABASE_URL')
            engine = create_engine(DATABASE_URL)
            Session = scoped_session(sessionmaker(bind=engine))
            session = Session()
            
            try:
                # Get history items
                enriched_items = db.get_netflix_history_from_db(limit=10)
                if enriched_items:
                    print("\nSample of Netflix titles:")
                    for i, item in enumerate(enriched_items, 1):
                        print(f"{i}. {item.title}")
                        if item.content_type:
                            print(f"   Type: {item.content_type}, Year: {item.release_year or 'Unknown'}")
                        if item.show_name:
                            print(f"   Show: {item.show_name}")
                        
                        # Look up title info for IMDB ID
                        title_info = session.query(Netflix_Title_Info).filter_by(title=item.title).first()
                        if title_info and title_info.imdb_id:
                            print(f"   IMDB ID: {title_info.imdb_id}")
                        
                        print()
            finally:
                session.close()
        
        except Exception as e:
            print(f"Error enriching Netflix data: {str(e)}")
            print(traceback.format_exc())

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Show debug mode status
    debug_mode = args.debug
    if debug_mode:
        print("Debug mode ENABLED: Will save data to JSON files in /data directory")
    else:
        print("Debug mode DISABLED: Will not save data to JSON files")
    
    # Global app_debug_mode is set in run_cli function
    
    # Process Netflix operations if requested
    if args.netflix_csv or args.enrich_netflix or args.deduplicate_netflix:
        print("Netflix operations requested - skipping regular data collection")
        
        # Initialize APIs just in case we need them
        initialize_apis()
        
        # Handle Netflix deduplication separately
        if args.deduplicate_netflix:
            print("\nRemoving duplicate Netflix series entries from the database...")
            try:
                from remove_duplicate_netflix_series import remove_duplicate_netflix_series
                result = remove_duplicate_netflix_series()
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"\nResults:")
                    print(f"- Found {result['total_series']} unique series with {result['total_entries']} total entries")
                    print(f"- Kept {result['entries_kept']} entries (one per series)")
                    print(f"- Removed {result['entries_removed']} duplicate entries")
            except Exception as e:
                print(f"Error deduplicating Netflix series: {str(e)}")
                print(traceback.format_exc())
        
        # Run other Netflix operations
        if args.netflix_csv or args.enrich_netflix:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(process_netflix_operations(
                netflix_csv=args.netflix_csv,
                enrich_netflix=args.enrich_netflix,
                enrich_limit=args.enrich_limit,
                debug_mode=debug_mode
            ))
    else:
        # Run the regular data collection CLI
        run_cli(debug_mode)