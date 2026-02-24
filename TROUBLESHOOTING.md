# 🔧 Troubleshooting Guide

## Common Issues & Solutions

### ❌ "ModuleNotFoundError: No module named 'openai'"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### ❌ "OpenAI API key not set"

**Solution:** 
1. Get your API key from https://platform.openai.com/api-keys
2. Add it to `config.json`:
```json
"openai_api_key": "sk-your-actual-key-here"
```

### ❌ Instagram posting fails

**Possible causes:**

1. **Not logged in**
   - Open Chrome manually
   - Go to instagram.com
   - Log in and check "Remember me"

2. **Chrome profile not found**
   - Get your Chrome profile path:
     - Type `chrome://version` in Chrome address bar
     - Copy the "Profile Path"
   - Add to `config.json`:
   ```json
   "chrome_profile_path": "C:\\Users\\gageg\\AppData\\Local\\Google\\Chrome\\User Data"
   ```

3. **Instagram UI changed**
   - Instagram sometimes changes their website
   - The bot may need updates to XPath selectors
   - Check logs for specific errors

### ❌ "selenium.common.exceptions.WebDriverException"

**Solution:** Update ChromeDriver
```bash
pip install --upgrade selenium webdriver-manager
```

### ❌ Scheduled tasks not running

**Check Task Scheduler:**
1. Press Windows key
2. Type "Task Scheduler"
3. Find "AIArtBot" tasks
4. Right-click → Properties → Check settings
5. Look at "Last Run Result" for errors

**Common fixes:**
- Make sure Python is in your system PATH
- Run Task Scheduler as Administrator
- Check that the paths in scheduled tasks are correct

### ❌ "Insufficient credits" from OpenAI

**Solution:**
1. Go to https://platform.openai.com/account/billing
2. Add payment method and credits
3. Each image costs ~$0.04

### ❌ Images generate but don't post

**Check:**
1. Is Chrome logged into Instagram?
2. Are there unposted images?
   - Look in `generated_images/` folder
   - Check `YYYYMMDD_metadata.json` file
3. Run manually to see error:
   ```bash
   python art_bot.py post
   ```

### ❌ "Rate limit exceeded" from OpenAI

**Solution:**
- DALL-E 3 has rate limits (50 images/minute for standard)
- The bot adds delays between generations
- If you still hit limits, increase the delay in `art_bot.py`:
  ```python
  time.sleep(5)  # Change from 2 to 5 seconds
  ```

## 📊 Checking Logs

Logs are saved in the `logs/` folder:
```bash
# View today's log
type logs\bot_20241030.log

# Or open in notepad
notepad logs\bot_20241030.log
```

Look for:
- `ERROR` messages for failures
- `INFO` messages for successful operations
- Timestamps showing when operations ran

## 🔍 Debugging Steps

1. **Test each component separately:**
   ```bash
   # Test prompts (no API calls)
   python art_bot.py test
   
   # Test generation (uses API)
   python art_bot.py generate
   
   # Test posting
   python art_bot.py post
   ```

2. **Check your config.json:**
   - Is the API key correct?
   - Are paths using double backslashes? (`\\`)
   - Is it valid JSON? (use a JSON validator online)

3. **Run with Python directly:**
   ```bash
   python -c "import sys; print(sys.version)"
   python -c "import openai; print('OpenAI imported OK')"
   python -c "import selenium; print('Selenium imported OK')"
   ```

4. **Check file permissions:**
   - Can the bot write to `generated_images/` folder?
   - Can it read `config.json`?

## 💡 Performance Tips

**Speed up image generation:**
- Images are generated sequentially to avoid rate limits
- Each takes ~10-20 seconds
- Total time for 4 images: ~1-2 minutes

**Reduce Instagram posting failures:**
- Use your Chrome profile (add `chrome_profile_path` to config)
- Keep Chrome updated
- Don't manually interfere while bot is posting

## 🆘 Still Having Issues?

1. Check the logs in `logs/` folder
2. Make sure all dependencies are installed: `pip list`
3. Verify Python version: `python --version` (need 3.8+)
4. Check OpenAI API status: https://status.openai.com/
5. Check Instagram status: https://www.isitdownrightnow.com/instagram.com

## 📝 Getting Help

When asking for help, provide:
- Error message from logs
- Your Python version
- What command you ran
- Contents of config.json (WITHOUT your API key!)
