/* Request access: a leader asks for an officers' account; an owner approves it. */
(function () {
  "use strict";
  const { api } = window.MM;
  const $ = (id) => document.getElementById(id);
  const form = $("request-form");
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("r-err").textContent = "";
    if (!form.checkValidity()) { $("r-err").textContent = "Please fill in every box. The password needs at least 10 characters."; return; }
    if ($("r-password").value !== $("r-password2").value) { $("r-err").textContent = "The two passwords don't match."; return; }
    const phone = $("r-phone").value.trim();
    if (!phone.startsWith("+")) { $("r-err").textContent = "Start the phone number with + and the country code, for example +254."; return; }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const r = await api("POST", "/api/auth/requests", {
        display_name: $("r-name").value.trim(), email: $("r-email").value.trim(), phone,
        country: $("r-country").value.trim(), position: $("r-position").value.trim(),
        password: $("r-password").value, website: $("r-website").value,
      });
      form.querySelectorAll(".row, .field, .actions").forEach((el) => { el.hidden = true; });
      $("r-ok").textContent = r.detail; $("r-ok").hidden = false;
    } catch (e) { $("r-err").textContent = e.message; btn.disabled = false; }
  });
})();
