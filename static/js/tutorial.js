/* tutorial.js - the "Start Here - Learn HTTPS" guided tutorial.

   Each step lists what the learner must actually do before Next works.
   The lab pages report real actions with markTutorialEvent(), for example
   "http-done" when an HTTP simulation reaches its last step.
   Nothing here plays or advances a simulation by itself.

   Examiner mode (a button in the tutorial and on the start page) removes the
   step requirements for this browser tab only. */

"use strict";

// Things the learner has really done on this page, e.g. { "http-done": true }.
const tutorialEvents = {};

const GUIDE_STEPS = [
  {
    title: "Your browser visits a website",
    text: "When you visit a website, your browser (the app you browse with) sends " +
      "information to the website's server (the computer that runs the website).",
    todo: "Look at the connection, then press Next.",
    needs: [],
    target: "#diagram",
    place: "below",   // the diagram is wide, so the note goes underneath it rather than over it
  },
  {
    title: "Try HTTP",
    text: "HTTP sends your information without encryption, so it travels as readable text.",
    todo: "Choose HTTP, press Send message, then press Next Step until the last step.",
    needs: ["http-done"],
    target: "#protocol-toggle",
    also: ["#player [data-action=start]"],
  },
  {
    title: "Look inside a packet",
    text: "Your message travelled in packets. Opening one shows exactly what anyone on the " +
      "network could read.",
    todo: "Select a blue (readable) packet in the Packets sent list or on the diagram.",
    needs: ["inspected-plain"],
    target: "#packet-log-box",
  },
  {
    title: "Try HTTPS",
    text: "HTTPS encrypts your information while it travels. Encryption scrambles it " +
      "so that only the website can turn it back into readable text.",
    todo: "Switch to HTTPS, press Send message and press Next Step until the last step.",
    needs: ["https-done"],
    target: "#protocol-toggle",
    also: ["#player [data-action=start]"],
  },
  {
    title: "Compare the results",
    text: "HTTP sends information without encryption. HTTPS protects it while it travels. " +
      "With HTTPS, the network can still see which website you visit, but not what you send.",
    todo: "Compare the two columns. Both need a finished HTTP and HTTPS run.",
    needs: ["http-done", "https-done"],
    target: "#compare-box",
  },
  {
    title: "Add an eavesdropper",
    text: "Now see the same thing from the attacker's side: someone on the same Wi-Fi " +
      "watching the connection.",
    todo: "Tick the eavesdropper box, send a message and press Next Step until the last step.",
    needs: ["observer-done"],
    target: "#observer-option",
    place: "top",   // above the checkbox, so the diagram (where the eavesdropper appears) stays visible
  },
];

// Shown when the whole HTTP vs HTTPS lab has been completed.
const LAB_COMPLETE = {
  title: "HTTP vs HTTPS Lab Completed",
  text: "You've seen how HTTP and HTTPS handle information differently.",
  nextName: "TLS Handshake",
  nextUrl: "/tls-handshake",
  nextTeaches: "How your browser and a website agree on a secret key before any data is sent.",
};

const WARNING_TEXT = "Please complete this section before moving onto the next!";

const guide = {
  index: -1,            // current step, or -1 when no step is showing
  box: null,
  target: null,
  highlighted: [],
  moved: false,         // true once the user has dragged the box somewhere
  savedLeft: 0,
  savedTop: 0,
  drag: null,           // offset of the pointer inside the box while dragging
  warningTimer: null,
  completionShown: false,
};

/* ---------- Completion checks ---------- */

// Called by the lab pages when the learner really does something.
function markTutorialEvent(name) {
  tutorialEvents[name] = true;
  refreshGuideStatus();

  // If the whole lab is now done and the tutorial is not open, offer the next lab once.
  if (labIsComplete() && !guide.box && !guide.completionShown && $("#compare-box")) {
    showLabComplete();
  }
}

// True if every action in the list has happened.
function hasDone(needs) {
  return needs.every(function (name) { return tutorialEvents[name] === true; });
}

// A step is complete when its actions have happened, or always in examiner mode.
function stepIsComplete(index) {
  return isExaminerMode() || hasDone(GUIDE_STEPS[index].needs);
}

// The lab counts as complete when every step's actions have really happened.
function labIsComplete() {
  return GUIDE_STEPS.every(function (step) { return hasDone(step.needs); });
}

/* ---------- Examiner mode ---------- */

// Kept in sessionStorage: it lasts for this browser tab only, so ordinary users start guided.
let examinerFallback = false;   // used if the browser blocks sessionStorage

function isExaminerMode() {
  try {
    return window.sessionStorage.getItem("examinerMode") === "on";
  } catch (error) {
    return examinerFallback;
  }
}

function setExaminerMode(on) {
  try {
    if (on) window.sessionStorage.setItem("examinerMode", "on");
    else window.sessionStorage.removeItem("examinerMode");
  } catch (error) {
    examinerFallback = on;
  }
  updateExaminerButtons();
  refreshGuideStatus();
  showToast(on ? "Examiner mode enabled — tutorial restrictions removed."
               : "Guided mode restored — each section must be completed again.");
}

function toggleExaminerMode() {
  setExaminerMode(!isExaminerMode());
}

// Every button with data-examiner-toggle shows the current mode.
function updateExaminerButtons() {
  const on = isExaminerMode();
  document.body.classList.toggle("examiner-mode", on);
  $all("[data-examiner-toggle]").forEach(function (button) {
    // One button, two lines: "Examiner Button" on top, the action underneath.
    button.innerHTML = '<span class="examiner-line1">Examiner Button</span>' +
      '<span class="examiner-line2">' + (on ? "Restore all restrictions" : "Remove all restrictions") + "</span>";
    button.classList.toggle("is-on", on);
    button.setAttribute("aria-pressed", on ? "true" : "false");
  });
}

// A small message at the top of the screen that fades out after a few seconds.
let toastTimer = null;
function showToast(message) {
  let toast = $("#tutorial-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "tutorial-toast";
    toast.className = "tutorial-toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 3500);
}

/* ---------- Showing the tutorial box ---------- */

// True if an element is actually visible on the page.
function isVisible(element) {
  if (!element || !element.getClientRects().length) return false;
  const rect = element.getBoundingClientRect();
  return rect.right > 0 && rect.left < window.innerWidth && getComputedStyle(element).visibility !== "hidden";
}

// Phones get a note docked to the bottom of the screen instead of a floating one.
function isNarrowScreen() {
  return window.innerWidth <= 640;
}

function startGuide() {
  // The tutorial lives on the HTTP vs HTTPS page, so go there first if needed.
  if (!$("#compare-box")) {
    window.location.href = "/?tutorial=1";
    return;
  }
  guide.moved = false;
  showGuideStep(0);
}

// Remove the box and the outlines, but remember where the user dragged it.
function removeGuideBox() {
  document.body.style.paddingBottom = "";
  guide.highlighted.forEach(function (element) { element.classList.remove("guide-target"); });
  guide.highlighted = [];
  if (guide.box) guide.box.remove();
  guide.box = null;
  guide.target = null;
  guide.index = -1;
  clearTimeout(guide.warningTimer);
  clearTimeout(guide.skipTimer);
  window.removeEventListener("scroll", positionGuide, true);
  window.removeEventListener("resize", positionGuide);
}

function closeGuide() {
  removeGuideBox();
  guide.moved = false;
}

// Create an empty tutorial box with the draggable header and the examiner button.
function buildGuideBox(headerRight, bodyHtml) {
  const box = document.createElement("div");
  box.className = "guide";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "Learn HTTPS tutorial");
  box.innerHTML =
    '<div class="guide-count guide-head" title="Drag to move"><span>Learn HTTPS</span><span>' + headerRight + "</span></div>" +
    '<div class="guide-examiner"><button class="btn btn-sm examiner-toggle" type="button" data-examiner-toggle></button>' +
    '<span class="examiner-note">Examiner mode on: every section is unlocked.</span></div>' +
    bodyHtml;
  document.body.appendChild(box);
  guide.box = box;

  $("[data-examiner-toggle]", box).addEventListener("click", toggleExaminerMode);
  setupDragging(box);
  updateExaminerButtons();
  return box;
}

function showGuideStep(index) {
  removeGuideBox();
  guide.index = index;
  const step = GUIDE_STEPS[index];
  const last = index === GUIDE_STEPS.length - 1;

  const box = buildGuideBox("Step " + (index + 1) + " of " + GUIDE_STEPS.length,
    '<div class="guide-title">' + escapeHtml(step.title) + "</div>" +
    '<p class="guide-text">' + escapeHtml(step.text) + "</p>" +
    '<p class="guide-todo"><strong>What to do:</strong> ' + escapeHtml(step.todo) + "</p>" +
    '<p class="guide-status" aria-live="polite"></p>' +
    '<p class="guide-warning" role="alert"></p>' +
    '<div class="guide-controls">' +
    (index > 0 ? '<button class="btn btn-sm" data-guide="back">Back</button>' : "") +
    '<button class="btn btn-sm skip" data-guide="skip">' + skipLabel(false) + "</button>" +
    '<button class="btn btn-sm btn-primary next" data-guide="next">' + (last ? "Finish" : "Next") + "</button>" +
    "</div>");

  $all("[data-guide]", box).forEach(function (button) {
    button.addEventListener("click", function () {
      const action = button.dataset.guide;
      if (action === "back") showGuideStep(guide.index - 1);
      else if (action === "skip") pressSkip(button);
      else tryToAdvance();
    });
  });

  // Outline the main element (the note sits next to it) plus any extra ones.
  const selectors = [step.target].concat(step.also || []);
  selectors.forEach(function (selector) {
    const element = $(selector);
    if (isVisible(element)) {
      element.classList.add("guide-target");
      guide.highlighted.push(element);
    }
  });
  const target = $(step.target);
  if (isVisible(target)) {
    guide.target = target;
    if (isNarrowScreen() || step.place === "below") {
      // Put the target near the top, so the note underneath does not hide it.
      const headerHeight = $(".site-header").offsetHeight;
      window.scrollTo(0, window.scrollY + target.getBoundingClientRect().top - headerHeight - 16);
    } else {
      target.scrollIntoView({ block: "center", behavior: "auto" });
    }
  }
  refreshGuideStatus();
  positionGuide();
  window.addEventListener("scroll", positionGuide, true);
  window.addEventListener("resize", positionGuide);
  $("[data-guide=next]", box).focus();
}

// Next / Finish: only move on if this section is complete. The button is never disabled,
// so a click on an unfinished section can show the warning instead.
function tryToAdvance() {
  if (!stepIsComplete(guide.index)) {
    showGuideWarning();
    return;
  }
  if (guide.index === GUIDE_STEPS.length - 1) showLabComplete();
  else showGuideStep(guide.index + 1);
}

// Skip is padlocked so one stray click cannot end the tutorial:
// the first click unlocks it, a second click within 4 seconds skips.
function skipLabel(unlocked) {
  return '<svg class="icon"><use href="#i-' + (unlocked ? "unlock" : "lock") + '"/></svg>' +
    (unlocked ? "Click again to skip" : "Skip tutorial");
}

function pressSkip(button) {
  if (button.classList.contains("is-unlocked")) {
    closeGuide();
    return;
  }
  button.classList.add("is-unlocked");
  button.innerHTML = skipLabel(true);
  clearTimeout(guide.skipTimer);
  guide.skipTimer = setTimeout(function () {
    button.classList.remove("is-unlocked");
    button.innerHTML = skipLabel(false);
  }, 4000);
}

// One red warning inside the box. Clicking again restarts its timer instead of adding another.
function showGuideWarning() {
  const warning = $(".guide-warning", guide.box);
  if (!warning) return;
  warning.textContent = WARNING_TEXT;
  warning.classList.add("show");
  clearTimeout(guide.warningTimer);
  guide.warningTimer = setTimeout(function () { warning.classList.remove("show"); }, 3500);
}

// Update the "complete / not complete" line and the look of the Next button.
function refreshGuideStatus() {
  if (!guide.box || guide.index < 0) return;
  const complete = stepIsComplete(guide.index);
  const status = $(".guide-status", guide.box);
  const next = $("[data-guide=next]", guide.box);

  if (isExaminerMode()) status.textContent = "Examiner mode: you can move on freely.";
  else if (complete) status.textContent = "✓ Section complete. Press " + next.textContent + " to continue.";
  else status.textContent = "Not complete yet. Do the task above to unlock " + next.textContent + ".";
  status.classList.toggle("is-complete", complete);

  // Only the look changes; the button stays clickable so an early click can show the warning.
  next.classList.toggle("is-locked", !complete);
  if (complete) {
    $(".guide-warning", guide.box).classList.remove("show");
    clearTimeout(guide.warningTimer);
  }
}

// The end of the lab: say so, and let the learner choose whether to continue.
function showLabComplete() {
  removeGuideBox();
  guide.completionShown = true;
  const box = buildGuideBox("Lab complete",
    '<div class="guide-title">' + escapeHtml(LAB_COMPLETE.title) + "</div>" +
    '<p class="guide-text">' + escapeHtml(LAB_COMPLETE.text) + "</p>" +
    '<p class="guide-todo"><strong>Next lab: ' + escapeHtml(LAB_COMPLETE.nextName) + ".</strong> " +
    escapeHtml(LAB_COMPLETE.nextTeaches) + "</p>" +
    '<div class="guide-controls">' +
    '<a class="btn btn-sm btn-primary" href="' + LAB_COMPLETE.nextUrl + '">Continue to ' + escapeHtml(LAB_COMPLETE.nextName) + "</a>" +
    '<button class="btn btn-sm" data-guide="stay">Stay and explore</button>' +
    "</div>");
  $("[data-guide=stay]", box).addEventListener("click", closeGuide);
  positionGuide();
  window.addEventListener("resize", positionGuide);
  $("[data-guide=stay]", box).focus();
}

/* ---------- Positioning ---------- */

// Place the guide box next to its target: to the right, below, or above.
function positionGuide() {
  const box = guide.box;
  if (!box) return;
  const gap = 14;
  const boxWidth = box.offsetWidth;
  const boxHeight = box.offsetHeight;
  const viewWidth = window.innerWidth;
  const viewHeight = window.innerHeight;

  // Once dragged, the box stays where the user put it (kept inside the window).
  if (guide.moved) {
    document.body.style.paddingBottom = "";
    moveGuideTo(guide.savedLeft, guide.savedTop);
    box.className = "guide at-moved";
    return;
  }

  let left;
  let top;
  let side;
  if (isNarrowScreen()) {
    // Docked at the bottom. Extra page padding means nothing is ever stuck behind it.
    side = "dock";
    left = 12;
    top = viewHeight - boxHeight - 12;
    document.body.style.paddingBottom = (boxHeight + 24) + "px";
  } else if (!guide.target) {
    document.body.style.paddingBottom = "";
    side = "center";
    left = (viewWidth - boxWidth) / 2;
    top = (viewHeight - boxHeight) / 2;
  } else {
    document.body.style.paddingBottom = "";
    const rect = guide.target.getBoundingClientRect();
    const step = GUIDE_STEPS[guide.index];
    if (step.place === "below" && rect.bottom + gap + boxHeight < viewHeight) {
      side = "bottom";
      left = rect.left + 24;
      top = rect.bottom + gap;
    } else if (step.place === "top" && rect.top - gap - boxHeight > 60) {
      side = "top";
      left = rect.right - boxWidth;
      top = rect.top - gap - boxHeight;
    } else if (rect.right + gap + boxWidth < viewWidth - 8 && rect.width < viewWidth / 2) {
      side = "right";
      left = rect.right + gap;
      top = Math.max(rect.top, Math.min(rect.top + 8, viewHeight - boxHeight - 8));
    } else if (rect.bottom + gap + boxHeight < viewHeight - 8) {
      side = "bottom";
      left = rect.left;
      top = rect.bottom + gap;
    } else {
      side = "top";
      left = rect.left;
      top = rect.top - gap - boxHeight;
    }
  }
  box.className = "guide at-" + side;
  moveGuideTo(left, top);

  // Point the little arrow at the middle of the target (or its left part if it is wide).
  if (guide.target) {
    const rect = guide.target.getBoundingClientRect();
    const aim = Math.min(rect.left + rect.width / 2, rect.left + 60) - parseFloat(box.style.left) - 5;
    box.style.setProperty("--arrow-x", Math.max(14, Math.min(aim, boxWidth - 24)) + "px");
  }
}

// Move the box, but never past the edges of the window or over the site header.
function moveGuideTo(left, top) {
  const box = guide.box;
  const minTop = $(".site-header").offsetHeight + 8;
  const maxLeft = window.innerWidth - box.offsetWidth - 8;
  const maxTop = Math.max(minTop, window.innerHeight - box.offsetHeight - 8);
  box.style.left = Math.max(8, Math.min(left, maxLeft)) + "px";
  box.style.top = Math.max(minTop, Math.min(top, maxTop)) + "px";
}

/* ---------- Dragging by the header ---------- */

function setupDragging(box) {
  const handle = $(".guide-head", box);

  handle.addEventListener("mousedown", function (event) {
    if (event.button !== 0) return;   // left mouse button only
    event.preventDefault();           // stops text being selected
    startDrag(event.clientX, event.clientY);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", stopDrag);
  });

  handle.addEventListener("touchstart", function (event) {
    const touch = event.touches[0];
    startDrag(touch.clientX, touch.clientY);
    document.addEventListener("touchmove", onTouchMove, { passive: false });
    document.addEventListener("touchend", stopDrag);
  }, { passive: true });
}

function startDrag(x, y) {
  const rect = guide.box.getBoundingClientRect();
  guide.drag = { offsetX: x - rect.left, offsetY: y - rect.top };
  document.body.classList.add("guide-dragging");
}

function dragTo(x, y) {
  if (!guide.drag || !guide.box) return;
  guide.moved = true;
  guide.box.className = "guide at-moved";
  moveGuideTo(x - guide.drag.offsetX, y - guide.drag.offsetY);
  guide.savedLeft = parseFloat(guide.box.style.left);
  guide.savedTop = parseFloat(guide.box.style.top);
}

function onMouseMove(event) {
  dragTo(event.clientX, event.clientY);
}

function onTouchMove(event) {
  event.preventDefault();   // move the box, not the page
  dragTo(event.touches[0].clientX, event.touches[0].clientY);
}

function stopDrag() {
  guide.drag = null;
  document.body.classList.remove("guide-dragging");
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", stopDrag);
  document.removeEventListener("touchmove", onTouchMove);
  document.removeEventListener("touchend", stopDrag);
}

/* ---------- Start-up ---------- */

function setupGuide() {
  $all("[data-start-guide]").forEach(function (button) {
    button.addEventListener("click", startGuide);
  });
  // Examiner buttons outside the tutorial box (e.g. on the start page).
  $all("[data-examiner-toggle]").forEach(function (button) {
    button.addEventListener("click", toggleExaminerMode);
  });
  updateExaminerButtons();

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && guide.box) closeGuide();
  });
  // Opened from another page with the tutorial button. Wait for "load" so the
  // page's own script has finished drawing the diagram first.
  if (new URLSearchParams(window.location.search).get("tutorial") === "1") {
    window.addEventListener("load", function () {
      if ($("#compare-box")) startGuide();
    });
  }
}

document.addEventListener("DOMContentLoaded", setupGuide);
