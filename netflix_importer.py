"""
Netflix Viewing History Importer

This module handles importing Netflix viewing history data from a CSV file 
and parsing it into the database.
"""

import os
import csv
import json
import re
from datetime import datetime
import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Netflix_History_Item, Netflix_Title_Info, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
Session = scoped_session(sessionmaker(bind=engine))

def clean_special_characters(title):
    """
    Remove special characters from a title.
    
    Args:
        title: Original title string
        
    Returns:
        Cleaned title string
    """
    if not title:
        return title
        
    # Remove quotes if they exist
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
        
    # Replace colons and other special characters with spaces
    cleaned = re.sub(r'[:\-_]', ' ', title)
    
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Trim leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def parse_date(date_str):
    """Parse date string from Netflix CSV to datetime object."""
    try:
        return datetime.strptime(date_str, '%m/%d/%y')
    except ValueError:
        # Try alternative formats
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}, using today's date")
            return datetime.now()

def parse_title(title):
    """
    Parse Netflix title to extract show name, season, and episode information.
    
    Returns a dictionary with keys:
        - show_name: The name of the show (if applicable)
        - season: Season information (if applicable)
        - episode_name: Episode name (if applicable)
        - episode_number: Episode number (if applicable)
    """
    # Initialize result with empty values
    result = {
        'show_name': None,
        'season': None,
        'episode_name': None,
        'episode_number': None
    }
    
    # Check if title has quotes - usually indicates a movie
    if title.startswith('"') and title.endswith('"'):
        # Remove quotes from title
        clean_title = title[1:-1]
        
        # Common patterns for TV shows
        # Pattern: "Show Name: Season X: Episode Name"
        season_episode_pattern = r'^(.*?):\s*(Season\s*\d+):\s*(.*)$'
        # Pattern: "Show Name: Limited Series: Episode Name"
        limited_series_pattern = r'^(.*?):\s*(Limited Series):\s*(.*)$'
        # Pattern: "Show Name: Episode X"
        episode_pattern = r'^(.*?):\s*(Episode\s*\d+)$'
        
        # Try to match season and episode pattern
        match = re.match(season_episode_pattern, clean_title)
        if match:
            result['show_name'] = match.group(1).strip()
            result['season'] = match.group(2).strip()
            result['episode_name'] = match.group(3).strip()
            
            # Try to extract episode number if it exists in the episode name
            ep_num_match = re.search(r'Episode\s*(\d+)', result['episode_name'])
            if ep_num_match:
                result['episode_number'] = ep_num_match.group(1)
            return result
        
        # Try to match limited series pattern
        match = re.match(limited_series_pattern, clean_title)
        if match:
            result['show_name'] = match.group(1).strip()
            result['season'] = match.group(2).strip()  # "Limited Series"
            result['episode_name'] = match.group(3).strip()
            return result
        
        # Try to match simple episode pattern
        match = re.match(episode_pattern, clean_title)
        if match:
            result['show_name'] = match.group(1).strip()
            result['episode_number'] = re.search(r'\d+', match.group(2)).group(0)
            return result
        
        # If no patterns match, just use the entire title
        return result
    
    # Not in quotes - might be a movie or simple format
    return result

def extract_series_name(title):
    """
    Extract the base series name from a title with episode information.
    
    Args:
        title: Original Netflix title with episode information
        
    Returns:
        Base series name without episode/season information
    """
    # Remove episode indicators
    base_title = title
    
    # Try to extract series name before episode indicators
    episode_keywords = [" Episode ", " Season ", " Chapter ", " Part "]
    for keyword in episode_keywords:
        if keyword.lower() in base_title.lower():
            base_title = base_title.split(keyword, 1)[0]
            break
    
    # Also handle format like "Series_Name: Season X: Episode Y"
    if ":" in base_title:
        base_title = base_title.split(":", 1)[0]
    
    # Handle "Limited Series" indicator
    if "Limited Series" in base_title:
        base_title = base_title.replace("Limited Series", "").strip()
    
    return base_title.strip()

def is_series_episode(title):
    """
    Check if a title appears to be an episode of a TV series.
    
    Args:
        title: The title to check
        
    Returns:
        True if it appears to be a series episode, False otherwise
    """
    episode_indicators = ["Episode ", "Season ", "Chapter ", " Part ", "Limited Series"]
    return any(indicator in title for indicator in episode_indicators)

def import_netflix_history(csv_file_path, deduplicate_series=True):
    """
    Import Netflix viewing history from a CSV file into the database.
    
    Args:
        csv_file_path: Path to the Netflix viewing history CSV file
        deduplicate_series: If True, only keep one episode per series
        
    Returns:
        Dictionary with counts of processed, added, and skipped items
    """
    session = Session()
    result = {"processed": 0, "added": 0, "skipped": 0, "deduplicated": 0, "cross_deduplicated": 0}
    
    try:
        # Check if file exists
        if not os.path.exists(csv_file_path):
            logger.error(f"File not found: {csv_file_path}")
            return result
        
        # Dictionary to track series episodes for deduplication
        # Key: series_name, Value: list of (title, watch_date) tuples
        series_episodes = {}
        
        # Track series that are already in the database
        existing_series = set()
        if deduplicate_series:
            # Query the database for all existing series
            all_history = session.query(Netflix_History_Item).all()
            for item in all_history:
                if item.show_name and is_series_episode(item.title):
                    existing_series.add(item.show_name)
            logger.info(f"Found {len(existing_series)} existing series in the database")
            
        # Read CSV file and gather data
        all_entries = []
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                result["processed"] += 1
                
                # Parse date and title
                try:
                    title = row.get('Title', '')
                    date_str = row.get('Date', '')
                    
                    if not title or not date_str:
                        logger.warning(f"Missing title or date in row: {row}")
                        result["skipped"] += 1
                        continue
                    
                    watch_date = parse_date(date_str)
                    parsed_title = parse_title(title)
                    
                    # Clean title by removing special characters
                    cleaned_title = clean_special_characters(title)
                    
                    # Check if this entry already exists in the database
                    existing = session.query(Netflix_History_Item).filter(
                        Netflix_History_Item.title == cleaned_title,
                        Netflix_History_Item.watch_date == watch_date
                    ).first()
                    
                    if existing:
                        logger.debug(f"Skipping duplicate entry: {cleaned_title} on {date_str}")
                        result["skipped"] += 1
                        continue
                    
                    # Check for cross-import deduplication:
                    # If this is a series episode, and we already have an episode from this series
                    # in the database, skip it
                    if deduplicate_series and is_series_episode(cleaned_title):
                        series_name = extract_series_name(cleaned_title)
                        if series_name in existing_series:
                            logger.info(f"Skipping {cleaned_title} - Series '{series_name}' already in database")
                            result["cross_deduplicated"] += 1
                            continue
                    
                    # Store entry for processing
                    all_entries.append({
                        'original_title': title,
                        'cleaned_title': cleaned_title,
                        'watch_date': watch_date,
                        'parsed_title': parsed_title
                    })
                    
                    # If this is a series episode and deduplication is enabled, group by series name
                    if deduplicate_series and is_series_episode(cleaned_title):
                        series_name = extract_series_name(cleaned_title)
                        if series_name not in series_episodes:
                            series_episodes[series_name] = []
                        
                        series_episodes[series_name].append({
                            'original_title': title,
                            'cleaned_title': cleaned_title,
                            'watch_date': watch_date,
                            'parsed_title': parsed_title
                        })
                    
                except Exception as e:
                    logger.error(f"Error processing row: {row} - Error: {str(e)}")
                    result["skipped"] += 1
        
        # Process entries with deduplication
        entries_to_add = []
        if deduplicate_series:
            # Process non-series entries first
            for entry in all_entries:
                if not is_series_episode(entry['cleaned_title']):
                    entries_to_add.append(entry)
            
            # For each series, only keep the first episode (by watch date)
            for series_name, episodes in series_episodes.items():
                if episodes:
                    # Sort by watch date (oldest first)
                    episodes.sort(key=lambda x: x['watch_date'])
                    # Keep only the first episode of each series
                    entries_to_add.append(episodes[0])
                    # Count skipped episodes
                    result["deduplicated"] += len(episodes) - 1
                    logger.info(f"Keeping 1 episode out of {len(episodes)} for series '{series_name}'")
        else:
            # No deduplication, add all entries
            entries_to_add = all_entries
        
        # Add the final entries to the database
        for entry in entries_to_add:
            # Create new history item
            history_item = Netflix_History_Item(
                title=entry['cleaned_title'],
                watch_date=entry['watch_date'],
                show_name=entry['parsed_title']['show_name'],
                season=entry['parsed_title']['season'],
                episode_name=entry['parsed_title']['episode_name'],
                episode_number=entry['parsed_title']['episode_number']
            )
            
            session.add(history_item)
            result["added"] += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Import completed: {result['processed']} processed, {result['added']} added, " +
                   f"{result['skipped']} skipped, {result['deduplicated']} deduplicated")
            
    except Exception as e:
        logger.error(f"Error importing Netflix history: {str(e)}")
        session.rollback()
    finally:
        session.close()
    
    return result

def save_netflix_history_to_json(output_dir='data/netflix'):
    """
    Retrieve Netflix viewing history from the database and save to JSON file.
    
    Args:
        output_dir: Directory to save JSON file
        
    Returns:
        Path to JSON file if successful, None otherwise
    """
    session = Session()
    try:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Query all history items
        history_items = session.query(Netflix_History_Item).order_by(
            Netflix_History_Item.watch_date.desc()
        ).all()
        
        if not history_items:
            logger.warning("No Netflix history items found in database")
            return None
        
        # Format data for JSON
        formatted_items = []
        for item in history_items:
            formatted_item = {
                'title': item.title,
                'watch_date': item.watch_date.strftime('%Y-%m-%d') if item.watch_date else None,
                'show_name': item.show_name,
                'season': item.season,
                'episode': item.episode_name,
                'episode_number': item.episode_number
            }
            
            # Add additional info if available
            if item.content_type:
                formatted_item['content_type'] = item.content_type
            if item.genres:
                try:
                    formatted_item['genres'] = json.loads(item.genres)
                except:
                    pass
            if item.release_year:
                formatted_item['release_year'] = item.release_year
            
            formatted_items.append(formatted_item)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"netflix_history_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'netflix_history': formatted_items,
                'count': len(formatted_items),
                'exported_at': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"Saved {len(formatted_items)} Netflix history items to {filepath}")
        return filepath
    
    except Exception as e:
        logger.error(f"Error saving Netflix history to JSON: {str(e)}")
        return None
    finally:
        session.close()

def clean_title_for_search(title):
    """
    Clean and normalize a Netflix title for better IMDB search results.
    Removes episode indicators, special characters, and handles possessive forms.
    Special handling for popular TV series to improve match rate.
    
    Args:
        title: Original Netflix title
    
    Returns:
        Cleaned title string optimized for IMDB search
    """
    # First, remove quotes if they exist
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
    
    # Check for popular TV series with exact matching
    popular_shows = {
        "Game of Thrones": ["Game of Thrones", "GoT"],
        "Stranger Things": ["Stranger Things"],
        "The Crown": ["The Crown"],
        "Breaking Bad": ["Breaking Bad"],
        "The Witcher": ["The Witcher"],
        "Money Heist": ["Money Heist", "La Casa de Papel"],
        "Bridgerton": ["Bridgerton"],
        "The Queen's Gambit": ["The Queens Gambit", "Queens Gambit"]
    }
    
    # Check if the title starts with any of the popular show names
    for show_name, search_terms in popular_shows.items():
        for term in search_terms:
            if title.startswith(term):
                return show_name
    
    # Standard cleaning for other titles
    # Extract show name without episode info (split by colon)
    base_title = title.split(':')[0] if ':' in title else title
    
    # Remove anything after "Episode" or "Season" keywords
    episode_keywords = [" Episode ", " Season ", " Chapter ", " Part "]
    for keyword in episode_keywords:
        if keyword.lower() in base_title.lower():
            base_title = base_title.split(keyword, 1)[0]
    
    # Also handle episode indicators with numbers like "- E01" or "S01E01"
    base_title = re.sub(r'\s+-\s+[Ee]\d+.*$', '', base_title)  # Remove "- E01" pattern
    base_title = re.sub(r'\s+[Ss]\d+[Ee]\d+.*$', '', base_title)  # Remove "S01E01" pattern
    
    # Handle special cases before removing all special characters
    # Convert possessive form to regular form (Queen's → Queens)
    base_title = base_title.replace("'s", "s")
    
    # Remove special characters, keeping only alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s]', '', base_title)
    
    # Remove extra spaces and trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Remove "Limited Series" and similar suffixes
    suffixes_to_remove = ["Limited Series", "The Complete Series", "The Series"]
    for suffix in suffixes_to_remove:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-(len(suffix))].strip()
    
    return cleaned

async def enrich_netflix_title_data(limit=None):
    """
    Enrich Netflix title data using the IMDB API.
    
    Looks up each Netflix title in the IMDB database using the autocomplete search
    and updates the Netflix_Title_Info table with IMDB data.
    
    Args:
        limit: Optional maximum number of titles to process (default: None, process all)
    
    Returns:
        Dictionary with counts of processed, enriched, and skipped items
    """
    from imdb_api import IMDBAPI
    import asyncio
    
    # Initialize API client
    api = IMDBAPI()
    session = Session()
    result = {"processed": 0, "enriched": 0, "skipped": 0}
    
    try:
        # Query Netflix history items without enriched data
        query = session.query(Netflix_History_Item.title).distinct()
        
        # Check which titles already have info
        existing_info = session.query(Netflix_Title_Info.title).all()
        existing_titles = [info[0] for info in existing_info]
        
        # Filter out titles that already have info
        all_titles = [item[0] for item in query.all()]
        titles_to_process = [title for title in all_titles if title not in existing_titles]
        
        # Apply limit if specified
        if limit and limit > 0:
            titles_to_process = titles_to_process[:limit]
        
        logger.info(f"Found {len(titles_to_process)} Netflix titles to enrich")
        
        # Process each title
        for title in titles_to_process:
            result["processed"] += 1
            
            try:
                # Clean the title for better search results
                search_term = clean_title_for_search(title)
                logger.info(f"Searching IMDB for: {search_term} (from {title})")
                
                # Try autocomplete search first
                search_success = False
                search_result = None
                
                # Initial search with cleaned term
                autocomplete_result = await api.autocomplete_search(search_term, max_results=5)
                
                if "results" in autocomplete_result and autocomplete_result["results"]:
                    search_result = autocomplete_result["results"][0]  # Take the first/best match
                    search_success = True
                else:
                    # Try variations if original search failed
                    variations = []
                    
                    # Try without "The" prefix if it exists
                    if search_term.startswith("The "):
                        variations.append(search_term[4:])
                    
                    # Try with "The" prefix if it doesn't exist and isn't too long
                    if not search_term.startswith("The ") and len(search_term.split()) <= 3:
                        variations.append("The " + search_term)
                        
                    # Try with apostrophe for possessive nouns (Queens → Queen's)
                    if "s " in search_term:
                        variation = search_term.replace("s ", "'s ")
                        variations.append(variation)
                        
                    # Try each variation
                    for variation in variations:
                        logger.info(f"Trying variation: {variation}")
                        var_result = await api.autocomplete_search(variation, max_results=5)
                        
                        if "results" in var_result and var_result["results"]:
                            search_result = var_result["results"][0]  # Take the first/best match
                            search_success = True
                            break
                
                if search_success and search_result:
                    # Create new title info record
                    imdb_id = search_result.get("id")
                    primary_title = search_result.get("primaryTitle", "")
                    content_type = "SERIES" if search_result.get("type") in ["tvSeries", "tvMiniSeries"] else "MOVIE"
                    
                    title_info = Netflix_Title_Info(
                        title=title,
                        content_type=content_type,
                        imdb_id=imdb_id,
                        raw_data=json.dumps(search_result)
                    )
                    
                    # Add release year if available
                    if "startYear" in search_result:
                        try:
                            title_info.release_year = int(search_result.get("startYear", 0))
                        except (ValueError, TypeError):
                            pass
                    
                    session.add(title_info)
                    result["enriched"] += 1
                    
                    # Update all Netflix history items with this title
                    history_items = session.query(Netflix_History_Item).filter(
                        Netflix_History_Item.title == title
                    ).all()
                    
                    for item in history_items:
                        item.content_type = content_type
                        if title_info.release_year:
                            item.release_year = title_info.release_year
                    
                    # Commit after each successful enrichment to avoid losing progress
                    session.commit()
                    logger.info(f"Enriched: {title} → {primary_title} ({imdb_id})")
                
                else:
                    logger.warning(f"No IMDB match found for: {title}")
                    result["skipped"] += 1
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error enriching title {title}: {str(e)}")
                result["skipped"] += 1
                session.rollback()
        
        logger.info(f"Title enrichment completed: {result['processed']} processed, "
                  f"{result['enriched']} enriched, {result['skipped']} skipped")
        
    except Exception as e:
        logger.error(f"Error during title enrichment process: {str(e)}")
        session.rollback()
    finally:
        session.close()
    
    return result

def main(csv_file_path):
    """Import Netflix viewing history from CSV and save to JSON."""
    # Import data from CSV
    import_result = import_netflix_history(csv_file_path)
    print(f"Import result: {import_result['processed']} processed, {import_result['added']} added, {import_result['skipped']} skipped")
    
    # Save to JSON
    json_path = save_netflix_history_to_json()
    if json_path:
        print(f"Netflix history saved to {json_path}")
    else:
        print("Failed to save Netflix history to JSON")
    
    return import_result

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python netflix_importer.py <netflix_csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    main(csv_file)