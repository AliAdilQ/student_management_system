"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const toggle = document.getElementById("menu-toggle");
  const close = () => { sidebar?.classList.remove("open"); backdrop?.classList.remove("active"); toggle?.setAttribute("aria-expanded", "false"); };
  toggle?.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    backdrop.classList.toggle("active", open);
    toggle.setAttribute("aria-expanded", String(open));
  });
  backdrop?.addEventListener("click", close);
  document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
  document.getElementById("mark-all-present")?.addEventListener("click", () => {
    document.querySelectorAll('input[type="radio"][value="present"]').forEach(input => { input.checked = true; });
  });
});
