import os
from collections import defaultdict
from datetime import datetime
from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = os.environ.get("CHATAPP_SECRET", "super-secret-key")

socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory stores for demo purposes
ACTIVE_USERS = set()
FRIENDS = defaultdict(set)
GROUPS = {
    "lobby": {"name": "Lobby", "description": "Chat with everyone in the app"},
    "gamers": {"name": "Gamers", "description": "Find teammates and discuss games"},
    "devs": {"name": "Devs", "description": "Share code, tips, and resources"},
}
MESSAGES = defaultdict(list)


def _dm_key(user_a: str, user_b: str) -> str:
    """Return a consistent key for a direct message thread."""
    return f"dm:{':'.join(sorted([user_a, user_b]))}"


@app.route("/")
def index():
    username = session.get("username")
    return render_template("index.html", username=username)


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    if not username:
        flash("Please choose a username to join the chat.")
        return redirect(url_for("index"))

    if username in ACTIVE_USERS:
        flash("That username is already in use. Pick a different one.")
        return redirect(url_for("index"))

    session["username"] = username
    ACTIVE_USERS.add(username)
    _ensure_sample_social_graph(username)
    return redirect(url_for("chat"))


@app.get("/chat")
def chat():
    username = session.get("username")
    if not username:
        flash("Sign in with a username to access the chat.")
        return redirect(url_for("index"))

    groups = [{"id": group_id, **group_meta} for group_id, group_meta in GROUPS.items()]
    friends = sorted(FRIENDS.get(username, []))

    return render_template(
        "chat.html",
        username=username,
        groups=groups,
        friends=friends,
    )


@app.post("/logout")
def logout():
    username = session.pop("username", None)
    if username and username in ACTIVE_USERS:
        ACTIVE_USERS.remove(username)
        socketio.emit("user_status", {"username": username, "status": "offline"}, broadcast=True)
    return redirect(url_for("index"))


@app.get("/api/messages/<channel>")
def get_messages(channel: str):
    username = session.get("username")
    if not username:
        return jsonify({"error": "unauthorized"}), 401

    if channel in GROUPS:
        return jsonify({"messages": MESSAGES[channel][-100:]})

    friends = FRIENDS.get(username, set())
    if channel == username or channel not in friends:
        return jsonify({"error": "unknown channel"}), 404

    storage_key = _dm_key(username, channel)
    history = [
        {"channel": channel, **entry}
        for entry in MESSAGES[storage_key][-100:]
    ]
    return jsonify({"messages": history})


@socketio.on("connect")
def handle_connect():
    username = session.get("username")
    if not username:
        return False

    join_room(username)
    emit("user_status", {"username": username, "status": "online"}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    username = session.get("username")
    if not username:
        return

    if username in ACTIVE_USERS:
        ACTIVE_USERS.remove(username)
        emit("user_status", {"username": username, "status": "offline"}, broadcast=True)


@socketio.on("join_group")
def handle_join_group(data):
    group_id = data.get("group")
    if group_id not in GROUPS:
        emit("error", {"message": "Group not found."})
        return

    join_room(group_id)
    username = session["username"]
    timestamp = datetime.utcnow().isoformat()
    system_message = {
        "channel": group_id,
        "from": "system",
        "message": f"{username} joined {GROUPS[group_id]['name']}",
        "timestamp": timestamp,
    }
    MESSAGES[group_id].append(system_message)
    emit("system", system_message, room=group_id)


@socketio.on("leave_group")
def handle_leave_group(data):
    group_id = data.get("group")
    if group_id not in GROUPS:
        emit("error", {"message": "Group not found."})
        return

    leave_room(group_id)
    username = session["username"]
    timestamp = datetime.utcnow().isoformat()
    system_message = {
        "channel": group_id,
        "from": "system",
        "message": f"{username} left {GROUPS[group_id]['name']}",
        "timestamp": timestamp,
    }
    MESSAGES[group_id].append(system_message)
    emit("system", system_message, room=group_id)


@socketio.on("private_invite")
def handle_private_invite(data):
    target = data.get("to")
    username = session.get("username")

    if not target or target == username or target not in ACTIVE_USERS:
        emit("error", {"message": "User is not available."})
        return

    FRIENDS[username].add(target)
    FRIENDS[target].add(username)

    emit("friend_update", {"friend": target}, room=username)
    emit("friend_update", {"friend": username}, room=target)


@socketio.on("send_message")
def handle_message(data):
    username = session.get("username")
    channel = data.get("channel")
    content = data.get("message", "").strip()

    if not username or not channel or not content:
        return

    timestamp = datetime.utcnow().isoformat()

    if channel in GROUPS:
        join_room(channel)
        payload = {
            "channel": channel,
            "from": username,
            "message": content,
            "timestamp": timestamp,
        }
        MESSAGES[channel].append(payload)
        emit("message", payload, room=channel)
        return

    friends = FRIENDS.get(username, set())
    if channel == username or channel not in friends:
        emit("error", {"message": "You are not connected with this user."})
        return

    storage_key = _dm_key(username, channel)
    entry = {
        "from": username,
        "message": content,
        "timestamp": timestamp,
    }
    MESSAGES[storage_key].append(entry)

    sender_payload = {"channel": channel, **entry}
    recipient_payload = {"channel": username, **entry}

    emit("message", sender_payload, room=username)
    emit("message", recipient_payload, room=channel)


def _ensure_sample_social_graph(username: str) -> None:
    """Populate baseline friends and groups for a newcomer."""
    # Give newcomers some suggested friends
    starter_friends = {"alexa", "blake", "casey"}
    for friend in starter_friends:
        if friend != username:
            FRIENDS[username].add(friend)
            FRIENDS[friend].add(username)

    # Seed a welcome message in the lobby for new users
    welcome = {
        "channel": "lobby",
        "from": "system",
        "message": f"Welcome {username}! Say hi to everyone in the Lobby.",
        "timestamp": datetime.utcnow().isoformat(),
    }
    MESSAGES["lobby"].append(welcome)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
