// auto-expand small reply textareas on focus
document.addEventListener("focusin", (e) => {
  const t = e.target;
  if (t.matches && t.matches("textarea.evaluate-textarea")) {
    t.rows = 10;
  }
});

// Typewriter effect for banner
document.addEventListener("DOMContentLoaded", () => {
  const el = document.querySelector("[data-type]");
  if (!el) return;
  const text = el.dataset.type;
  el.textContent = "";
  let i = 0;
  const tick = () => {
    if (i < text.length) {
      el.textContent += text[i++];
      setTimeout(tick, 18);
    } else {
      el.insertAdjacentHTML("beforeend", '<span class="blink">_</span>');
    }
  };
  tick();
});
