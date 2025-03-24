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

def import_netflix_history(csv_file_path):
    """
    Import Netflix viewing history from a CSV file into the database.
    
    Args:
        csv_file_path: Path to the Netflix viewing history CSV file
        
    Returns:
        Dictionary with counts of processed, added, and skipped items
    """
    session = Session()
    result = {"processed": 0, "added": 0, "skipped": 0}
    
    try:
        # Check if file exists
        if not os.path.exists(csv_file_path):
            logger.error(f"File not found: {csv_file_path}")
            return result
        
        # Read CSV file
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
                    
                    # Check if this entry already exists
                    existing = session.query(Netflix_History_Item).filter(
                        Netflix_History_Item.title == title,
                        Netflix_History_Item.watch_date == watch_date
                    ).first()
                    
                    if existing:
                        logger.debug(f"Skipping duplicate entry: {title} on {date_str}")
                        result["skipped"] += 1
                        continue
                    
                    # Create new history item
                    history_item = Netflix_History_Item(
                        title=title,
                        watch_date=watch_date,
                        show_name=parsed_title['show_name'],
                        season=parsed_title['season'],
                        episode_name=parsed_title['episode_name'],
                        episode_number=parsed_title['episode_number']
                    )
                    
                    session.add(history_item)
                    result["added"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row: {row} - Error: {str(e)}")
                    result["skipped"] += 1
            
            # Commit changes
            session.commit()
            logger.info(f"Import completed: {result['processed']} processed, {result['added']} added, {result['skipped']} skipped")
            
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

def enrich_netflix_title_data():
    """
    Attempt to enrich Netflix title data using the Netflix API or other sources.
    This is a placeholder function and would need to be implemented with actual API access.
    """
    # This would be implemented when we have access to Netflix API or other data sources
    # For now, just log a message
    logger.info("Netflix title enrichment is not currently implemented")
    return False

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