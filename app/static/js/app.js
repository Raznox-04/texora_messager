(() => {
    let ws = null;
    let currentConversationId = null;
    let currentConversation = null;
    let conversations = [];
    let currentTab = "chats";
    let reconnectAttempts = 0;
    let typingTimeout = null;

    const $ = (sel) => document.querySelector(sel);

    if (!API.getToken()) {
        window.location.href = "/login";
        return;
    }

    const me = API.getUser();
    if (me) {
        $("#my-name").textContent = me.display_name || me.username;
        $("#my-avatar").textContent = UI.avatarText(me.display_name || me.username);
        if ($("#settings-display-name")) $("#settings-display-name").value = me.display_name || "";
        if ($("#settings-bio")) $("#settings-bio").value = me.bio || "";
        if ($("#settings-online")) $("#settings-online").checked = me.show_online_status !== false;
        if ($("#settings-lastseen")) $("#settings-lastseen").checked = me.show_last_seen !== false;

        if ((me.role === "super_admin" || me.role === "moderator") && $("#btn-admin-panel")) {
            $("#btn-admin-panel").style.display = "inline-flex";
        }
    }

    function connectWS() {
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const token = API.getToken();
        if (!token) return;

        ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`);

        ws.onopen = () => {
            reconnectAttempts = 0;
            const statusEl = $("#connection-status");
            if (statusEl) {
                statusEl.textContent = "آنلاین";
                statusEl.classList.add("online");
            }
        };

        ws.onclose = () => {
            const statusEl = $("#connection-status");
            if (statusEl) {
                statusEl.textContent = "قطع اتصال — تلاش مجدد...";
                statusEl.classList.remove("online");
            }
            if (reconnectAttempts < 10) {
                reconnectAttempts++;
                // ✅ اصلاح باگ سینتکسی: اضافه شدن علامت ضرب (*) و حذف خط تیره اضافی
                setTimeout(connectWS, Math.min(1000 * reconnectAttempts, 10000));
            }
        };

        ws.onmessage = (event) => {
            try { handleWSEvent(JSON.parse(event.data)); }
            catch (e) { console.error("WS parse error", e); }
        };
    }

    function handleWSEvent(data) {
        switch (data.type) {
            case "message:new":
                if (data.message.conversation_id === currentConversationId) {
                    // بررسی جلوگیری از نمایش تکراری پیام در صورت وجود
                    const exists = document.querySelector(`[data-message-id="${data.message.id}"]`);
                    if (!exists) {
                        appendMessage(data.message);
                        scrollToBottom();
                    }
                }
                refreshConversations();
                break;
            case "typing":
                if (data.conversation_id === currentConversationId && data.user_id !== me?.id) {
                    showTyping();
                }
                break;
            case "presence":
                updatePresence(data.user_id, data.is_online);
                break;
            case "moderation_report":
                UI.toast(`گزارش نظارتی جدید: ${data.category}`, "error");
                break;
            case "error":
                UI.toast(data.message || "خطا در ارتباط بلادرنگ", "error");
                break;
        }
    }

    function scrollToBottom() {
        const box = $("#messages");
        if (box) {
            box.scrollTop = box.scrollHeight;
        }
    }

    function showTyping() {
        const el = $("#typing-indicator");
        if (!el) return;
        el.hidden = false;
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => { el.hidden = true; }, 3000);
    }

    function updatePresence(userId, isOnline) {
        const items = document.querySelectorAll(`[data-user-id="${userId}"]`);
        items.forEach((el) => {
            const sub = el.querySelector(".list-item-subtitle");
            if (sub) sub.textContent = isOnline ? "آنلاین" : "آفلاین";
        });
    }

    // تابع کمکی برای استخراج نام گفت‌وگوی خصوصی
    function getChatDisplayTitle(c) {
        if (c.title) return c.title;
        if (c.name) return c.name;
        if (c.other_user) return c.other_user.display_name || c.other_user.username;
        if (Array.isArray(c.participants)) {
            const other = c.participants.find((u) => u.id !== me?.id);
            if (other) return other.display_name || other.username;
        }
        return `گفت‌وگوی خصوصی #${c.id}`;
    }

    async function refreshConversations() {
        try {
            const [chats, groups] = await Promise.all([
                API.get("/api/chats"),
                API.get("/api/groups"),
            ]);
            conversations = [
                ...chats.map((c) => ({ ...c, kind: "chat" })),
                ...groups.map((g) => ({ ...g, kind: "group" })),
            ];
            renderSidebar();
        } catch (e) { console.error(e); }
    }

    async function renderSidebar() {
        const list = $("#sidebar-list");
        const q = ($("#search-input")?.value || "").trim().toLowerCase();

        const btnNewGroup = $("#btn-new-group");
        if (btnNewGroup) {
            btnNewGroup.style.display = currentTab === "groups" ? "inline-flex" : "none";
        }

        if (currentTab === "chats") {
            const items = conversations.filter((c) => {
                if (c.kind !== "chat") return false;
                if (!q) return true;
                return getChatDisplayTitle(c).toLowerCase().includes(q);
            });
            if (!items.length) { list.innerHTML = '<div class="empty-state"><p>گفت‌وگویی نیست</p></div>'; return; }

            list.innerHTML = items.map((c) => {
                const title = getChatDisplayTitle(c);
                const isActive = c.id === currentConversationId ? "active" : "";
                return `
                <div class="list-item ${isActive}" data-conv-id="${c.id}" data-kind="chat">
                    <span class="avatar">${UI.avatarText(title)}</span>
                    <div class="list-item-content">
                        <div class="list-item-title">${UI.escapeHtml(title)}</div>
                        <div class="list-item-subtitle">${c.last_message ? UI.escapeHtml(c.last_message) : UI.formatDate(c.created_at)}</div>
                    </div>
                </div>
            `}).join("");
        } else if (currentTab === "groups") {
            const items = conversations.filter((c) => {
                if (c.kind !== "group") return false;
                if (!q) return true;
                return (c.name || "").toLowerCase().includes(q);
            });
            if (!items.length) { list.innerHTML = '<div class="empty-state"><p>گروهی نیست</p></div>'; return; }

            list.innerHTML = items.map((g) => {
                const isActive = (g.conversation_id || g.id) === currentConversationId ? "active" : "";
                return `
                <div class="list-item ${isActive}" data-conv-id="${g.conversation_id || g.id}" data-group-id="${g.id}" data-kind="group">
                    <span class="avatar">${UI.avatarText(g.name)}</span>
                    <div class="list-item-content">
                        <div class="list-item-title">${UI.escapeHtml(g.name)}</div>
                        <div class="list-item-subtitle">${UI.escapeHtml(g.description || "")}</div>
                    </div>
                </div>
            `}).join("");
        } else if (currentTab === "users") {
            try {
                const users = await API.get(`/api/users?q=${encodeURIComponent(q)}`);
                list.innerHTML = users.filter((u) => u.id !== me?.id).map((u) => `
                    <div class="list-item" data-user-id="${u.id}" data-start-chat="${u.id}">
                        <span class="avatar">${UI.avatarText(u.display_name || u.username)}</span>
                        <div class="list-item-content">
                            <div class="list-item-title">${UI.escapeHtml(u.display_name || u.username)}</div>
                            <div class="list-item-subtitle">${u.is_online ? "آنلاین" : "آفلاین"}</div>
                        </div>
                    </div>
                `).join("");
            } catch (e) { console.error(e); }
        }

        list.querySelectorAll(".list-item").forEach((el) => {
            el.addEventListener("click", async () => {
                const convId = el.dataset.convId;
                const startChat = el.dataset.startChat;
                if (startChat) await startPrivateChat(parseInt(startChat));
                else if (convId) openConversation(parseInt(convId), el.dataset.kind);
            });
        });
    }

    async function startPrivateChat(userId) {
        try {
            const conv = await API.post("/api/chats", { participant_id: userId });
            await refreshConversations();
            openConversation(conv.id, "chat");
        } catch (e) { UI.toast(e.message, "error"); }
    }

    async function openConversation(convId, kind) {
        currentConversationId = convId;
        $("#empty-state").hidden = true;
        $("#chat-view").hidden = false;

        // در حالت موبایل، با باز شدن چت سایدبار مخفی شود
        if (window.innerWidth <= 768) {
            $(".sidebar")?.classList.add("hidden");
        }

        const conv = conversations.find((c) => (c.conversation_id === convId || c.id === convId) && c.kind === kind);
        currentConversation = conv;

        if (kind === "group" && conv) {
            $("#chat-title").textContent = conv.name;
            $("#chat-avatar").textContent = UI.avatarText(conv.name);
            $("#chat-subtitle").textContent = conv.is_public ? "گروه عمومی" : "گروه خصوصی";
        } else if (conv) {
            const title = getChatDisplayTitle(conv);
            $("#chat-title").textContent = title;
            $("#chat-avatar").textContent = UI.avatarText(title);
            $("#chat-subtitle").textContent = "گفت‌وگوی خصوصی";
        } else {
            $("#chat-title").textContent = `گفت‌وگو #${convId}`;
            $("#chat-avatar").textContent = "گ";
            $("#chat-subtitle").textContent = "";
        }

        renderSidebar(); // بروزرسانی کلاس active در لیست
        await loadMessages();
    }

    async function loadMessages() {
        const box = $("#messages");
        box.innerHTML = '<div class="empty-state"><p>در حال بارگذاری...</p></div>';
        try {
            const msgs = await API.get(`/api/messages/conversation/${currentConversationId}?limit=50`);
            box.innerHTML = "";
            msgs.forEach(appendMessage);
            scrollToBottom();
        } catch (e) {
            box.innerHTML = `<div class="empty-state"><p>${UI.escapeHtml(e.message)}</p></div>`;
        }
    }

    function appendMessage(m) {
        const box = $("#messages");
        const isMine = m.sender_id === me?.id;
        const div = document.createElement("div");
        div.className = `message ${isMine ? "mine" : "theirs"}`;
        div.dataset.messageId = m.id;
        let inner = "";

        if (!isMine && m.sender_name) {
            inner += `<div class="message-sender">${UI.escapeHtml(m.sender_name)}</div>`;
        }

        if (m.attachments && m.attachments.length) {
            for (const a of m.attachments) {
                if (a.is_image) {
                    inner += `<div class="message-image"><img src="${a.file_path}" alt="${UI.escapeHtml(a.file_name)}" loading="lazy"></div>`;
                } else {
                    inner += `<div class="message-file">📄 <a href="${a.file_path}" target="_blank" rel="noopener">${UI.escapeHtml(a.file_name)}</a> <span>(${Math.round(a.file_size/1024)}KB)</span></div>`;
                }
            }
        }
        if (m.content) inner += `<div class="message-content">${UI.escapeHtml(m.content)}</div>`;
        if (m.reactions && m.reactions.length) {
            const grouped = {};
            m.reactions.forEach((r) => { grouped[r.emoji] = (grouped[r.emoji] || 0) + 1; });
            inner += `<div class="message-reactions">${Object.entries(grouped).map(([e, n]) => `<span class="reaction">${e}${n}</span>`).join("")}</div>`;
        }
        inner += `<div class="message-time">${UI.formatTime(m.created_at)}${m.is_edited ? " (ویرایش)" : ""}</div>`;
        div.innerHTML = inner;
        box.appendChild(div);
    }

    $("#message-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const input = $("#message-input");
        const content = input.value.trim();
        if (!content || !currentConversationId) return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: "message:send",
                conversation_id: currentConversationId,
                content,
            }));
            input.value = "";
            input.style.height = "auto";
        } else {
            try {
                const msg = await API.post("/api/messages", {
                    conversation_id: currentConversationId,
                    content,
                });
                appendMessage(msg);
                input.value = "";
                input.style.height = "auto";
                scrollToBottom();
            } catch (err) { UI.toast(err.message, "error"); }
        }
    });

    $("#message-input")?.addEventListener("input", (e) => {
        e.target.style.height = "auto";
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
        if (ws && ws.readyState === WebSocket.OPEN && currentConversationId) {
            ws.send(JSON.stringify({ type: "typing", conversation_id: currentConversationId }));
        }
    });

    $("#message-input")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            $("#message-form").requestSubmit();
        }
    });

    $("#btn-attach")?.addEventListener("click", () => $("#file-input").click());
    $("#file-input")?.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file || !currentConversationId) return;
        const fd = new FormData();
        fd.append("conversation_id", currentConversationId);
        fd.append("file", file);
        try {
            const msg = await API.request("/api/uploads/message", { method: "POST", body: fd });
            appendMessage(msg);
            scrollToBottom();
        } catch (err) { UI.toast(err.message, "error"); }
        e.target.value = "";
    });

    document.querySelectorAll(".sidebar-tabs .tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".sidebar-tabs .tab").forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            currentTab = tab.dataset.tab;
            renderSidebar();
        });
    });

    $("#search-input")?.addEventListener("input", () => {
        clearTimeout(window.__searchTimeout);
        window.__searchTimeout = setTimeout(renderSidebar, 300);
    });

    // مدیریت مودال‌ها
    $("#btn-new-chat")?.addEventListener("click", () => UI.openModal("modal-new-chat"));
    $("#btn-new-group")?.addEventListener("click", () => UI.openModal("modal-new-group"));
    $("#btn-settings")?.addEventListener("click", () => UI.openModal("modal-settings"));

    document.querySelectorAll("[data-close-modal]").forEach((b) => {
        b.addEventListener("click", (e) => {
            e.preventDefault();
            const modal = e.target.closest(".modal");
            if (modal) modal.classList.remove("active");
        });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("active");
        });
    });

    // جستجوی کاربر برای چت جدید
    $("#new-chat-search")?.addEventListener("input", async (e) => {
        const q = e.target.value.trim();
        const results = $("#new-chat-results");
        if (q.length < 2) { results.innerHTML = ""; return; }
        try {
            const users = await API.get(`/api/users?q=${encodeURIComponent(q)}`);
            results.innerHTML = users.filter((u) => u.id !== me?.id).map((u) => `
                <div class="list-item" data-uid="${u.id}">
                    <span class="avatar">${UI.avatarText(u.display_name || u.username)}</span>
                    <div class="list-item-content">
                        <div class="list-item-title">${UI.escapeHtml(u.display_name || u.username)}</div>
                        <div class="list-item-subtitle">@${UI.escapeHtml(u.username)}</div>
                    </div>
                </div>
            `).join("");
            results.querySelectorAll(".list-item").forEach((el) => {
                el.addEventListener("click", async () => {
                    await startPrivateChat(parseInt(el.dataset.uid));
                    UI.closeModal("modal-new-chat");
                });
            });
        } catch (e) { console.error(e); }
    });

    // ساخت گروه
    $("#btn-create-group")?.addEventListener("click", async () => {
        const name = $("#group-name").value.trim();
        if (!name) {
            UI.toast("نام گروه را وارد کنید", "error");
            return;
        }
        try {
            const group = await API.post("/api/groups", {
                name: name,
                description: $("#group-desc").value.trim(),
                is_public: $("#group-public").checked,
                member_ids: []
            });
            UI.toast("گروه با موفقیت ساخته شد", "success");
            UI.closeModal("modal-new-group");
            $("#group-name").value = "";
            $("#group-desc").value = "";

            await refreshConversations();
            openConversation(group.conversation_id || group.id, "group");
        } catch (e) { UI.toast(e.message, "error"); }
    });

    $("#btn-save-settings")?.addEventListener("click", async () => {
        try {
            const updated = await API.patch("/api/users/me", {
                display_name: $("#settings-display-name").value.trim(),
                bio: $("#settings-bio").value.trim(),
            });
            await API.patch("/api/users/me/privacy", {
                show_online_status: $("#settings-online").checked,
                show_last_seen: $("#settings-lastseen").checked,
            });
            API.setUser(updated);
            $("#my-name").textContent = updated.display_name || updated.username;
            $("#my-avatar").textContent = UI.avatarText(updated.display_name || updated.username);
            UI.toast("تنظیمات ذخیره شد", "success");
            UI.closeModal("modal-settings");
        } catch (e) { UI.toast(e.message, "error"); }
    });

    $("#btn-logout")?.addEventListener("click", async () => {
        try { await API.post("/api/auth/logout", {}); } catch {}
        API.clearTokens();
        window.location.href = "/login";
    });

    $("#btn-back")?.addEventListener("click", () => {
        $("#chat-view").hidden = true;
        $("#empty-state").hidden = false;
        currentConversationId = null;
        $(".sidebar")?.classList.remove("hidden");
    });

    connectWS();
    refreshConversations();
    setInterval(refreshConversations, 30000);
})();