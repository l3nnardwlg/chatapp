(function () {
    const { username, groups, friends } = window.CHAT_CONFIG;
    const socket = io({ transports: ["websocket"] });

    const groupList = document.getElementById("group-list");
    const friendList = document.getElementById("friend-list");
    const messagesView = document.getElementById("messages");
    const composer = document.getElementById("composer");
    const messageInput = document.getElementById("message-input");
    const presence = document.getElementById("presence");
    const channelTitle = document.getElementById("channel-title");
    const inviteBtn = document.getElementById("invite-btn");
    const inviteName = document.getElementById("invite-name");

    const onlineUsers = new Set();

    const channelState = {
        active: "lobby",
        history: {},
    };

    function setActiveChannel(channelId, label) {
        channelState.active = channelId;
        channelTitle.textContent = label;
        Array.from(document.querySelectorAll(".sidebar li"))
            .forEach((item) => item.classList.toggle("active", item.dataset.channel === channelId));
        loadHistory(channelId);
        if (!channelState.history[channelId]) {
            fetch(`/api/messages/${encodeURIComponent(channelId)}`)
                .then((res) => res.json())
                .then((payload) => {
                    (payload.messages || []).forEach((msg) => appendMessage(msg));
                });
        }
        updatePresence(channelId);
    }

    function addListItem(list, label, channelId, badge = "") {
        const li = document.createElement("li");
        li.dataset.channel = channelId;
        li.innerHTML = `<span>${label}</span>${badge}`;
        li.addEventListener("click", () => setActiveChannel(channelId, label));
        list.appendChild(li);
    }

    function updatePresence(channelId) {
        if (channelId in GROUP_LOOKUP) {
            presence.textContent = GROUP_LOOKUP[channelId].description;
        } else if (channelId !== username) {
            const dot = document.querySelector(`.status[data-username="${channelId}"]`);
            const online = dot && dot.classList.contains("online");
            presence.textContent = online ? `${channelId} is online` : `${channelId} is offline`;
        } else {
            presence.textContent = "";
        }
    }

    function appendMessage({ channel, from, message, timestamp }) {
        if (!channelState.history[channel]) {
            channelState.history[channel] = [];
        }
        channelState.history[channel].push({ from, message, timestamp });

        if (channel !== channelState.active) {
            badgeUnread(channel);
            return;
        }

        renderBubble({ from, message, timestamp });
    }

    function renderBubble({ from, message, timestamp }) {
        const bubble = document.createElement("div");
        bubble.classList.add("message");
        if (from === username) bubble.classList.add("me");

        const meta = document.createElement("div");
        meta.classList.add("message__meta");
        const time = new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        meta.innerHTML = `<span>${from}</span><span>${time}</span>`;

        const body = document.createElement("div");
        body.textContent = message;

        bubble.appendChild(meta);
        bubble.appendChild(body);
        messagesView.appendChild(bubble);
        messagesView.scrollTop = messagesView.scrollHeight;
    }

    function loadHistory(channel) {
        messagesView.innerHTML = "";
        const history = channelState.history[channel] || [];
        history.forEach((payload) => renderBubble(payload));
        clearBadge(channel);
    }

    function badgeUnread(channel) {
        const item = document.querySelector(`.sidebar li[data-channel="${channel}"]`);
        if (!item || item.classList.contains("active")) return;
        if (!item.querySelector(".badge")) {
            const badge = document.createElement("span");
            badge.classList.add("badge");
            badge.textContent = "●";
            item.appendChild(badge);
        }
    }

    function clearBadge(channel) {
        const item = document.querySelector(`.sidebar li[data-channel="${channel}"] .badge`);
        if (item) item.remove();
    }

    function renderFriendList() {
        friendList.innerHTML = "";
        friends.sort().forEach((friend) => {
            const statusDot = document.createElement("span");
            statusDot.classList.add("status");
            statusDot.dataset.username = friend;
            addListItem(friendList, friend, friend, statusDot.outerHTML);
        });
        applyStatuses();
    }

    function renderGroupList() {
        groupList.innerHTML = "";
        groups.forEach((group) => {
            addListItem(groupList, group.name, group.id);
            socket.emit("join_group", { group: group.id });
        });
    }

    const GROUP_LOOKUP = Object.fromEntries(groups.map((group) => [group.id, group]));

    renderGroupList();
    renderFriendList();
    setActiveChannel("lobby", "Lobby");

    fetch(`/api/messages/${encodeURIComponent(channelState.active)}`)
        .then((res) => res.json())
        .then((payload) => {
            (payload.messages || []).forEach((msg) => appendMessage(msg));
        });

    composer.addEventListener("submit", (event) => {
        event.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;
        socket.emit("send_message", { channel: channelState.active, message });
        messageInput.value = "";
        messageInput.focus();
    });

    inviteBtn.addEventListener("click", () => {
        const invitee = inviteName.value.trim();
        if (!invitee) return;
        socket.emit("private_invite", { to: invitee });
        inviteName.value = "";
    });

    socket.on("message", (payload) => {
        appendMessage(payload);
    });

    socket.on("system", (payload) => {
        appendMessage({ ...payload, from: "system" });
    });

    socket.on("user_status", ({ username: user, status }) => {
        const dot = document.querySelector(`.status[data-username="${user}"]`);
        if (status === "online") {
            onlineUsers.add(user);
        } else {
            onlineUsers.delete(user);
        }
        if (!dot) return;
        if (status === "online") {
            dot.classList.add("online");
        } else {
            dot.classList.remove("online");
        }
    });

    socket.on("friend_update", ({ friend }) => {
        if (!friends.includes(friend)) {
            friends.push(friend);
            renderFriendList();
        }
    });

    socket.on("error", ({ message }) => {
        presence.textContent = message;
        presence.style.color = "var(--danger)";
        setTimeout(() => {
            presence.textContent = "";
            presence.style.color = "var(--muted)";
        }, 3000);
    });

    window.addEventListener("focus", () => clearBadge(channelState.active));

    function applyStatuses() {
        onlineUsers.forEach((user) => {
            const dot = document.querySelector(`.status[data-username="${user}"]`);
            if (dot) {
                dot.classList.add("online");
            }
        });
    }
})();
