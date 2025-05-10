#!/usr/bin/env python3
"""
Flag Downloader Script for NVC Banking Platform
Downloads country flag SVGs for all currencies in our system
"""
import os
import requests
import time
from pathlib import Path

# Flag CDN URL
FLAG_CDN_URL = "https://cdn.jsdelivr.net/gh/lipis/flag-icons@main/flags/4x3/{}.svg"

# List of country codes to download flags for
COUNTRY_CODES = [
    # Major world currencies
    "us", "gb", "eu", "jp", "ch", "ca", "au", "nz", "cn", "hk", 
    "sg", "in", "ru", "br", "mx", "se", "no", "dk", "pl", "tr",
    
    # North African countries
    "dz", "eg", "ly", "ma", "sd", "tn",
    
    # West African countries
    "ng", "gh", "sn", "gm", "gn", "lr", "sl", "cv", 
    
    # Central African countries
    "cm", "cd", "st",
    
    # East African countries
    "ke", "et", "ug", "tz", "rw", "bi", "dj", "er", "ss", "so",
    
    # Southern African countries
    "za", "ls", "na", "sz", "bw", "zm", "mw", "zw", "mz", "mg", "sc", "mu", "ao",
    
    # Asian countries
    "id", "my", "ph", "th", "vn", "kr", "tw", "pk", "bd", "np", "lk",
    
    # Middle Eastern countries
    "ae", "sa", "qa", "om", "bh", "kw", "il", "jo", "lb", "ir", "iq",
    
    # Latin American countries
    "ar", "cl", "co", "pe", "uy", "ve", "bo", "py", "do", "cr", "jm", "tt",
    
    # European countries (non-Euro)
    "cz", "hu", "ro", "bg", "hr", "rs", "ua", "by"
]

# Set directory for flags
FLAGS_DIR = Path("static/images/flags")

def download_flag(country_code):
    """Download a flag SVG for a specific country code"""
    output_file = FLAGS_DIR / f"{country_code}.svg"
    
    # Skip if flag already exists
    if output_file.exists():
        print(f"Flag for {country_code} already exists, skipping.")
        return True
    
    url = FLAG_CDN_URL.format(country_code)
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"Downloaded flag for {country_code}")
            return True
        else:
            print(f"Failed to download flag for {country_code}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading flag for {country_code}: {str(e)}")
        return False

def main():
    """Main function to download all flags"""
    # Create flags directory if it doesn't exist
    os.makedirs(FLAGS_DIR, exist_ok=True)
    
    # Download flags with a small delay between requests
    success_count = 0
    for country_code in COUNTRY_CODES:
        if download_flag(country_code):
            success_count += 1
        time.sleep(0.2)  # Small delay to avoid overloading the server
    
    print(f"\nDownloaded {success_count} flags out of {len(COUNTRY_CODES)} country codes")

if __name__ == "__main__":
    main()