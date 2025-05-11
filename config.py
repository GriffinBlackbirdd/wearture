import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-for-jwt-keep-this-very-secure")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"