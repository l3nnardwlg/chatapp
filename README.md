# ChatSphere

A drop-in real-time chat experience designed for lightweight self-hosting. Users join with only a username, then dive into groups, private chats, and curated friend suggestions—perfect for spinning up a social space on any Python-friendly server.

## Features

- 🌐 **Landing page starter kit** that introduces the app and lets people jump back into the chat if already signed in.
- 💬 **Real-time group rooms** (Lobby, Gamers, Devs) powered by Socket.IO with online presence hints.
- 👥 **Friend list & invites** so users can add others for one-on-one chats without additional auth.
- 📬 **Channel history API** that lazily loads the last 100 messages for each room or DM.
- 🎨 **Responsive UI** with a modern gradient theme built using pure HTML/CSS/JS—no build step required.

## Running locally or on a server

1. Install dependencies (preferably inside a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

2. Start the Socket.IO-enabled Flask server. It binds to `0.0.0.0` by default so it is reachable on the machine's IP without extra configuration.

   ```bash
   python app.py
   ```

3. Visit `http://<server-ip>:5000` in a browser. Pick a username to log in and begin chatting.

## Customization tips

- Update the predefined groups in `app.py` by editing the `GROUPS` dictionary.
- Seed your own welcome messages or onboarding flows inside the `_ensure_sample_social_graph` helper.
- Replace or extend the landing page visuals in `templates/index.html` and tweak the aesthetic in `static/css/style.css`.
- Add persistence by swapping the in-memory stores (`ACTIVE_USERS`, `FRIENDS`, `MESSAGES`) with your preferred database or cache.

## Project structure

```
.
├── app.py                 # Flask + Socket.IO server
├── requirements.txt       # Python dependencies
├── templates/             # Jinja2 templates for landing + chat views
├── static/css/style.css   # Global styling
└── static/js/chat.js      # Front-end chat logic
```

Enjoy running ChatSphere on your own terms! If you build cool extensions, we'd love to hear about them.
