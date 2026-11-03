/* Private preview only: lets reviewers try each colour scheme. The choice is remembered on this device;
   the scheme everyone sees is set with SITE_PALETTE in .env. */
(function () {
  "use strict";
  const KEY = "mmma.palette";
  let saved = "";
  try { saved = localStorage.getItem(KEY) || ""; } catch (e) { /* storage blocked */ }
  if (saved) document.documentElement.dataset.palette = saved;
  document.addEventListener("DOMContentLoaded", function () {
    const buttons = document.querySelectorAll(".palette-picker button");
    function mark(key) { buttons.forEach((b) => b.setAttribute("aria-checked", String(b.dataset.palette === key))); }
    mark(document.documentElement.dataset.palette);
    buttons.forEach((b) => b.addEventListener("click", function () {
      document.documentElement.dataset.palette = b.dataset.palette;
      try { localStorage.setItem(KEY, b.dataset.palette); } catch (e) { /* storage blocked */ }
      mark(b.dataset.palette);
    }));
  });
})();
