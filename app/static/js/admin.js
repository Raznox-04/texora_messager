(() => {
    const $ = (s) => document.querySelector(s);
    const content = $("#admin-content");

    if (!API.getToken()) {
        window.location.href = "/login";
        return;
    }

    // ✅ اصلاح بستن مودال‌ها در پنل ادمین (در صورت وجود)
    document.querySelectorAll("[data-close-modal]").forEach((b) => {
        b.addEventListener("click", (e) => {
            e.preventDefault();
            const modal = e.target.closest(".modal");
            if (modal) modal.classList.remove("active");
        });
    });

    async function loadStats() {
        try {
            const s = await API.get("/api/admin/stats");
            content.innerHTML = `
                <h2 style="margin-bottom:20px;">📊 آمار کلی</h2>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;">
                    <div class="auth-card" style="text-align:center;">
                        <div style="font-size:32px;font-weight:700;color:var(--primary);">${s.users}</div>
                        <div>کاربران</div>
                    </div>
                    <div class="auth-card" style="text-align:center;">
                        <div style="font-size:32px;font-weight:700;color:var(--primary);">${s.messages}</div>
                        <div>پیام‌ها</div>
                    </div>
                    <div class="auth-card" style="text-align:center;">
                        <div style="font-size:32px;font-weight:700;color:var(--primary);">${s.groups}</div>
                        <div>گروه‌ها</div>
                    </div>
                    <div class="auth-card" style="text-align:center;">
                        <div style="font-size:32px;font-weight:700;color:var(--danger);">${s.pending_reports}</div>
                        <div>گزارش‌های در انتظار</div>
                    </div>
                </div>
            `;
        } catch (e) {
            content.innerHTML = `<p style="color:var(--danger)">خطا در دریافت آمار: ${UI.escapeHtml(e.message)}</p>`;
        }
    }

    async function loadReports() {
        try {
            const reports = await API.get("/api/moderation/reports?status_filter=pending");
            if (!reports.length) {
                content.innerHTML = "<h2>گزارش‌های نظارتی</h2><p>گزارش در انتظاری وجود ندارد.</p>";
                return;
            }
            content.innerHTML = `
                <h2 style="margin-bottom:20px;">🚨 گزارش‌های نظارتی</h2>
                <div style="display:flex;flex-direction:column;gap:12px;">
                    ${reports.map((r) => `
                        <div class="auth-card" style="padding:16px;">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                                <strong>پیام #${r.message_id} — کاربر #${r.user_id}</strong>
                                <span style="color:var(--danger);">${r.result} / ${r.severity}</span>
                            </div>
                            <p style="color:var(--text-muted);font-size:14px;margin-bottom:8px;">${r.explanation || ""}</p>
                            <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">
                                دسته: ${r.category || "-"} | اقدام پیشنهادی: ${r.suggested_action || "-"} | اطمینان: ${r.confidence ?? "-"}
                            </div>
                            <div style="display:flex;gap:8px;">
                                <button class="btn btn-primary" data-decide="warned" data-report="${r.id}">اخطار</button>
                                <button class="btn btn-secondary" data-decide="approved" data-report="${r.id}">تأیید</button>
                                <button class="btn btn-secondary" data-decide="rejected" data-report="${r.id}">رد</button>
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;
            content.querySelectorAll("[data-decide]").forEach((b) => {
                b.addEventListener("click", async () => {
                    try {
                        await API.post(`/api/moderation/reports/${b.dataset.report}/decision?decision=${b.dataset.decide}&reason=`, {});
                        UI.toast("تصمیم ثبت شد", "success");
                        loadReports();
                    } catch (e) { UI.toast(e.message, "error"); }
                });
            });
        } catch (e) {
            content.innerHTML = `<p style="color:var(--danger)">خطا در دریافت گزارش‌ها: ${UI.escapeHtml(e.message)}</p>`;
        }
    }

    async function loadUsers() {
        try {
            const users = await API.get("/api/admin/users");
            content.innerHTML = `
                <h2 style="margin-bottom:20px;">👥 کاربران</h2>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    ${users.map((u) => `
                        <div class="auth-card" style="padding:12px;display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <strong>${UI.escapeHtml(u.display_name)}</strong> (@${UI.escapeHtml(u.username)})
                                <div style="font-size:12px;color:var(--text-muted);">${u.email} | نقش: ${u.role} | ${u.is_blocked ? "مسدود" : "فعال"}</div>
                            </div>
                            <div>
                                ${u.is_blocked
                                    ? `<button class="btn btn-secondary" data-unblock="${u.id}">رفع مسدودی</button>`
                                    : `<button class="btn btn-secondary" data-block="${u.id}">مسدودسازی</button>`}
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;
            content.querySelectorAll("[data-block]").forEach((b) => {
                b.addEventListener("click", async () => {
                    try {
                        await API.post(`/api/admin/users/${b.dataset.block}/block?reason=`, {});
                        UI.toast("کاربر مسدود شد", "success");
                        loadUsers();
                    } catch (e) { UI.toast(e.message, "error"); }
                });
            });
            content.querySelectorAll("[data-unblock]").forEach((b) => {
                b.addEventListener("click", async () => {
                    try {
                        await API.post(`/api/admin/users/${b.dataset.unblock}/unblock`, {});
                        UI.toast("رفع مسدودی شد", "success");
                        loadUsers();
                    } catch (e) { UI.toast(e.message, "error"); }
                });
            });
        } catch (e) {
            content.innerHTML = `<p style="color:var(--danger)">خطا در دریافت کاربران: ${UI.escapeHtml(e.message)}</p>`;
        }
    }

    document.querySelectorAll("[data-section]").forEach((el) => {
        el.addEventListener("click", () => {
            const s = el.dataset.section;
            if (s === "stats") loadStats();
            else if (s === "reports") loadReports();
            else if (s === "users") loadUsers();
        });
    });

    // لود اولیه آمار
    loadStats();
})();