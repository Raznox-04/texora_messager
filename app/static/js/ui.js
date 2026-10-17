const UI = (() => {
    function toast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }

    function formatTime(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        const h = String(d.getHours()).padStart(2, "0");
        const m = String(d.getMinutes()).padStart(2, "0");
        return `${h}:${m}`;
    }

    function formatDate(iso) {
        if (!iso) return "";
        return new Date(iso).toLocaleDateString("fa-IR");
    }

    function avatarText(name) {
        if (!name) return "؟";
        return name.trim().charAt(0).toUpperCase();
    }

    // باز کردن مودال با کلاس active
    function openModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.add("active");
    }

    // بستن مودال با حذف کلاس active
    function closeModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.remove("active");
    }

    return { toast, escapeHtml, formatTime, formatDate, avatarText, closeModal, openModal };
})();