from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation, Bee_Fact, Bee_Todo, Limitless_Lifelog, Weather_Data, Billboard_Chart_Item, Netflix_History_Item, Netflix_Title_Info
import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a sessionmaker
Session = sessionmaker(bind=engine)

def parse_date(date_str):
    """Parse date string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None

def store_conversations(conversations):
    """
    Store conversations in the database with deduplication.
    
    Args:
        conversations: List of conversation dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(conversations),
            "added": 0,
            "skipped": 0
        }
        
        for conv in conversations:
            # Check if this conversation already exists in the database
            conv_id = str(conv.get('id', ''))
            existing = session.query(Bee_Conversation).filter_by(conversation_id=conv_id).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Get location data if it exists
            location = conv.get('primary_location', {})
            address = location.get('address') if location else None
            latitude = location.get('latitude') if location else None
            longitude = location.get('longitude') if location else None
            
            # Create new conversation record
            new_conv = Bee_Conversation(
                conversation_id=conv_id,
                summary=conv.get('Summary'),  # Use the extracted summary without heading
                atmosphere=conv.get('Atmosphere'),  # Store the atmosphere content separately
                key_takeaways=conv.get('Key Takeaways'),  # Store key takeaways if they exist
                created_at=parse_date(conv.get('Created At')),
                address=address,
                latitude=latitude,
                longitude=longitude,
                raw_data=json.dumps(conv)
            )
            
            session.add(new_conv)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def store_facts(facts):
    """
    Store facts in the database with deduplication.
    
    Args:
        facts: List of fact dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(facts),
            "added": 0,
            "skipped": 0
        }
        
        for fact in facts:
            fact_text = fact.get('text')
            if not fact_text:
                result["skipped"] += 1
                continue
                
            # Check if this fact already exists in the database
            existing = session.query(Bee_Fact).filter_by(text=fact_text).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Create new fact record
            new_fact = Bee_Fact(
                fact_id=str(fact.get('id', '')),
                text=fact_text,
                created_at=parse_date(fact.get('created_at')),
                raw_data=json.dumps(fact)
            )
            
            session.add(new_fact)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def store_todos(todos):
    """
    Store todos in the database with deduplication.
    
    Args:
        todos: List of todo dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(todos),
            "added": 0,
            "skipped": 0
        }
        
        for todo in todos:
            # Check if this todo already exists in the database
            todo_id = str(todo.get('id', ''))
            existing = session.query(Bee_Todo).filter_by(todo_id=todo_id).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Create new todo record
            new_todo = Bee_Todo(
                todo_id=todo_id,
                task=todo.get('text', 'No task description'),
                completed=todo.get('completed', False),
                created_at=parse_date(todo.get('created_at')),
                raw_data=json.dumps(todo)
            )
            
            session.add(new_todo)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_conversations_from_db():
    """Retrieve all conversations from the database."""
    session = Session()
    try:
        return session.query(Bee_Conversation).order_by(Bee_Conversation.created_at.desc()).all()
    finally:
        session.close()

def get_facts_from_db():
    """Retrieve all facts from the database."""
    session = Session()
    try:
        return session.query(Bee_Fact).order_by(Bee_Fact.created_at.desc()).all()
    finally:
        session.close()

def get_todos_from_db():
    """Retrieve all todos from the database."""
    session = Session()
    try:
        return session.query(Bee_Todo).order_by(Bee_Todo.created_at.desc()).all()
    finally:
        session.close()

def store_lifelogs(lifelogs):
    """
    Store lifelogs in the database with deduplication.
    
    Args:
        lifelogs: List of lifelog dictionaries from Limitless API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        # Initialize result with 0 processed in case we have an empty list or error
        result = {
            "processed": 0,
            "added": 0,
            "skipped": 0
        }
        
        # Skip processing if we get an empty list or a list with a single string 'lifelogs'
        if not lifelogs or (isinstance(lifelogs, list) and len(lifelogs) == 1 and isinstance(lifelogs[0], str) and lifelogs[0] == 'lifelogs'):
            logger.warning("Received empty or invalid lifelogs list, skipping")
            return result
            
        # Update processed count for valid list
        result["processed"] = len(lifelogs)
        
        for log in lifelogs:
            # Skip if it's a string that's just "lifelogs"
            if isinstance(log, str) and log == "lifelogs":
                logger.warning("Skipping string entry 'lifelogs'")
                result["skipped"] += 1
                continue
                
            # Handle both string and dictionary format for actual lifelog data
            if isinstance(log, str) and log != "lifelogs":
                # Try to parse the string as JSON
                try:
                    log_data = json.loads(log)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse lifelog string as JSON: {log[:30]}...")
                    result["skipped"] += 1
                    continue
            else:
                log_data = log
                
            # Skip if log_data is not a dictionary (e.g., it might be None or another type)
            if not isinstance(log_data, dict):
                logger.warning(f"Skipping non-dictionary lifelog data: {type(log_data)}")
                result["skipped"] += 1
                continue
                
            # Check if this lifelog already exists in the database
            log_id = str(log_data.get('id', ''))
            if not log_id:
                logger.warning("Skipping lifelog with no ID")
                result["skipped"] += 1
                continue
                
            existing = session.query(Limitless_Lifelog).filter_by(log_id=log_id).first()
            
            if existing:
                logger.info(f"Lifelog ID {log_id} already exists, skipping")
                result["skipped"] += 1
                continue
            
            try:
                # Extract tags if they exist
                tags = log_data.get('tags')
                if tags and isinstance(tags, list):
                    tags_json = json.dumps(tags)
                else:
                    tags_json = None
                
                # Extract timestamps from contents
                created_at = None
                updated_at = None
                
                # Look for startTime and endTime in contents
                if 'contents' in log_data and isinstance(log_data['contents'], list):
                    # Find the earliest startTime and latest endTime
                    for item in log_data['contents']:
                        start_time = item.get('startTime')
                        parsed_start = parse_date(start_time) if start_time else None
                        
                        if parsed_start:
                            if created_at is None:
                                created_at = parsed_start
                            elif parsed_start < created_at:
                                created_at = parsed_start
                            
                        end_time = item.get('endTime')
                        parsed_end = parse_date(end_time) if end_time else None
                        
                        if parsed_end:
                            if updated_at is None:
                                updated_at = parsed_end
                            elif parsed_end > updated_at:
                                updated_at = parsed_end
                
                # Fallback to created_at/updated_at if they exist at top level
                if created_at is None:
                    created_at = parse_date(log_data.get('created_at'))
                
                if updated_at is None:
                    updated_at = parse_date(log_data.get('updated_at'))
                
                # If we still don't have timestamps, log a warning
                if created_at is None:
                    logger.warning(f"No valid startTime or created_at found for lifelog {log_id}")
                
                # Create new lifelog record
                new_log = Limitless_Lifelog(
                    log_id=log_id,
                    title=log_data.get('title'),
                    description=log_data.get('description'),
                    created_at=created_at,
                    updated_at=updated_at,
                    log_type=log_data.get('type'),
                    tags=tags_json,
                    raw_data=json.dumps(log_data)
                )
                
                session.add(new_log)
                result["added"] += 1
                logger.info(f"Added lifelog with ID {log_id}")
            except Exception as e:
                logger.error(f"Error adding lifelog {log_id}: {str(e)}")
                result["skipped"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in store_lifelogs: {str(e)}")
        # Return empty result if exception happens before result is initialized
        return {
            "processed": 0,
            "added": 0,
            "skipped": 0
        }
    finally:
        session.close()

def get_lifelogs_from_db():
    """Retrieve all lifelogs from the database."""
    session = Session()
    try:
        return session.query(Limitless_Lifelog).order_by(Limitless_Lifelog.created_at.desc()).all()
    finally:
        session.close()

def get_latest_lifelog_date():
    """
    Retrieve the most recent lifelog date from the database.
    Returns a string in format YYYY-MM-DD or None if no lifelogs exist.
    """
    session = Session()
    try:
        # Get the lifelog with the most recent created_at timestamp
        latest_lifelog = session.query(Limitless_Lifelog).order_by(Limitless_Lifelog.created_at.desc()).first()
        
        if latest_lifelog and latest_lifelog.created_at:
            # Format as YYYY-MM-DD
            return latest_lifelog.created_at.strftime('%Y-%m-%d')
        return None
    except Exception as e:
        logger.error(f"Error getting latest lifelog date: {str(e)}")
        return None
    finally:
        session.close()

def store_weather_data(weather_data):
    """
    Store weather data in the database with deduplication.
    
    Args:
        weather_data: Dictionary containing weather data from OpenWeatherMap API
        
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        # Initialize result
        result = {
            "processed": 1,  # We always process 1 weather data point at a time
            "added": 0,
            "skipped": 0
        }
        
        # Skip if we received empty or None data
        if not weather_data or not isinstance(weather_data, dict):
            logger.warning(f"Invalid weather data type: {type(weather_data)}")
            result["skipped"] += 1
            return result
            
        # Get required fields
        try:
            # Extract main coordinates
            coord = weather_data.get('coord', {})
            latitude = coord.get('lat')
            longitude = coord.get('lon')
            
            # Skip if we don't have coordinates
            if latitude is None or longitude is None:
                logger.warning("Weather data missing coordinates, skipping")
                result["skipped"] += 1
                return result
                
            # Extract timestamp
            dt = weather_data.get('dt')  # Unix timestamp
            if dt:
                timestamp = datetime.fromtimestamp(dt)
            else:
                # Use current time if no timestamp provided
                timestamp = datetime.utcnow()
                
            # Check if weather data for this location and time already exists
            existing = session.query(Weather_Data).filter_by(
                latitude=latitude,
                longitude=longitude,
                timestamp=timestamp
            ).first()
            
            if existing:
                logger.info(f"Weather data for location ({latitude}, {longitude}) at {timestamp} already exists, skipping")
                result["skipped"] += 1
                return result
                
            # Extract weather data
            main_data = weather_data.get('main', {})
            wind_data = weather_data.get('wind', {})
            clouds_data = weather_data.get('clouds', {})
            weather_info = weather_data.get('weather', [{}])[0]  # First weather item
            
            # Create new weather data record
            new_weather = Weather_Data(
                weather_id=weather_info.get('id'),
                location_name=weather_data.get('name'),
                latitude=latitude,
                longitude=longitude,
                temperature=main_data.get('temp'),
                feels_like=main_data.get('feels_like'),
                humidity=main_data.get('humidity'),
                pressure=main_data.get('pressure'),
                wind_speed=wind_data.get('speed'),
                wind_direction=wind_data.get('deg'),
                clouds=clouds_data.get('all'),  # Cloudiness percentage
                weather_main=weather_info.get('main'),
                weather_description=weather_info.get('description'),
                visibility=weather_data.get('visibility'),
                timestamp=timestamp,
                raw_data=json.dumps(weather_data),
                units=weather_data.get('units', 'metric')  # Default to metric if not specified
            )
            
            session.add(new_weather)
            session.commit()
            result["added"] += 1
            logger.info(f"Added weather data for {new_weather.location_name} ({latitude}, {longitude}) at {timestamp}")
            return result
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing weather data: {str(e)}")
            result["skipped"] += 1
            return result
            
    except Exception as e:
        session.rollback()
        logger.error(f"Error in store_weather_data: {str(e)}")
        return {
            "processed": 1,
            "added": 0,
            "skipped": 1
        }
    finally:
        session.close()

def get_weather_data_from_db():
    """Retrieve all weather data from the database."""
    session = Session()
    try:
        return session.query(Weather_Data).order_by(Weather_Data.timestamp.desc()).all()
    finally:
        session.close()
        
def get_latest_weather_data_for_location(latitude, longitude, max_age_hours=24):
    """
    Retrieve the most recent weather data for a given location within max_age_hours.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        max_age_hours: Maximum age of weather data in hours
        
    Returns:
        Weather_Data object or None if no matching data exists
    """
    session = Session()
    try:
        # Calculate the maximum age timestamp
        from datetime import timedelta
        max_age = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find weather data within 0.01 degree of the given coordinates (approx 1km)
        # and not older than max_age_hours
        return session.query(Weather_Data)\
            .filter(Weather_Data.latitude.between(latitude - 0.01, latitude + 0.01))\
            .filter(Weather_Data.longitude.between(longitude - 0.01, longitude + 0.01))\
            .filter(Weather_Data.timestamp >= max_age)\
            .order_by(Weather_Data.timestamp.desc())\
            .first()
    except Exception as e:
        logger.error(f"Error getting latest weather data for location: {str(e)}")
        return None
    finally:
        session.close()
        
def get_conversations_with_coordinates():
    """
    Retrieve all conversations from the database that have valid coordinates.
    
    Returns:
        List of Bee_Conversation objects with latitude and longitude
    """
    session = Session()
    try:
        return session.query(Bee_Conversation)\
            .filter(Bee_Conversation.latitude.isnot(None))\
            .filter(Bee_Conversation.longitude.isnot(None))\
            .order_by(Bee_Conversation.created_at.desc())\
            .all()
    finally:
        session.close()
        
def check_weather_data_exists_for_date(date_str):
    """
    Check if weather data exists for a specific date.
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        
    Returns:
        True if weather data exists for this date, False otherwise
    """
    session = Session()
    try:
        # Parse the date string
        from datetime import datetime
        
        # Create datetime objects for the start and end of the day
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = datetime.strptime(date_str + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        
        # Check if any weather data exists within this date range
        count = session.query(Weather_Data)\
            .filter(Weather_Data.timestamp >= start_date)\
            .filter(Weather_Data.timestamp <= end_date)\
            .count()
        
        return count > 0
    except Exception as e:
        logger.error(f"Error checking weather data for date {date_str}: {str(e)}")
        return False
    finally:
        session.close()
        
def get_dates_with_data():
    """
    Get a list of unique dates that have Bee, Netflix, or Limitless data.
    
    Returns:
        A list of date strings in format YYYY-MM-DD
    """
    session = Session()
    try:
        unique_dates = set()
        
        # Get Bee conversation dates
        bee_dates = session.query(
            func.date_trunc('day', Bee_Conversation.created_at).label('date_day')
        ).distinct().all()
        
        for date_tuple in bee_dates:
            if date_tuple[0]:
                unique_dates.add(date_tuple[0].strftime('%Y-%m-%d'))
        
        # Get Netflix history dates
        netflix_dates = session.query(
            func.date_trunc('day', Netflix_History_Item.watch_date).label('date_day')
        ).distinct().all()
        
        for date_tuple in netflix_dates:
            if date_tuple[0]:
                unique_dates.add(date_tuple[0].strftime('%Y-%m-%d'))
        
        # Get Limitless lifelog dates
        lifelog_dates = session.query(
            func.date_trunc('day', Limitless_Lifelog.created_at).label('date_day')
        ).distinct().all()
        
        for date_tuple in lifelog_dates:
            if date_tuple[0]:
                unique_dates.add(date_tuple[0].strftime('%Y-%m-%d'))
        
        # Convert to sorted list
        return sorted(list(unique_dates))
    except Exception as e:
        logger.error(f"Error getting dates with data: {str(e)}")
        return []
    finally:
        session.close()

def store_billboard_chart_items(chart_data, chart_name):
    """
    Store Billboard chart data in the database with deduplication.
    
    Args:
        chart_data: Dictionary containing chart data from Billboard Charts API
        chart_name: Name of the chart (e.g., 'hot-100', 'billboard-200')
        
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        # Initialize result
        result = {
            "processed": 0,
            "added": 0,
            "skipped": 0
        }
        
        # Skip if we received empty or None data
        if not chart_data or not isinstance(chart_data, dict):
            logger.warning(f"Invalid chart data type: {type(chart_data)}")
            return result
        
        # Extract chart entries
        entries = chart_data.get('chart', {}).get('entries', [])
        if not entries:
            logger.warning("No chart entries found in data")
            return result
            
        # Get current date as string for chart_date if not in data
        chart_date = chart_data.get('chart', {}).get('date')
        if not chart_date:
            chart_date = datetime.utcnow().strftime('%Y-%m-%d')
            
        # Update processed count
        result["processed"] = len(entries)
        
        for entry in entries:
            # Skip if entry is not a dictionary
            if not isinstance(entry, dict):
                logger.warning(f"Skipping non-dictionary chart entry: {type(entry)}")
                result["skipped"] += 1
                continue
                
            # Get rank (required)
            rank = entry.get('rank')
            if rank is None:
                logger.warning("Chart entry missing rank, skipping")
                result["skipped"] += 1
                continue
                
            # Check if this chart entry already exists
            existing = session.query(Billboard_Chart_Item).filter_by(
                chart_name=chart_name,
                chart_date=chart_date,
                item_rank=rank
            ).first()
            
            if existing:
                logger.info(f"Chart entry for {chart_name} on {chart_date} at rank {rank} already exists, skipping")
                result["skipped"] += 1
                continue
                
            # Get required fields
            title = entry.get('title', '')
            artist = entry.get('artist', '')
            
            # Create new chart entry record
            new_chart_item = Billboard_Chart_Item(
                chart_name=chart_name,
                item_rank=rank,
                title=title,
                artist=artist,
                image_url=entry.get('image'),
                last_week_rank=entry.get('last_week'),
                peak_position=entry.get('peak_position'),
                weeks_on_chart=entry.get('weeks_on_chart'),
                chart_date=chart_date,
                raw_data=json.dumps(entry)
            )
            
            session.add(new_chart_item)
            result["added"] += 1
            logger.info(f"Added chart entry: {chart_name}, rank {rank}, {artist} - {title}")
            
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in store_billboard_chart_items: {str(e)}")
        # Return current result with whatever was processed before the error
        return result
    finally:
        session.close()

def get_billboard_chart_items_from_db(chart_name=None, chart_date=None, limit=100):
    """
    Retrieve Billboard chart items from the database with optional filtering.
    
    Args:
        chart_name: Optional name of chart to filter by (e.g., 'hot-100')
        chart_date: Optional date string to filter by (format: YYYY-MM-DD)
        limit: Maximum number of items to return (default: 100)
        
    Returns:
        List of Billboard_Chart_Item objects
    """
    session = Session()
    try:
        query = session.query(Billboard_Chart_Item)
        
        # Apply filters if provided
        if chart_name:
            query = query.filter(Billboard_Chart_Item.chart_name == chart_name)
            
        if chart_date:
            query = query.filter(Billboard_Chart_Item.chart_date == chart_date)
            
        # Order by chart name, date, and rank
        query = query.order_by(
            Billboard_Chart_Item.chart_name,
            Billboard_Chart_Item.chart_date.desc(),
            Billboard_Chart_Item.item_rank
        ).limit(limit)
        
        return query.all()
    finally:
        session.close()

def get_latest_chart_date(chart_name):
    """
    Get the most recent date for which we have data for a specific chart.
    
    Args:
        chart_name: Name of the chart (e.g., 'hot-100', 'billboard-200')
        
    Returns:
        String date in format YYYY-MM-DD or None if no data exists
    """
    session = Session()
    try:
        latest = session.query(Billboard_Chart_Item).filter(
            Billboard_Chart_Item.chart_name == chart_name
        ).order_by(Billboard_Chart_Item.chart_date.desc()).first()
        
        if latest:
            return latest.chart_date
        return None
    finally:
        session.close()

def should_update_billboard_chart(chart_name, days_threshold=7):
    """
    Check if the billboard chart data is older than the specified threshold 
    and should be updated.
    
    Args:
        chart_name: Name of the chart (e.g., 'hot-100')
        days_threshold: Number of days after which to update the chart data (default: 7)
        
    Returns:
        Tuple of (should_update, latest_date)
        - should_update: True if chart should be updated, False otherwise
        - latest_date: The latest chart date or None if no data exists
    """
    latest_date = get_latest_chart_date(chart_name)
    
    # If we don't have any data, we should update
    if not latest_date:
        return True, None
        
    # Parse the latest date
    try:
        latest_date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
        current_date = datetime.utcnow()
        
        # Calculate the difference in days
        delta = current_date - latest_date_obj
        
        # If it's been more than days_threshold days, we should update
        if delta.days >= days_threshold:
            return True, latest_date
        else:
            return False, latest_date
    except Exception as e:
        logger.error(f"Error parsing date in should_update_billboard_chart: {str(e)}")
        # If there's an error, be safe and return True
        return True, latest_date
        
def store_netflix_history(history_items):
    """
    Store Netflix viewing history items in the database with deduplication.
    
    Args:
        history_items: List of Netflix viewing history dictionaries
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    result = {"processed": 0, "added": 0, "skipped": 0}
    
    try:
        for item in history_items:
            result["processed"] += 1
            
            # Check if this item already exists in database
            existing = session.query(Netflix_History_Item).filter(
                Netflix_History_Item.title == item.get('title'),
                Netflix_History_Item.watch_date == item.get('watch_date')
            ).first()
            
            if existing:
                # Skip duplicate entries
                logger.debug(f"Skipping duplicate Netflix history entry: {item.get('title')}")
                result["skipped"] += 1
                continue
                
            # Create new item
            netflix_item = Netflix_History_Item(
                title=item.get('title'),
                watch_date=item.get('watch_date'),
                show_name=item.get('show_name'),
                season=item.get('season'),
                episode_name=item.get('episode_name'),
                episode_number=item.get('episode_number'),
                content_type=item.get('content_type'),
                genres=item.get('genres'),
                release_year=item.get('release_year'),
                duration=item.get('duration'),
                description=item.get('description')
            )
            
            session.add(netflix_item)
            logger.info(f"Added Netflix history item: {item.get('title')}")
            result["added"] += 1
            
        # Commit all changes
        session.commit()
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing Netflix history items: {str(e)}")
    finally:
        session.close()
        
    return result

def get_netflix_history_from_db(limit=None, order_by_recent=True):
    """
    Retrieve Netflix viewing history from the database.
    
    Args:
        limit: Optional maximum number of items to return (default: None, returns all)
        order_by_recent: If True, orders by watch_date descending (newest first)
        
    Returns:
        List of Netflix_History_Item objects
    """
    try:
        session = Session()
        query = session.query(Netflix_History_Item)
        
        # Order by watch date
        if order_by_recent:
            query = query.order_by(Netflix_History_Item.watch_date.desc())
        else:
            query = query.order_by(Netflix_History_Item.watch_date.asc())
            
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
            
        return query.all()
    except Exception as e:
        logger.error(f"Error retrieving Netflix history from database: {str(e)}")
        return []