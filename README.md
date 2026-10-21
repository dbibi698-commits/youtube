# Murshid Developer — Video Sharing Platform

A runnable Flask web-app starter inspired by video-sharing platforms, with a mobile-first interface. It is **not a copy of YouTube's private backend** and cannot provide every production YouTube feature from a ZIP alone.

## Included
- Email/password registration and login; duplicate email is rejected
- Admin role for `dbibi698@gmail.com` **when that address registers**
- Password hashing, session login/logout, profile name/bio/avatar editing
- Video uploads, thumbnails, title, description, tags, category, captions text
- Public/private videos, Shorts/long-video type, browser playback
- Home feed, search, category filter, latest/popular sorting
- Channel page, channel search endpoint, subscriber count and subscribe/unsubscribe
- Likes/dislikes, comments, view counts, watch history
- Notifications for subscriptions, uploads, likes and comments (polling/in-app)
- Playback speed and quality preference UI (quality preference does not transcode files)
- Long-video download route can be accessed from the media URL; Shorts download is intentionally not promoted in the UI
- Edit/delete own video API endpoints
- Admin overview, user block/unblock, restrict/delete video
- Responsive HTML/CSS/JavaScript frontend

## Run on Android (Termux)
1. Extract the ZIP.
2. In Termux, navigate into the extracted folder.
3. Run:
   ```bash
   pkg update
   pkg install python
   pip install -r requirements.txt
   python app.py
   ```
4. Open `http://127.0.0.1:5000` in Chrome.

## Run on PC (VS Code / terminal)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then visit `http://127.0.0.1:5000`.

## Admin setup
The default admin email is `dbibi698@gmail.com`. Register using that email to receive the admin role. For deployment, set a strong `SECRET_KEY` and `ADMIN_EMAIL` environment variables. Do not share the admin password.

## Important production limitations
This project uses a local JSON file and local `uploads/` folder to keep setup simple. It is for learning and prototype testing, not a hardened public service. A public multi-user deployment should use PostgreSQL, cloud/object storage, HTTPS, a production WSGI server, backups, upload scanning, rate limiting, CSRF protection, and monitoring. JSON-file writes may not be safe under heavy simultaneous traffic.

The following require additional implementation/configuration and are **not fully working in this starter**: Google OAuth sign-in, public push notifications, real live streaming, live chat at scale, multi-resolution transcoding/adaptive bitrate, automatic speech recognition captions, licensed music catalogue, recommendation ranking comparable to YouTube, monetization, copyright detection, and production-grade analytics. The interface cannot create a public internet URL by itself; deploy it to a hosting provider for that.

Only upload media you own or have permission to distribute.


## Hosting
See `HOSTING_GUIDE_BN.md`. Render Blueprint configuration is included in `render.yaml`; persistent disk may incur hosting charges. A public URL is not created until you deploy it from your own hosting account.
