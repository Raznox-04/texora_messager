const API = (() => {
    const BASE = "";

    function getToken() { return localStorage.getItem("texora_access_token"); }
    function getRefreshToken() { return localStorage.getItem("texora_refresh_token"); }
    function setTokens(access, refresh) {
        if (access) localStorage.setItem("texora_access_token", access);
        if (refresh) localStorage.setItem("texora_refresh_token", refresh);
    }
    function clearTokens() {
        localStorage.removeItem("texora_access_token");
        localStorage.removeItem("texora_refresh_token");
        localStorage.removeItem("texora_user");
    }
    function setUser(user) { localStorage.setItem("texora_user", JSON.stringify(user)); }
    function getUser() {
        try { return JSON.parse(localStorage.getItem("texora_user") || "null"); }
        catch { return null; }
    }

    async function request(path, options = {}, retry = true) {
        // کپی کردن options برای جلوگیری از تغییر شیء اصلی در زمان retry
        const fetchOptions = { ...options };
        const headers = { ...(options.headers || {}) };

        const token = getToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;

        if (fetchOptions.body && !(fetchOptions.body instanceof FormData) && typeof fetchOptions.body !== "string") {
            headers["Content-Type"] = "application/json";
            fetchOptions.body = JSON.stringify(fetchOptions.body);
        }
        fetchOptions.headers = headers;

        const res = await fetch(BASE + path, fetchOptions);

        if (res.status === 401 && retry) {
            const refresh = getRefreshToken();
            if (refresh) {
                try {
                    const r = await fetch("/api/auth/refresh", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ refresh_token: refresh }),
                    });
                    if (r.ok) {
                        const data = await r.json();
                        setTokens(data.access_token, data.refresh_token);
                        return request(path, options, false);
                    }
                } catch {}
            }
            clearTokens();
            window.location.href = "/login";
            throw new Error(" نشست کاربری منقضی شد، لطفاً دوباره وارد شوید");
        }

        if (!res.ok) {
            let detail = "خطای ناشناخته در ارتباط با سرور";
            try {
                const d = await res.json();
                detail = Array.isArray(d.detail) ? d.detail[0]?.msg || detail : (d.detail || detail);
            } catch {}
            throw new Error(detail);
        }

        const ct = res.headers.get("content-type") || "";
        if (ct.includes("application/json")) return res.json();
        return res.text();
    }

    return {
        getToken, setTokens, clearTokens, setUser, getUser, request,
        get: (p) => request(p),
        post: (p, body) => request(p, { method: "POST", body }),
        patch: (p, body) => request(p, { method: "PATCH", body }),
        del: (p) => request(p, { method: "DELETE" }),
    };
})();