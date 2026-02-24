"""
AI Art Bot - Interactive Setup Helper
Run this script to set up your bot configuration interactively
"""

import json
import os
from pathlib import Path

def setup_wizard():
    print("=" * 60)
    print("  🎨 AI ART BOT - INTERACTIVE SETUP WIZARD")
    print("=" * 60)
    print()
    
    config_path = Path(__file__).parent / "config.json"
    
    # Load existing config or create new one
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("✓ Found existing configuration")
        print()
    else:
        config = {
            "openai_api_key": "",
            "instagram_username": "",
            "num_images_per_day": 4,
            "chrome_profile_path": "",
            "last_run_date": None,
            "posting_times": ["09:00", "12:00", "15:00", "18:00"]
        }
    
    # OpenAI API Key
    print("1️⃣  OPENAI API KEY")
    print("   Get your key at: https://platform.openai.com/api-keys")
    current = config.get("openai_api_key", "")
    if current:
        print(f"   Current: {current[:10]}...{current[-4:]}")
        use_existing = input("   Keep this key? (y/n): ").lower()
        if use_existing != 'y':
            current = ""
    if not current:
        api_key = input("   Enter your OpenAI API key: ").strip()
        config["openai_api_key"] = api_key
    print()
    
    # Instagram Username
    print("2️⃣  INSTAGRAM USERNAME")
    current = config.get("instagram_username", "")
    if current:
        print(f"   Current: @{current}")
        use_existing = input("   Keep this username? (y/n): ").lower()
        if use_existing != 'y':
            current = ""
    if not current:
        username = input("   Enter your Instagram username: ").strip()
        config["instagram_username"] = username
    print()
    
    # Number of images
    print("3️⃣  NUMBER OF IMAGES PER DAY")
    print("   Note: Each image costs ~$0.04")
    print("   - 4 images = $0.16/day = $4.80/month")
    print("   - 6 images = $0.24/day = $7.20/month")
    current = config.get("num_images_per_day", 4)
    num_images = input(f"   Enter number of images per day [{current}]: ").strip()
    if num_images:
        config["num_images_per_day"] = int(num_images)
    print()
    
    # Chrome profile (optional)
    print("4️⃣  CHROME PROFILE PATH (Optional)")
    print("   This keeps you logged into Instagram automatically")
    print("   To find it: Type 'chrome://version' in Chrome, copy Profile Path")
    current = config.get("chrome_profile_path", "")
    if current:
        print(f"   Current: {current}")
        use_existing = input("   Keep this path? (y/n): ").lower()
        if use_existing != 'y':
            current = ""
    if not current:
        chrome_path = input("   Enter Chrome profile path (or press Enter to skip): ").strip()
        if chrome_path:
            config["chrome_profile_path"] = chrome_path
    print()
    
    # Posting times
    print("5️⃣  POSTING TIMES")
    print(f"   Current times: {', '.join(config.get('posting_times', []))}")
    change_times = input("   Change posting times? (y/n): ").lower()
    if change_times == 'y':
        print("   Enter times in HH:MM format (24-hour), separated by commas")
        print("   Example: 09:00, 12:00, 15:00, 18:00, 21:00")
        times_input = input("   Enter times: ").strip()
        if times_input:
            times = [t.strip() for t in times_input.split(',')]
            config["posting_times"] = times
    print()
    
    # Save configuration
    with open(config_path, 'w') as f:
        json.dump(config, indent=4, fp=f)
    
    print("=" * 60)
    print("  ✅ CONFIGURATION SAVED!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Make sure Instagram is logged in on Chrome")
    print("  2. Test the bot:")
    print("     python art_bot.py test       # Test prompts (free)")
    print("     python art_bot.py generate   # Generate images ($0.04 each)")
    print("     python art_bot.py post       # Post to Instagram")
    print()
    print("  3. Setup automatic scheduling:")
    print("     Run PowerShell as Administrator:")
    print("     .\\setup_scheduler.ps1")
    print()
    print("📖 For detailed help, see README.md")
    print()

if __name__ == "__main__":
    try:
        setup_wizard()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
