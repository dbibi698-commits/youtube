# Murshid Developer Hosting Guide (বাংলা)

## আগে গুরুত্বপূর্ণ কথা
এই ZIP-এ Render-এর deploy configuration যোগ করা আছে। আমি তোমার Render/GitHub অ্যাকাউন্টে লগইন করতে বা তোমার হয়ে বাইরে সার্ভারে deploy করতে পারি না। তাই এখনই কোনো Public URL তৈরি হয়েছে—এমন দাবি করছি না। তুমি নিজের অ্যাকাউন্টে নিচের ধাপগুলো করলে URL পাবে।

## Render-এ Deploy (PC অথবা Android Chrome Desktop mode)
1. ZIP extract করো।
2. পুরো `murshid_developer` project GitHub repository-তে upload করো।
3. Render-এ account খুলে **New + → Blueprint** নির্বাচন করো এবং ওই GitHub repository connect করো।
4. Render `render.yaml` পড়বে। Blueprint তৈরি করে deploy করো।
5. Render build ও deploy শেষ করলে Dashboard-এ দেওয়া `https://...onrender.com` URL খোলো।
6. URL-এর শেষে `/api/health` খুলে `ok: true` দেখো।
7. Website-এ `dbibi698@gmail.com` দিয়ে Register করো—এই ইমেল Admin হবে। আগে থেকে অন্যভাবে account তৈরি হয়ে থাকলে Admin status-এর জন্য deployment environment ও JSON data পরীক্ষা করতে হবে।

## Persistent storage
`render.yaml`-এ `/var/data` persistent disk চাওয়া হয়েছে। Persistent disk-এর জন্য hosting plan-এ অতিরিক্ত খরচ হতে পারে। Disk ছাড়া ephemeral hosting-এ restart/redeploy হলে local JSON database ও uploaded files হারিয়ে যেতে পারে। Disk mount path environment variables দিয়ে configure করা আছে।

## Android Termux-এ local run
```bash
pkg update
pkg install python
pip install -r requirements.txt
python app.py
```
Chrome-এ `http://127.0.0.1:5000` খোলো। এটি শুধু তোমার ডিভাইসে local; public internet URL নয়.

## Security / production limitations
- `SECRET_KEY`-কে production environment variable হিসেবে secret রাখো.
- Admin account-এ strong password use করো.
- This is a prototype: JSON file storage is not safe for high concurrent traffic.
- Google OAuth, genuine live streaming, public push notifications, adaptive transcoding and automatic captions are not implemented as complete production services.
- Public-scale service needs a proper database, object storage/CDN, video transcoding, rate limits, CSRF/security review, backups, and moderation tooling.
- Upload size limit is currently 1 GB in app configuration; host proxy/plan limits may be lower.
