# TikTok Video Saver (free, no API key)

Flask backend + yt-dlp + a single HTML page. One folder, one free service.

## Run on your computer
```
pip install -r requirements.txt
python app.py
```
Open http://localhost:5000

## Put it online for free (Render)
1. Make a free GitHub account and create a new repository.
2. Upload all these files (app.py, requirements.txt, render.yaml, templates/index.html).
3. Make a free account at render.com and choose New > Web Service, then connect your GitHub repo.
4. Render reads render.yaml. If it asks: Build Command `pip install -r requirements.txt`,
   Start Command `gunicorn app:app --workers 1 --threads 4 --timeout 120`, Plan: Free.
5. Click Deploy. You get a free link like https://video-saver.onrender.com

## Things to know
- Free plan sleeps after ~15 minutes idle; the first visit then takes about 30-60 seconds.
- If downloads suddenly stop working, TikTok changed something. Fix: redeploy
  (Render > Manual Deploy > Clear build cache & deploy) so the newest yt-dlp installs.
- The app only accepts tiktok.com links, limits each visitor to 6 requests a minute,
  and caps files at 100 MB.
- Only download your own videos or videos you have permission to use.
