# 🎨 AI ART BOT - COMPLETE INSTALLATION GUIDE

## ✅ Everything You Have Now

```
C:\Users\gageg\AIArtBot\
│
├── 📜 Main Files
│   ├── art_bot.py                 # Main bot (273 lines of Python)
│   ├── config.json               # Your settings (edit this!)
│   ├── setup_wizard.py           # Interactive setup helper
│   └── requirements.txt          # Python dependencies
│
├── 🚀 Setup Scripts
│   ├── setup_scheduler.ps1       # Windows Task Scheduler setup
│   └── test_setup.bat           # Quick test script
│
├── 📚 Documentation
│   ├── START_HERE.txt           # ⭐ READ THIS FIRST
│   ├── QUICKSTART.md            # 5-minute setup
│   ├── README.md                # Full documentation
│   ├── TROUBLESHOOTING.md       # Fix problems
│   └── PROJECT_SUMMARY.md       # What this does
│
└── 📁 Folders
    ├── generated_images/        # AI images saved here
    └── logs/                   # Bot activity logs
```

## 🎯 Your Next Steps (Choose One Path)

### Path A: Interactive Setup (Easiest! ⭐)

1. Open PowerShell in `C:\Users\gageg\AIArtBot`
2. Run: `python setup_wizard.py`
3. Answer the questions
4. Done!

### Path B: Manual Setup (More Control)

1. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```


2. **Get OpenAI API Key:**
   - Visit: https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy it (starts with "sk-")

3. **Edit config.json:**
   ```json
   {
       "openai_api_key": "sk-your-key-here",
       "instagram_username": "your_username",
       "num_images_per_day": 4
   }
   ```

4. **Login to Instagram:**
   - Open Chrome
   - Go to instagram.com
   - Log in (check "Remember me")

5. **Test it:**
   ```bash
   python art_bot.py test       # Free
   python art_bot.py generate   # $0.16 for 4 images
   python art_bot.py post       # Posts to Instagram
   ```

6. **Automate (PowerShell as Admin):**
   ```powershell
   .\setup_scheduler.ps1
   ```

## 🎨 What Happens Next

Once automated, your bot will:

**Every day at 2:00 AM:**
- Generate 3-6 creative prompts
- Create images with DALL-E 3
- Save them to `generated_images/`

**Throughout the day:**
- 9:00 AM → Post image #1
- 12:00 PM → Post image #2
- 3:00 PM → Post image #3
- 6:00 PM → Post image #4

Each post includes:
- Date and time
- The full AI prompt used
- Relevant hashtags

## 🧪 Testing Before Automation

**Test 1: Prompts (FREE)**
```bash
python art_bot.py test
```
Should show creative prompts. No API calls.

**Test 2: Image Generation**
```bash
python art_bot.py generate
```
Will create 3-6 images. Costs ~$0.16 (4 images × $0.04)

**Test 3: Instagram Upload**
```bash
python art_bot.py post
```
Must be logged into Instagram on Chrome first!

## 💰 Cost Breakdown

| Setting | Images/Day | Daily Cost | Monthly Cost |
|---------|------------|------------|--------------|
| Light   | 3 images   | $0.12      | $3.60        |
| **Default** | **4 images** | **$0.16** | **$4.80** |
| Heavy   | 6 images   | $0.24      | $7.20        |

*DALL-E 3 pricing: $0.04 per 1024x1024 image*

## 🎨 Example Output

The bot creates prompts like:

> **"An otherworldly landscape of cyberpunk oddities, bathed in neon light, created in the style of hyperdetailed digital art, highly detailed and atmospheric"**

> **"A mysterious entity from bioluminescent creatures dimension, shrouded in mist, visualized as 3D rendered CGI, with rich textures and surreal composition"**

> **"An impossible structure inspired by cosmic horror, dissolving into particles, depicted in watercolor illustration, with ethereal quality"**


## 🎨 Creative Elements (Built-in)

**20+ Themes:**
- Surreal dreamscapes, Cyberpunk oddities, Bioluminescent creatures
- Impossible architecture, Cosmic horror, Whimsical steampunk
- Retrofuturistic nostalgia, Alien botanicals, Glitch aesthetics
- Mystical folklore, Post-apocalyptic beauty, Underwater civilizations
- Interdimensional beings, Neon noir, Crystalline formations
- And more!

**16+ Art Styles:**
- Hyperdetailed digital art, Oil painting, Watercolor
- 3D rendered CGI, Pencil sketch, Mixed media collage
- Ukiyo-e woodblock, Art Nouveau, Abstract expressionism
- Photorealistic render, Vaporwave, 80s airbrush
- Gothic illuminated manuscript, Minimalist, Maximalist baroque
- And more!

**15+ Modifiers:**
- Bathed in neon light, Shrouded in mist, Reflected in water
- Viewed through kaleidoscope, Emerging from shadows
- Dissolving into particles, Suspended in time
- Fragmented and reassembled, Overgrown with flora
- Crystallized and frozen, Warped by gravity
- And more!

## ⚙️ Customization

Edit `config.json` to change:
- Number of images per day
- Posting times
- Instagram username
- Chrome profile path

Edit `art_bot.py` to change:
- Prompt themes and styles
- Image quality/size
- Caption format and hashtags

## 🔐 Security & Privacy

✅ All data stays on your PC
✅ API key stored locally in config.json
✅ Uses Chrome's existing Instagram session
✅ No external data collection
