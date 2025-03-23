from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import os
from datetime import datetime

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create declarative base
Base = declarative_base()

class Bee_Conversation(Base):
    __tablename__ = 'bee_conversations'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, unique=True)  # External ID from Bee API
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    def __repr__(self):
        return f"<Bee_Conversation(id={self.id}, created_at={self.created_at})>"

class Bee_Fact(Base):
    __tablename__ = 'bee_facts'
    
    id = Column(Integer, primary_key=True)
    fact_id = Column(String, nullable=True)  # External ID from Bee API if available
    text = Column(Text, nullable=False)
    created_at = Column(DateTime)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    # Create a unique constraint on the text field to prevent duplicates
    __table_args__ = (UniqueConstraint('text', name='uq_bee_fact_text'),)
    
    def __repr__(self):
        return f"<Bee_Fact(id={self.id}, text={self.text[:30]}...)>"

class Bee_Todo(Base):
    __tablename__ = 'bee_todos'
    
    id = Column(Integer, primary_key=True)
    todo_id = Column(String, unique=True)  # External ID from Bee API
    task = Column(Text, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    def __repr__(self):
        return f"<Bee_Todo(id={self.id}, task={self.task[:30]}..., completed={self.completed})>"

class Limitless_Lifelog(Base):
    __tablename__ = 'limitless_lifelogs'
    
    id = Column(Integer, primary_key=True)
    log_id = Column(String, unique=True)  # External ID from Limitless API
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime, nullable=True)
    log_type = Column(String, nullable=True)  # Type of lifelog (e.g., "note", "event", etc.)
    tags = Column(Text, nullable=True)  # Store tags as JSON string
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    def __repr__(self):
        return f"<Limitless_Lifelog(id={self.id}, title={self.title[:30] if self.title else 'None'}..., created_at={self.created_at})>"

class Weather_Data(Base):
    __tablename__ = 'weather_data'
    
    id = Column(Integer, primary_key=True)
    weather_id = Column(Integer, nullable=True)  # Weather condition ID from OpenWeatherMap
    location_name = Column(String, nullable=True)  # City/location name
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)  # Temperature in selected units
    feels_like = Column(Float, nullable=True)  # "Feels like" temperature
    humidity = Column(Integer, nullable=True)  # Humidity percentage
    pressure = Column(Integer, nullable=True)  # Atmospheric pressure
    wind_speed = Column(Float, nullable=True)  # Wind speed
    wind_direction = Column(Integer, nullable=True)  # Wind direction in degrees
    clouds = Column(Integer, nullable=True)  # Cloudiness percentage
    weather_main = Column(String, nullable=True)  # Main weather condition (e.g., "Clear", "Rain")
    weather_description = Column(String, nullable=True)  # Detailed weather description
    visibility = Column(Integer, nullable=True)  # Visibility in meters
    created_at = Column(DateTime, default=datetime.utcnow)  # When this record was created
    timestamp = Column(DateTime)  # The timestamp of the weather data from API
    raw_data = Column(Text)  # Store the raw JSON response for reference
    units = Column(String, default="metric")  # The units used for this record (metric, imperial, standard)
    
    # Create a unique constraint on lat, lon, and timestamp to prevent duplicates
    __table_args__ = (UniqueConstraint('latitude', 'longitude', 'timestamp', name='uq_weather_location_time'),)
    
    def __repr__(self):
        return f"<Weather_Data(id={self.id}, location={self.location_name}, temp={self.temperature}, created_at={self.created_at})>"

# Create all tables in the database
Base.metadata.create_all(engine)