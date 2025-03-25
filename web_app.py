"""
Life Journal Web Interface

This script provides a web interface for viewing Bee, Netflix, and Limitless data
organized as a journal of daily activities.
"""

from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime, timedelta
import database_handler as db
from sqlalchemy import and_, func, extract
import models
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Create the Flask application
app = Flask(__name__)

# Get database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)

# Function to get a database session with connection check
def get_db_session():
    """Get a database session with connection verification"""
    session = Session()
    try:
        # Test the connection with a simple query
        session.execute("SELECT 1")
        return session
    except Exception as e:
        # Close the session if connection failed
        session.close()
        # Try to create a new session
        new_session = Session()
        return new_session

# Ensure templates directory exists
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    """Home page showing the calendar view of all data."""
    return render_template('index.html')

@app.route('/test')
def test():
    """Simple test endpoint to verify the application is running."""
    return jsonify({
        "status": "success",
        "message": "Web application is running correctly.",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/journal_data')
def journal_data():
    """API endpoint to get journal data for a specific date range."""
    # Get date range from query parameters
    try:
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        # Default to last 30 days if no dates provided
        if not start_date:
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=30)
        else:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date_obj = start_date_obj + timedelta(days=1)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Query data from all sources with connection retry
    session = get_db_session()
    try:
        # Format dates for query
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
        
        # Get Bee conversations
        bee_conversations = session.query(models.Bee_Conversation).filter(
            and_(
                models.Bee_Conversation.created_at >= start_date_obj,
                models.Bee_Conversation.created_at < end_date_obj + timedelta(days=1)
            )
        ).order_by(models.Bee_Conversation.created_at.desc()).all()
        
        # Facts removed as requested
        bee_facts = []  # Empty list to maintain compatibility with existing code
        
        # Get Limitless lifelogs
        lifelogs = session.query(models.Limitless_Lifelog).filter(
            and_(
                models.Limitless_Lifelog.created_at >= start_date_obj,
                models.Limitless_Lifelog.created_at < end_date_obj + timedelta(days=1)
            )
        ).order_by(models.Limitless_Lifelog.created_at.desc()).all()
        
        # Get Netflix viewing history
        netflix_history = session.query(models.Netflix_History_Item).filter(
            and_(
                models.Netflix_History_Item.watch_date >= start_date_obj,
                models.Netflix_History_Item.watch_date < end_date_obj + timedelta(days=1)
            )
        ).order_by(models.Netflix_History_Item.watch_date.desc()).all()
        
        # Process data into a format suitable for the journal
        days_data = {}
        
        # Process Bee conversations
        for conv in bee_conversations:
            day_key = conv.created_at.strftime('%Y-%m-%d')
            if day_key not in days_data:
                days_data[day_key] = {
                    'date': day_key,
                    'conversations': [],
                    'facts': [],
                    'lifelogs': [],
                    'netflix': []
                }
            
            # Extract summary, atmosphere, and key takeaways
            summary = conv.summary or ""
            atmosphere = conv.atmosphere or ""
            
            # Handle key_takeaways as JSON or convert to string as needed
            key_takeaways = ""
            if conv.key_takeaways:
                if isinstance(conv.key_takeaways, list):
                    # It's already a JSON list, we'll handle the formatting in the frontend
                    key_takeaways = conv.key_takeaways
                elif isinstance(conv.key_takeaways, str):
                    # Legacy format, convert lines to a list
                    key_takeaways = [line.strip() for line in conv.key_takeaways.split('\n') if line.strip()]
            
            days_data[day_key]['conversations'].append({
                'id': conv.id,
                'summary': summary,
                'atmosphere': atmosphere,
                'key_takeaways': key_takeaways,
                'time': conv.created_at.strftime('%H:%M'),
                'location': conv.address if conv.address else None,
                'latitude': conv.latitude,
                'longitude': conv.longitude
            })
        
        # Process Bee facts
        for fact in bee_facts:
            day_key = fact.created_at.strftime('%Y-%m-%d')
            if day_key not in days_data:
                days_data[day_key] = {
                    'date': day_key,
                    'conversations': [],
                    'facts': [],
                    'lifelogs': [],
                    'netflix': []
                }
            
            days_data[day_key]['facts'].append({
                'id': fact.id,
                'text': fact.text,
                'time': fact.created_at.strftime('%H:%M')
            })
        
        # Process Limitless lifelogs
        for log in lifelogs:
            day_key = log.created_at.strftime('%Y-%m-%d')
            if day_key not in days_data:
                days_data[day_key] = {
                    'date': day_key,
                    'conversations': [],
                    'facts': [],
                    'lifelogs': [],
                    'netflix': []
                }
            
            days_data[day_key]['lifelogs'].append({
                'id': log.id,
                'title': log.title or "Untitled",
                'description': log.description,
                'time': log.created_at.strftime('%H:%M'),
                'log_type': log.log_type,
                'tags': json.loads(log.tags) if log.tags else []
            })
        
        # Process Netflix viewing history
        for item in netflix_history:
            day_key = item.watch_date.strftime('%Y-%m-%d')
            if day_key not in days_data:
                days_data[day_key] = {
                    'date': day_key,
                    'conversations': [],
                    'facts': [],
                    'lifelogs': [],
                    'netflix': []
                }
            
            # Get enriched data if available
            title_info = session.query(models.Netflix_Title_Info).filter_by(title=item.title).first()
            
            watch_entry = {
                'id': item.id,
                'title': item.title,
                'time': item.watch_date.strftime('%H:%M'),
                'show_name': item.show_name,
                'season': item.season,
                'episode_name': item.episode_name,
                'content_type': item.content_type or (title_info.content_type if title_info else None),
                'release_year': item.release_year or (title_info.release_year if title_info else None),
                'genres': json.loads(item.genres) if item.genres else (
                    json.loads(title_info.genres) if title_info and title_info.genres else []
                ),
                'poster_url': title_info.poster_url if title_info else None,
                'imdb_score': title_info.imdb_score if title_info else None
            }
            
            days_data[day_key]['netflix'].append(watch_entry)
        
        # Convert to list and sort by date
        days_list = [days_data[day] for day in sorted(days_data.keys(), reverse=True)]
        
        return jsonify({
            "status": "success",
            "date_range": {
                "start": start_date_str,
                "end": end_date_str
            },
            "days": days_list
        })
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/api/date_counts')
def date_counts():
    """Get counts of entries by date for calendar visualization."""
    session = get_db_session()
    try:
        # Default to last 365 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Custom date range if provided
        if request.args.get('start_date'):
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
        if request.args.get('end_date'):
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
        
        # Dictionary to hold counts by date
        date_data = {}
        
        # Query Bee conversations counts by date
        conv_counts = session.query(
            func.date(models.Bee_Conversation.created_at).label('date'),
            func.count().label('count')
        ).filter(
            and_(
                models.Bee_Conversation.created_at >= start_date,
                models.Bee_Conversation.created_at <= end_date
            )
        ).group_by(func.date(models.Bee_Conversation.created_at)).all()
        
        for date_str, count in conv_counts:
            date_key = date_str.strftime('%Y-%m-%d')
            if date_key not in date_data:
                date_data[date_key] = {'conversations': 0, 'facts': 0, 'lifelogs': 0, 'netflix': 0, 'total': 0}
            date_data[date_key]['conversations'] = count
            date_data[date_key]['total'] += count
        
        # Facts queries removed as requested
        
        # Query Limitless lifelogs counts by date
        lifelog_counts = session.query(
            func.date(models.Limitless_Lifelog.created_at).label('date'),
            func.count().label('count')
        ).filter(
            and_(
                models.Limitless_Lifelog.created_at >= start_date,
                models.Limitless_Lifelog.created_at <= end_date
            )
        ).group_by(func.date(models.Limitless_Lifelog.created_at)).all()
        
        for date_str, count in lifelog_counts:
            date_key = date_str.strftime('%Y-%m-%d')
            if date_key not in date_data:
                date_data[date_key] = {'conversations': 0, 'facts': 0, 'lifelogs': 0, 'netflix': 0, 'total': 0}
            date_data[date_key]['lifelogs'] = count
            date_data[date_key]['total'] += count
        
        # Query Netflix history counts by date
        netflix_counts = session.query(
            func.date(models.Netflix_History_Item.watch_date).label('date'),
            func.count().label('count')
        ).filter(
            and_(
                models.Netflix_History_Item.watch_date >= start_date,
                models.Netflix_History_Item.watch_date <= end_date
            )
        ).group_by(func.date(models.Netflix_History_Item.watch_date)).all()
        
        for date_str, count in netflix_counts:
            date_key = date_str.strftime('%Y-%m-%d')
            if date_key not in date_data:
                date_data[date_key] = {'conversations': 0, 'facts': 0, 'lifelogs': 0, 'netflix': 0, 'total': 0}
            date_data[date_key]['netflix'] = count
            date_data[date_key]['total'] += count
        
        # Convert to list format with date as key
        result = [{"date": date, **counts} for date, counts in date_data.items()]
        
        return jsonify({
            "status": "success",
            "date_counts": result
        })
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/day/<date>')
def day_view(date):
    """Show journal for a specific day."""
    try:
        # Validate date format
        datetime.strptime(date, '%Y-%m-%d')
        return render_template('day.html', date=date)
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD", 400

if __name__ == '__main__':
    # Create templates directory if needed
    os.makedirs('templates', exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)