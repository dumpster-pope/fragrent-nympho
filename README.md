# AI Art Bot - Setup Guide

## 🎨 What This Bot Does

Automatically generates 3-6 weird, artistic AI images daily using DALL-E and posts them to Instagram at varying times throughout the day.

## 📋 Prerequisites

1. **Python 3.8+** installed on your PC
2. **Google Chrome** browser installed
3. **OpenAI API Key** (for DALL-E 3)
4. **Instagram account** already logged in on Chrome

## 🚀 Setup Instructions

### Step 1: Install Python Dependencies

Open PowerShell or Command Prompt in the `C:\Users\gageg\AIArtBot` directory and run:

```bash
pip install -r requirements.txt
```

### Step 2: Get Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (it starts with "sk-...")

### Step 3: Configure the Bot

Edit `config.json` and fill in:

```json
{
    "openai_api_key": "sk-your-actual-api-key-here",
    "instagram_username": "your_instagram_username",
    "num_images_per_day": 4,
    "chrome_profile_path": "",
    "last_run_date": null,
    "posting_times": ["09:00", "12:00", "15:00", "18:00"]
}
```

**Optional:** To use your existing Chrome profile (so you stay logged into Instagram):

1. Find your Chrome profile path:
   - Type `chrome://version` in Chrome
   - Copy the "Profile Path" (e.g., `C:\Users\gageg\AppData\Local\Google\Chrome\User Data`)
2. Add it to `config.json`:
   ```json
   "chrome_profile_path": "C:\\Users\\gageg\\AppData\\Local\\Google\\Chrome\\User Data",
   ```

### Step 4: Log into Instagram on Chrome

1. Open Chrome and go to https://www.instagram.com
2. Log in to your account
3. Make sure "Remember me" is checked
4. Keep Chrome open

### Step 5: Test the Bot

Test prompt generation:
```bash
python art_bot.py test
```

Test image generation (will use 1 DALL-E API credit):
```bash
python art_bot.py generate
```

Test Instagram posting (make sure Chrome is logged in):
```bash
python art_bot.py post
```

### Step 6: Setup Automatic Scheduling

Run PowerShell **as Administrator** and execute:

```powershell
cd C:\Users\gageg\AIArtBot
.\setup_scheduler.ps1
```

This creates Windows scheduled tasks that will:
- **Generate images** at 2:00 AM daily
- **Post images** at 9:00 AM, 12:00 PM, 3:00 PM, and 6:00 PM daily

## 📁 Folder Structure

```
AIArtBot/
├── art_bot.py              # Main bot script
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── setup_scheduler.ps1     # Scheduler setup script
├── README.md              # This file
├── generated_images/       # Saved AI images
│   ├── YYYYMMDD_01.png
│   ├── YYYYMMDD_02.png
│   └── YYYYMMDD_metadata.json
└── logs/                   # Bot logs
    └── bot_YYYYMMDD.log
```

## 🎯 How It Works

1. **2:00 AM** - Bot generates 3-6 weird, artistic prompts
2. **2:00 AM** - Bot creates images using DALL-E 3
3. **Throughout the day** - Bot posts images at scheduled times with captions showing the date, time, and prompt

## 🎨 Customization

### Change Number of Images Per Day

Edit `config.json`:
```json
"num_images_per_day": 6,
```


### Change Posting Times

Edit `config.json`:
```json
"posting_times": ["08:00", "11:30", "14:00", "17:30", "20:00", "23:00"],
```

Then re-run the scheduler setup script.

### Modify Prompt Themes

Edit `art_bot.py` and customize the `themes`, `styles`, and `modifiers` lists in the `generate_creative_prompts()` method.

## 💰 Costs

- **DALL-E 3 Standard Quality**: ~$0.04 per image
- **Daily cost** (4 images): ~$0.16/day = ~$4.80/month
- **Daily cost** (6 images): ~$0.24/day = ~$7.20/month

## 🔧 Troubleshooting

### Instagram posting fails

1. Make sure Chrome is logged into Instagram
2. Try using your Chrome profile path in `config.json`
3. Instagram may have changed their UI - check the XPath selectors in `post_to_instagram()`

### Images not generating

1. Check your OpenAI API key is valid
2. Make sure you have API credits
3. Check logs in `logs/` folder for error messages

### Scheduled tasks not running

1. Open Task Scheduler (search in Windows)
2. Find "AIArtBot" tasks
3. Check "Last Run Result" for errors
4. Make sure Python is in your PATH

## 📝 Manual Commands

```bash
# Generate today's images
python art_bot.py generate

# Post next scheduled image
python art_bot.py post

# Test prompt generation (no API calls)
python art_bot.py test
```

## 🎉 Features

✅ Ultra-descriptive, creative prompts with 20+ themes
✅ Automatic daily image generation
✅ Scheduled Instagram posting
✅ Metadata tracking (prompts, timestamps, post status)
✅ Comprehensive logging
✅ Configurable posting times
✅ Works with Chrome profiles (stay logged in)

## 🌟 Example Prompts

The bot generates prompts like:

- "A surreal dreamscapes scene featuring bathed in neon light, rendered in hyperdetailed digital art, with intricate details and dramatic lighting"
- "An otherworldly landscape of cyberpunk oddities, shrouded in mist, created in the style of watercolor illustration, highly detailed and atmospheric"
- "A mysterious entity from interdimensional beings dimension, crystallized and frozen, visualized as 3D rendered CGI, with rich textures and surreal composition"

## 📞 Support

Check logs in the `logs/` folder for detailed error messages and bot activity.

---

**Enjoy your automated AI art Instagram feed! 🎨✨**
