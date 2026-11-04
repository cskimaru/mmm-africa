/* Officers' area: sign in, answer messages, keep chapters, leaders and events up to date, manage accounts. */
(function () {
  "use strict";
  const { api, me, h, toast, hasRole, confirmClick } = window.MM;
  const $ = (id) => document.getElementById(id);
  const D = "/api/directory";
  const fmt = (d) => (d ? new Date(d).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");
  const ROLE_NAMES = { owner: "Owner", editor: "Editor" };
  const LEVEL_NAMES = { international: "International", continental: "Continental", national: "National" };
  const TOPIC_NAMES = { general: "General", start_chapter: "Start a chapter", partner: "Partnering", volunteer: "Volunteering" };
  let user = null;
  let units = [];

  async function start() {
    user = await me();
    if (!user) { $("login-form").hidden = false; $("dash").hidden = true; return; }
    $("login-form").hidden = true; $("dash").hidden = false;
    $("me-name").textContent = user.display_name;
    $("me-roles").textContent = "(" + user.roles.map((r) => ROLE_NAMES[r] || r).join(", ") + ")";
    document.querySelectorAll("[data-role]").forEach((b) => { b.hidden = !hasRole(user, b.dataset.role); });
    if (hasRole(user, "owner")) {
      api("GET", "/api/auth/requests").then((rows) => {
        if (rows.length) document.querySelector("[data-tab=people]").textContent = `Officer accounts (${rows.length} waiting)`;
      }).catch(() => {});
    }
    const wanted = location.hash.replace("#", "");
    const tab = document.querySelector(`[data-tab="${wanted}"]:not([hidden])`) || document.querySelector("[data-tab=text]");
    select(tab.dataset.tab);
  }

  // ---- Tabs ----
  document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => select(b.dataset.tab)));
  function select(name) {
    document.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
    document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== name; });
    history.replaceState(null, "", "#" + name);
    ({ text: loadText, pages: loadPages, messages: loadMessages, chapters: loadUnits, leaders: loadLeaders, events: loadEvents, people: loadPeople, account: () => {} })[name]();
  }

  // ---- Sign in / out ----
  $("login-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("l-err").textContent = "";
    try { await api("POST", "/api/auth/login", { email: $("l-email").value.trim(), password: $("l-password").value }); $("l-password").value = ""; await start(); }
    catch (e) { $("l-err").textContent = e.message; }
  });
  $("logout").addEventListener("click", async () => { try { await api("POST", "/api/auth/logout"); } catch (e) { /* ignore */ } location.href = "/"; });

  // ---- Website text ----
  const textFields = () => [...document.querySelectorAll("#text-form [data-key]")];
  let savedText = {};
  function markChanged(el) {
    const flag = document.querySelector(`[data-changed-for="${CSS.escape(el.dataset.key)}"]`);
    if (flag) flag.hidden = el.value === el.dataset.default;
  }
  async function loadText() {
    try {
      savedText = (await api("GET", `${D}/content`)).values;
      textFields().forEach((el) => {
        el.value = savedText[el.dataset.key] !== undefined ? savedText[el.dataset.key] : el.dataset.default;
        markChanged(el);
      });
    } catch (e) { $("t-err").textContent = e.message; }
  }
  textFields().forEach((el) => el.addEventListener("input", () => markChanged(el)));
  $("text-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("t-err").textContent = "";
    const values = {};
    textFields().forEach((el) => {
      const key = el.dataset.key;
      const value = el.value.trim() === "" || el.value === el.dataset.default ? "" : el.value;
      if (value !== (savedText[key] || "")) values[key] = value;
    });
    if (!Object.keys(values).length) { toast("Nothing has changed"); return; }
    try {
      savedText = (await api("PUT", `${D}/content`, { values })).values;
      textFields().forEach((el) => { if (el.value.trim() === "") el.value = el.dataset.default; markChanged(el); });
      toast("Saved. The website shows the new text within a minute.");
    } catch (e) { $("t-err").textContent = e.message; }
  });

  // ---- Pages ----
  async function loadPages() {
    try {
      const rows = await api("GET", `${D}/pages`);
      $("pages-body").replaceChildren(...(rows.length ? rows.map((p) => {
        const del = h("button", { class: "btn link danger", type: "button" }, "Delete");
        confirmClick(del, "Confirm delete", async () => { try { await api("DELETE", `${D}/pages/${p.id}`); toast("Page deleted"); loadPages(); } catch (e) { toast(e.message); } });
        return h("tr", null,
          h("td", null, p.title, p.hidden ? h("span", { class: "muted" }, " (hidden)") : null),
          h("td", null, h("a", { href: `/pages/${p.slug}`, target: "_blank", rel: "noopener" }, `/pages/${p.slug}`)),
          h("td", null, p.in_menu ? "Yes" : "No"),
          h("td", null, h("button", { class: "btn link", type: "button", onclick: () => editPage(p) }, "Edit"), " ", del));
      }) : [h("tr", null, h("td", { colspan: "4", class: "muted" }, "No pages yet. Add the first one below."))]));
    } catch (e) { toast(e.message); }
  }
  function resetPageForm() { $("page-form").reset(); $("p-id").value = ""; $("p-position").value = "100"; $("p-err").textContent = ""; $("page-form-title").textContent = "Add a page"; }
  function editPage(p) {
    $("p-id").value = p.id; $("p-title").value = p.title; $("p-slug").value = p.slug; $("p-summary").value = p.summary;
    $("p-body").value = p.body; $("p-position").value = p.position; $("p-menu").checked = p.in_menu; $("p-hidden").checked = p.hidden;
    $("page-form-title").textContent = "Edit " + p.title;
    $("page-form").scrollIntoView({ behavior: "smooth" });
  }
  $("page-reset").addEventListener("click", resetPageForm);
  $("p-title").addEventListener("input", () => {
    if ($("p-id").value) return;
    $("p-slug").value = $("p-title").value.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  });
  $("page-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("p-err").textContent = "";
    const body = {
      title: $("p-title").value.trim(), slug: $("p-slug").value.trim().toLowerCase(), summary: $("p-summary").value.trim(),
      body: $("p-body").value, position: Number($("p-position").value || 100), in_menu: $("p-menu").checked, hidden: $("p-hidden").checked,
    };
    try {
      const id = $("p-id").value;
      await api(id ? "PATCH" : "POST", id ? `${D}/pages/${id}` : `${D}/pages`, body);
      toast("Page saved"); resetPageForm(); loadPages();
    } catch (e) { $("p-err").textContent = e.message; }
  });

  // ---- Messages ----
  $("m-show-handled").addEventListener("change", loadMessages);
  async function loadMessages() {
    const list = $("message-list");
    const status = $("m-show-handled").checked ? "all" : "open";
    try {
      const rows = await api("GET", `${D}/messages?status=${status}`);
      list.replaceChildren();
      if (!rows.length) { list.append(h("p", { class: "muted" }, "No messages waiting. Messages sent from the Contact page appear here.")); return; }
      rows.forEach((m) => {
        const done = h("button", { class: "btn small", type: "button" }, "Mark as handled");
        done.addEventListener("click", async () => {
          try { await api("POST", `${D}/messages/${m.id}/handled`); toast("Marked as handled"); loadMessages(); } catch (e) { toast(e.message); }
        });
        list.append(h("article", { class: "card message" },
          h("div", { class: "message-head" },
            h("strong", null, m.name), h("a", { href: "mailto:" + m.email }, m.email),
            m.country ? h("span", null, m.country) : null,
            h("span", { class: "pill" }, TOPIC_NAMES[m.topic] || m.topic),
            h("span", { class: "muted" }, fmt(m.created_at))),
          h("p", { class: "message-body" }, m.body),
          m.handled_at ? h("p", { class: "muted small" }, "Handled " + fmt(m.handled_at)) : done));
      });
    } catch (e) { list.replaceChildren(h("p", { class: "err" }, e.message)); }
  }

  // ---- Chapters (units) ----
  async function fetchUnits() {
    const s = await api("GET", `${D}/structure`);
    units = [...s.international, ...s.continental, ...s.national];
    return s;
  }
  async function loadUnits() {
    try {
      await fetchUnits();
      $("units-body").replaceChildren(...units.map((u) => {
        const edit = h("button", { class: "btn link", type: "button", onclick: () => editUnit(u) }, "Edit");
        const del = u.level === "national" ? h("button", { class: "btn link danger", type: "button" }, "Remove") : null;
        if (del) confirmClick(del, "Confirm remove", async () => {
          try { await api("DELETE", `${D}/units/${u.id}`); toast("Chapter removed"); loadUnits(); } catch (e) { toast(e.message); }
        });
        return h("tr", null,
          h("td", null, h("a", { href: u.level === "national" ? `/chapters/${u.slug}` : "/" }, u.name), u.hidden ? h("span", { class: "muted" }, " (hidden)") : null),
          h("td", null, LEVEL_NAMES[u.level]), h("td", null, (u.country_code || "").toUpperCase()),
          h("td", null, u.status === "forming" ? "Forming" : "Established"),
          h("td", null, u.website_url ? h("a", { href: u.website_url, target: "_blank", rel: "noopener" }, u.website_url.replace(/^https?:\/\//, "")) : "—"),
          h("td", null, edit, " ", del));
      }));
    } catch (e) { toast(e.message); }
  }
  function resetUnitForm() {
    $("unit-form").reset(); $("u-id").value = ""; $("u-position").value = "100"; $("u-err").textContent = "";
    $("unit-form-title").textContent = "Add a national chapter";
  }
  function editUnit(u) {
    $("u-id").value = u.id; $("u-name").value = u.name; $("u-short").value = u.short_name; $("u-slug").value = u.slug;
    $("u-country").value = u.country_code; $("u-city").value = u.city; $("u-status").value = u.status;
    $("u-website").value = u.website_url; $("u-email").value = u.email; $("u-phone").value = u.phone;
    $("u-position").value = u.position; $("u-summary").value = u.summary; $("u-hidden").checked = u.hidden;
    $("unit-form-title").textContent = "Edit " + u.name;
    $("unit-form").scrollIntoView({ behavior: "smooth" });
  }
  $("unit-reset").addEventListener("click", resetUnitForm);
  $("unit-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("u-err").textContent = "";
    const body = {
      name: $("u-name").value.trim(), short_name: $("u-short").value.trim(), slug: $("u-slug").value.trim().toLowerCase(),
      country_code: $("u-country").value.trim(), city: $("u-city").value.trim(), status: $("u-status").value,
      website_url: $("u-website").value.trim(), email: $("u-email").value.trim(), phone: $("u-phone").value.trim(),
      position: Number($("u-position").value || 100), summary: $("u-summary").value.trim(), hidden: $("u-hidden").checked,
    };
    try {
      const id = $("u-id").value;
      if (id) { await api("PATCH", `${D}/units/${id}`, body); toast("Saved"); }
      else {
        const africa = units.find((u) => u.level === "continental");
        await api("POST", `${D}/units`, Object.assign(body, { level: "national", parent_id: africa && africa.id }));
        toast("Chapter added");
      }
      resetUnitForm(); loadUnits();
    } catch (e) { $("u-err").textContent = e.message; }
  });

  // ---- Leaders ----
  async function loadLeaders() {
    try {
      await fetchUnits();
      const sel = $("o-unit"); const current = sel.value;
      sel.replaceChildren(...units.filter((u) => u.level !== "international").map((u) => h("option", { value: u.slug, "data-id": u.id }, u.name)));
      if (current && units.some((u) => u.slug === current)) sel.value = current;
      await loadOfficers();
    } catch (e) { toast(e.message); }
  }
  $("o-unit").addEventListener("change", loadOfficers);
  async function loadOfficers() {
    const slug = $("o-unit").value;
    if (!slug) return;
    try {
      const rows = await api("GET", `${D}/officers?unit=${encodeURIComponent(slug)}`);
      $("officers-body").replaceChildren(...(rows.length ? rows.map((o) => {
        const del = h("button", { class: "btn link danger", type: "button" }, "Remove");
        confirmClick(del, "Confirm remove", async () => { try { await api("DELETE", `${D}/officers/${o.id}`); loadOfficers(); } catch (e) { toast(e.message); } });
        return h("tr", null, h("td", null, o.name), h("td", null, o.role), h("td", null, o.term || "—"), h("td", null, String(o.position)), h("td", null, del));
      }) : [h("tr", null, h("td", { colspan: "5", class: "muted" }, "No leaders listed yet."))]));
    } catch (e) { toast(e.message); }
  }
  $("officer-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("o-err").textContent = "";
    const opt = $("o-unit").selectedOptions[0];
    try {
      await api("POST", `${D}/officers`, {
        unit_id: opt && opt.dataset.id, name: $("o-name").value.trim(), role: $("o-role").value.trim(),
        term: $("o-term").value.trim(), email: $("o-email").value.trim(), position: Number($("o-position").value || 100),
      });
      $("officer-form").reset(); $("o-position").value = "100"; toast("Leader added"); loadOfficers();
    } catch (e) { $("o-err").textContent = e.message; }
  });

  // ---- Events ----
  let events = [];
  async function loadEvents() {
    try {
      await fetchUnits();
      $("e-host").replaceChildren(h("option", { value: "" }, "None"), ...units.filter((u) => u.level === "national").map((u) => h("option", { value: u.id }, u.name)));
      events = await api("GET", `${D}/events`);
      const STATES = { upcoming: "Coming up", happening: "Happening now", ended: "Held" };
      $("events-body").replaceChildren(...events.map((e) => {
        const del = h("button", { class: "btn link danger", type: "button" }, "Remove");
        confirmClick(del, "Confirm remove", async () => { try { await api("DELETE", `${D}/events/${e.id}`); loadEvents(); } catch (err) { toast(err.message); } });
        return h("tr", null, h("td", null, h("a", { href: `/events/${e.slug}` }, e.title), e.hidden ? h("span", { class: "muted" }, " (hidden)") : null),
          h("td", null, `${e.starts_on} → ${e.ends_on}`), h("td", null, e.host ? e.host.name : "—"), h("td", null, STATES[e.state]),
          h("td", null, h("button", { class: "btn link", type: "button", onclick: () => editEvent(e) }, "Edit"), " ", del));
      }));
    } catch (e) { toast(e.message); }
  }
  function resetEventForm() { $("event-form").reset(); $("e-id").value = ""; $("e-err").textContent = ""; $("event-form-title").textContent = "Add an event"; }
  function editEvent(e) {
    $("e-id").value = e.id; $("e-title").value = e.title; $("e-slug").value = e.slug; $("e-theme").value = e.theme;
    $("e-scripture").value = e.scripture; $("e-start").value = e.starts_on; $("e-end").value = e.ends_on;
    $("e-venue").value = e.venue; $("e-location").value = e.location; $("e-host").value = e.host_unit_id || "";
    $("e-register").value = e.register_url; $("e-summary").value = e.summary; $("e-recap").value = e.recap; $("e-hidden").checked = e.hidden;
    $("event-form-title").textContent = "Edit " + e.title;
    $("event-form").scrollIntoView({ behavior: "smooth" });
  }
  $("event-reset").addEventListener("click", resetEventForm);
  $("event-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("e-err").textContent = "";
    const body = {
      title: $("e-title").value.trim(), slug: $("e-slug").value.trim().toLowerCase(), theme: $("e-theme").value.trim(),
      scripture: $("e-scripture").value.trim(), starts_on: $("e-start").value, ends_on: $("e-end").value,
      venue: $("e-venue").value.trim(), location: $("e-location").value.trim(), host_unit_id: $("e-host").value || null,
      register_url: $("e-register").value.trim(), summary: $("e-summary").value.trim(), recap: $("e-recap").value.trim(), hidden: $("e-hidden").checked,
    };
    try {
      const id = $("e-id").value;
      await api(id ? "PATCH" : "POST", id ? `${D}/events/${id}` : `${D}/events`, body);
      toast("Saved"); resetEventForm(); loadEvents();
    } catch (e) { $("e-err").textContent = e.message; }
  });

  // ---- Officer accounts ----
  async function loadPeople() {
    try {
      const [users, invites, requests] = await Promise.all([api("GET", "/api/auth/users"), api("GET", "/api/auth/invitations"), api("GET", "/api/auth/requests")]);
      $("requests-body").replaceChildren(...(requests.length ? requests.map((r) => {
        const decide = (path, body, done) => async () => {
          try { await api("POST", `/api/auth/requests/${r.id}/${path}`, body); toast(done); loadPeople(); } catch (e) { toast(e.message); }
        };
        const decline = h("button", { class: "btn link danger", type: "button" }, "Decline");
        confirmClick(decline, "Confirm decline", decide("decline", undefined, "Request declined"));
        return h("tr", null, h("td", null, r.display_name), h("td", null, r.position), h("td", null, r.email),
          h("td", null, r.phone), h("td", null, r.country), h("td", null, fmt(r.created_at)),
          h("td", null,
            h("button", { class: "btn small", type: "button", onclick: decide("approve", { roles: ["editor"] }, r.display_name + " can now sign in as an editor") }, "Approve as editor"), " ",
            h("button", { class: "btn small ghost", type: "button", onclick: decide("approve", { roles: ["owner"] }, r.display_name + " can now sign in as an owner") }, "Approve as owner"), " ",
            decline));
      }) : [h("tr", null, h("td", { colspan: "7", class: "muted" }, "No requests waiting."))]));
      const tab = document.querySelector("[data-tab=people]");
      tab.textContent = requests.length ? `Officer accounts (${requests.length} waiting)` : "Officer accounts";
      $("users-body").replaceChildren(...users.map((u) => {
        const act = h("button", { class: "btn link danger", type: "button" }, u.is_active ? "Remove access" : "Restore access");
        if (u.id !== user.id) confirmClick(act, "Confirm", async () => {
          try { await api("PATCH", `/api/auth/users/${u.id}`, { is_active: !u.is_active }); loadPeople(); } catch (e) { toast(e.message); }
        });
        return h("tr", null, h("td", null, u.display_name), h("td", null, u.position || "—"), h("td", null, u.email), h("td", null, u.phone || "—"), h("td", null, u.roles.map((r) => ROLE_NAMES[r]).join(", ")),
          h("td", null, fmt(u.last_login_at)), h("td", null, u.id === user.id ? "You" : u.is_active ? act : h("span", null, "No access ", act)));
      }));
      $("invites-body").replaceChildren(...invites.map((i) => {
        const state = i.accepted_at ? "Accepted" : i.revoked_at ? "Cancelled" : new Date(i.expires_at) < new Date() ? "Expired" : "Waiting";
        const cancel = state === "Waiting" ? h("button", { class: "btn link danger", type: "button" }, "Cancel") : null;
        if (cancel) confirmClick(cancel, "Confirm cancel", async () => { await api("DELETE", `/api/auth/invitations/${i.id}`); loadPeople(); });
        return h("tr", null, h("td", null, i.email), h("td", null, i.roles.map((r) => ROLE_NAMES[r]).join(", ")), h("td", null, state), h("td", null, cancel));
      }));
    } catch (e) { toast(e.message); }
  }
  $("invite-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("i-err").textContent = "";
    const roles = [...document.querySelectorAll("input[name=role]:checked")].map((c) => c.value);
    try {
      const r = await api("POST", "/api/auth/invitations", { email: $("i-email").value.trim(), display_name: $("i-name").value.trim(), roles });
      $("invite-url").value = r.invite_url; $("invite-result").hidden = false; $("invite-hint").hidden = false;
      $("i-email").value = ""; $("i-name").value = ""; loadPeople();
    } catch (e) { $("i-err").textContent = e.message; }
  });
  $("copy-invite").addEventListener("click", async () => {
    const input = $("invite-url");
    try { await navigator.clipboard.writeText(input.value); toast("Link copied"); } catch (e) { input.select(); toast("Select the link and copy it"); }
  });

  // ---- Account ----
  $("password-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("pw-err").textContent = "";
    try {
      await api("POST", "/api/auth/password", { current_password: $("pw-current").value, new_password: $("pw-new").value });
      toast("Password changed. Please sign in again."); setTimeout(() => { location.reload(); }, 1200);
    } catch (e) { $("pw-err").textContent = e.message; }
  });

  start();
})();
