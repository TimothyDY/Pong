#!/usr/bin/env python3
"""
Vercel build script for Pong Game
This script runs during the build process to set up the application
"""

import os
import sys
from run import app, init_database

def main():
    """Main build function"""
    print("Starting Vercel build process...")
    
    # Initialize database
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        # Don't fail the build for database issues
        pass
    
    print("Vercel build process completed")

if __name__ == "__main__":
    main()
