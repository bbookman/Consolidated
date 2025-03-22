import os

# Get the LIMITLESS_API_KEY from environment variables
api_key = os.environ.get('LIMITLESS_API_KEY')

# Print the key with some masking for security
if api_key:
    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '****'
    print(f"LIMITLESS_API_KEY exists: {masked_key}")
    print(f"Key length: {len(api_key)} characters")
else:
    print("LIMITLESS_API_KEY is not set in environment variables")