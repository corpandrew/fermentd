const root = document.querySelector("[data-dashboard]");

function boardIds(alerts) {
  return alerts
    .filter((alert) => alert.status === "open" || !alert.reminder)
    .map((alert) => String(alert.id))
    .join(",");
}

function setText(card, name, value) {
  const node = card.querySelector(`[data-bind="${name}"]`);
  if (node && node.textContent !== value) node.textContent = value;
}

async function paintVessel(vessel) {
  const card = document.getElementById(`vessel-${vessel.id}`);
  if (!card) return;
  const temp = card.querySelector('[data-bind="temp"]');
  if (temp) {
    const next = vessel.vessel_temp_label || temp.dataset.empty || "";
    if (temp.textContent !== next) temp.textContent = next;
    temp.dataset.tone = vessel.tone || "idle";
  }
  setText(card, "ambient", vessel.ambient_temp_label || "—");
  setText(card, "elapsed", vessel.elapsed_label || "");
  const lamp = card.querySelector('[data-bind="lamp"]');
  if (lamp) lamp.dataset.on = vessel.heater_on ? "1" : "0";
  const heater = card.querySelector('[data-bind="heater"]');
  if (heater) {
    const word = vessel.heater_on ? "on" : "off";
    if (heater.textContent !== word) heater.textContent = word;
  }
  setText(card, "heater-word", vessel.heater_on ? "Heating" : "Off");
  const badge = card.querySelector('[data-bind="heater-badge"]');
  if (badge) badge.className = vessel.heater_on ? "badge heat" : "badge plain";
  const mark = card.querySelector('[data-bind="mark"]');
  if (mark && vessel.meter) {
    if (vessel.meter.mark == null) {
      mark.hidden = true;
    } else {
      mark.hidden = false;
      mark.style.left = `${vessel.meter.mark}%`;
    }
  }
  const fill = card.querySelector('[data-bind="carbonation"]');
  if (fill && vessel.carbonation) fill.style.width = `${vessel.carbonation.progress_pct}%`;
  if (vessel.next_reminder) {
    setText(card, "reminder", vessel.next_reminder.text || "");
    setText(card, "due", vessel.next_reminder.due_label || "");
  }
  const slot = card.querySelector("[data-chart]");
  if (!slot) return;
  const response = await fetch(`/api/vessels/${encodeURIComponent(vessel.id)}/chart`, { cache: "no-store" });
  if (!response.ok) return;
  const svg = await response.text();
  if (slot._svg !== svg) {
    slot.innerHTML = svg;
    slot._svg = svg;
  }
}

let refreshing = false;

async function refresh() {
  if (!root || refreshing || document.hidden) return;
  refreshing = true;
  try {
    const status = await fetch("/api/status", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error("status");
      return response.json();
    });
    const asof = document.querySelector('[data-bind="asof"]');
    if (asof) asof.textContent = status.as_of_label ? `Last reading ${status.as_of_label}` : "No readings yet";
    await Promise.all(status.vessels.map(paintVessel));
    const alerts = document.querySelector("[data-alerts]");
    const ids = boardIds(status.alerts);
    const focused = alerts && alerts.contains(document.activeElement);
    if (alerts && alerts.dataset.ids !== ids && !focused) {
      const html = await fetch("/partials/alerts", { cache: "no-store" }).then((response) => response.text());
      alerts.innerHTML = html;
      alerts.dataset.ids = ids;
    }
    document.body.dataset.live = "ok";
  } catch (_error) {
    document.body.dataset.live = "down";
  } finally {
    refreshing = false;
  }
}

if (root) {
  setInterval(refresh, 8000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh();
  });
}

// Confirm dialogs: <form data-confirm> or <a data-confirm data-confirm-form="id">.
const dialog = document.getElementById("confirm-dialog");

function askConfirm(node, proceed) {
  if (!dialog || typeof dialog.showModal !== "function") {
    if (window.confirm(node.dataset.confirm)) proceed();
    return;
  }
  dialog.querySelector("#confirm-title").textContent = node.dataset.confirmTitle || "Are you sure?";
  dialog.querySelector("#confirm-text").textContent = node.dataset.confirm || "";
  const ok = dialog.querySelector("#confirm-ok");
  ok.textContent = node.dataset.confirmOk || "Confirm";
  ok.className = node.dataset.confirmDanger !== undefined ? "destructive" : "";
  dialog.returnValue = "";
  dialog.addEventListener(
    "close",
    () => {
      if (dialog.returnValue === "ok") proceed();
    },
    { once: true },
  );
  dialog.showModal();
}

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.dataset.confirm === undefined || form.dataset.confirmed) return;
  event.preventDefault();
  askConfirm(form, () => {
    form.dataset.confirmed = "1";
    form.submit();
  });
});

document.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-confirm-form]");
  if (!link) return;
  const form = document.getElementById(link.dataset.confirmForm);
  if (!form) return;
  event.preventDefault();
  askConfirm(link, () => form.submit());
});

// Dialog openers: <button data-open="dialog-id">, and [data-close] inside a dialog.
document.addEventListener("click", (event) => {
  const opener = event.target.closest("[data-open]");
  if (opener) {
    const target = document.getElementById(opener.dataset.open);
    if (target && typeof target.showModal === "function") {
      event.preventDefault();
      target.showModal();
    } else {
      const fallback = document.getElementById(`${opener.dataset.open}-fallback`);
      if (fallback) fallback.open = true;
    }
    return;
  }
  const closer = event.target.closest("[data-close]");
  if (closer) {
    const open = closer.closest("dialog");
    if (open) open.close();
  }
});
document.documentElement.classList.add("js");

// Keep the suggested batch name in step with the chosen beverage until it is edited.
document.querySelectorAll("form.start").forEach((form) => {
  const select = form.querySelector("[data-profile-select]");
  const name = form.querySelector("[data-batch-name]");
  if (!select || !name) return;
  select.addEventListener("change", () => {
    const previous = name.dataset.suggested ?? name.defaultValue;
    if (name.value === previous) {
      const next = select.selectedOptions[0]?.dataset.defaultName || "";
      name.value = next;
      name.dataset.suggested = next;
    }
  });
});

// "Saved, applying…": poll the command until the controller finishes, then reload clean.
const pendingBanner = document.querySelector(".banner.notice[data-pending]");
if (pendingBanner && pendingBanner.dataset.pending) {
  const id = pendingBanner.dataset.pending;
  const clean = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("notice");
    url.searchParams.delete("pending");
    return url;
  };
  const check = async () => {
    try {
      const response = await fetch(`/api/commands/${encodeURIComponent(id)}`, { cache: "no-store" });
      if (response.ok) {
        const body = await response.json();
        if (body.status === "done") {
          window.location.replace(clean().toString());
          return;
        }
        if (body.status !== "pending") {
          const url = clean();
          url.searchParams.set("error", body.message || "The controller did not apply that action.");
          window.location.replace(url.toString());
          return;
        }
      }
    } catch (_error) {
      // Keep trying; the next poll may succeed.
    }
    setTimeout(check, 1500);
  };
  setTimeout(check, 1000);
}

// Guide checkboxes persist per guide in localStorage (client-side only).
document.querySelectorAll("[data-guide]").forEach((guide) => {
  const key = `fermentd-guide-${guide.dataset.guide}`;
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(key) || "{}");
  } catch (_error) {
    saved = {};
  }
  guide.querySelectorAll("input[data-step]").forEach((box) => {
    box.checked = Boolean(saved[box.dataset.step]);
    box.addEventListener("change", () => {
      saved[box.dataset.step] = box.checked;
      try {
        localStorage.setItem(key, JSON.stringify(saved));
      } catch (_error) {
        // Storage may be unavailable; checkmarks still work for this visit.
      }
    });
  });
  const reset = guide.parentElement.querySelector("[data-reset-steps]");
  if (reset) {
    reset.addEventListener("click", () => {
      saved = {};
      try {
        localStorage.removeItem(key);
      } catch (_error) {
        // ignore
      }
      guide.querySelectorAll("input[data-step]").forEach((box) => {
        box.checked = false;
      });
    });
  }
});
