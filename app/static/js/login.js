document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("login-error");
    errEl.hidden = true;
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "در حال ورود...";

    try {
        const data = await API.post("/api/auth/login", {
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
        });
        API.setTokens(data.access_token, data.refresh_token);
        API.setUser(data.user);
        window.location.href = "/";
    } catch (err) {
        errEl.textContent = err.message;
        errEl.hidden = false;
    } finally {
        btn.disabled = false;
        btn.textContent = "ورود";
    }
});