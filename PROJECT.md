# Project map

- `app.py` — Flask server, account authentication, JSON-file persistence, uploads, comments/reactions/subscriptions, notifications, admin controls.
- `static/index.html` — main application shell.
- `static/style.css` — responsive dark UI.
- `static/app.js` — front-end pages and actions.
- `requirements.txt` — Python dependencies.
- `data/store.json` — created automatically at first use; local app data.
- `uploads/` — uploaded media and thumbnails.

## Feature notes
- Short and long videos have separate filters and playback layout.
- Private videos are visible only to their owner.
- Channel page displays subscriber count and total channel views.
- Admin-only routes check the configured admin email and admin flag.
- Notifications are stored and polled while the app is open.
- Video quality selector does not create new encodings; it can only play the uploaded source.
