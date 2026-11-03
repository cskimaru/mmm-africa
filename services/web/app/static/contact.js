/* Contact form: posts the message to the directory service. */
(function () {
  "use strict";
  const { api } = window.MM;
  const $ = (id) => document.getElementById(id);
  const form = $("contact-form");
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("c-err").textContent = "";
    if (!form.checkValidity()) { $("c-err").textContent = "Please fill in your name, a valid email and a message."; return; }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const r = await api("POST", "/api/directory/messages", {
        name: $("c-name").value.trim(), email: $("c-email").value.trim(), country: $("c-country").value.trim(),
        topic: $("c-topic").value, body: $("c-body").value.trim(), website: $("c-website").value,
      });
      form.querySelectorAll(".row, .field, .actions").forEach((el) => { el.hidden = true; });
      $("c-ok").textContent = r.detail; $("c-ok").hidden = false;
    } catch (e) { $("c-err").textContent = e.message; btn.disabled = false; }
  });
})();
