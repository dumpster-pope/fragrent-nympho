# AI Art Bot — Quick Start

Generates **1 artistic image per hour** (24/day) using Grok's browser image
generation. Images land in `C:\Users\gageg\Desktop\AI_Art\`.

---

## 1 · Install dependencies (once)

```
cd C:\Users\gageg\AIArtBot
pip install -r requirements.txt
```

---

## 2 · Point the bot at your Chrome profile (keeps you logged in)

1. Open Chrome → address bar → type `chrome://version` → press Enter
2. Find **"Profile Path"** — copy everything **up to but not including** `\Default`
   - Example: `C:\Users\gageg\AppData\Local\Google\Chrome\User Data`
3. Open `config.json` and paste that path:

```json
{
    "chrome_profile_path": "C:\\Users\\gageg\\AppData\\Local\\Google\\Chrome\\User Data",
    "instagram_username": "",
    "instagram_password": "",
    "last_run": null
}
```

> Make sure you are already **logged into grok.com** in that Chrome profile.
> Log in once manually — the bot reuses the saved session every run.

---

## 3 · Test it right now

```
python art_bot.py run
```

Chrome opens, navigates to grok.com, submits a creative prompt, waits for the
image, downloads it, and saves it to `Desktop\AI_Art\`. Watch the terminal.

Preview a prompt without opening the browser:
```
python art_bot.py test
```

---

## 4 · Schedule to run every hour (24 images / day)

Open **PowerShell as Administrator** and run:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser   # only needed once
C:\Users\gageg\AIArtBot\setup_scheduler.ps1
```

Windows Task Scheduler will now fire the bot at the top of every hour.

---

## Where are my images?

```
C:\Users\gageg\Desktop\AI_Art\
    20260223_140000_An_ancient_lighthouse.png
    20260223_140000_An_ancient_lighthouse_meta.json   <- prompt + timestamp
    20260223_150001_A_city_suspended_inside.png
    ...
```

Each image has a `_meta.json` sidecar with the full prompt used.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser opens but can't find input | Confirm grok.com is reachable and you are logged in |
| Timeout — screenshot saved in logs/ | Grok's UI may have changed; check the screenshot |
| "No Chrome profile" warning | Set `chrome_profile_path` in config.json |
| Task Scheduler runs but nothing happens | Open Task Scheduler → check "Last Run Result" for AIArtBot_Hourly |

Logs → `C:\Users\gageg\AIArtBot\logs\`  (one file per day)

---

## Instagram upload (coming next)

`post_to_instagram()` in `art_bot.py` is already stubbed out.
Once image generation is running reliably, we'll wire up an agent that picks
images from `Desktop\AI_Art\` and posts them at randomised times each day.
