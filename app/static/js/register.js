document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("register-error");
    errEl.hidden = true;
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "در حال ثبت‌نام...";

    try {
        await API.post("/api/auth/register", {
            username: document.getElementById("username").value.trim(),
            display_name: document.getElementById("display_name").value.trim(),
            email: document.getElementById("email").value.trim(),
            password: document.getElementById("password").value,
        });
        UI.toast("ثبت‌نام موفق. حالا وارد شوید.", "success");
        setTimeout(() => window.location.href = "/login", 800);
    } catch (err) {
        errEl.textContent = err.message;
        errEl.hidden = false;
    } finally {
        btn.disabled = false;
        btn.textContent = "ثبت‌نام";
    }
});