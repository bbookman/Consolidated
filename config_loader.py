"""
Configuration Loader

This module loads configuration settings from the config.yml file
and provides default values if the file doesn't exist or is incomplete.
"""

import os
import yaml
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "default_location": {
        "name": "San Francisco",
        "latitude": 37.7749,
        "longitude": -122.4194
    },
    "weather": {
        "units": "metric",
        "max_age_hours": 24
    }
}

def load_config():
    """
    Load configuration from config.yml file or return default values if not found
    
    Returns:
        Dictionary containing configuration values
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                config = yaml.safe_load(config_file)
                
                # Validate and ensure required config sections exist
                if not config:
                    logger.warning("Config file is empty, using default values")
                    return DEFAULT_CONFIG
                
                # Ensure default_location section exists
                if "default_location" not in config:
                    logger.warning("No default_location in config, using default values")
                    config["default_location"] = DEFAULT_CONFIG["default_location"]
                    
                # Ensure weather section exists    
                if "weather" not in config:
                    logger.warning("No weather section in config, using default values")
                    config["weather"] = DEFAULT_CONFIG["weather"]
                
                logger.info(f"Configuration loaded from {config_path}")
                return config
        else:
            logger.warning(f"Config file not found at {config_path}, using default values")
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return DEFAULT_CONFIG
        
def get_default_location():
    """
    Get the default location coordinates from the configuration
    
    Returns:
        Tuple of (latitude, longitude, name) or None if not configured
    """
    config = load_config()
    location = config.get("default_location", {})
    
    # Ensure we have both latitude and longitude
    if "latitude" in location and "longitude" in location:
        return (
            location["latitude"], 
            location["longitude"], 
            location.get("name", "Default Location")
        )
    return None
    
def get_weather_config():
    """
    Get the weather configuration settings
    
    Returns:
        Dictionary with weather configuration values
    """
    config = load_config()
    return config.get("weather", DEFAULT_CONFIG["weather"])