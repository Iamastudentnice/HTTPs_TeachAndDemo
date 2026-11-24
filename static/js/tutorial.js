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
    target: ".page-header",
    also: ["#diagram"],
    pointers: [
      { to: [".page-header h1"], text: "READ THIS", sides: ["right", "top", "bottom"] },
      { to: ["#diagram .net-row"], text: "Watch how your message travels.", sides: ["top", "bottom"] },
    ],
    place: "right",   // beside the heading, so the heading and the diagram both stay visible
  },
  {
    title: "Try HTTP",
    text: "HTTP sends your information without encryption, so it travels as readable text.",
    todo: "Choose HTTP, press Send message, then press Next Step until the last step.",
    needs: ["http-done"],
    target: "#protocol-toggle",
    pointers: [
      { to: [".plain-terms dd:nth-of-type(1)"], text: "Read how HTTP sends information.", sides: ["right", "top"] },
      { to: ["#player [data-action=start]"], text: "Press here to send your message.", sides: ["top", "right", "bottom"] },
    ],
    also: ["#player [data-action=start]"],
  },
  {
    title: "Look inside a packet",
    text: "Your message travelled in packets. Opening one shows exactly what anyone on the " +
      "network could read.",
    todo: "Select a blue (readable) packet in the Packets sent list or on the diagram.",
    needs: ["inspected-plain"],
    target: "#packet-log-box",
    pointers: [
      { to: ["#diagram .packet.style-plain", "#packet-log li button"], text: "Select this packet to inspect it.", sides: ["top", "right", "bottom", "left"] },
    ],
  },
  {
    title: "Try HTTPS",
    text: "HTTPS encrypts your information while it travels. Encryption scrambles it " +
      "so that only the website can turn it back into readable text.",
    todo: "Switch to HTTPS, press Send message and press Next Step until the last step.",
    needs: ["https-done"],
    target: "#protocol-toggle",
    pointers: [
      { to: [".plain-terms dd:nth-of-type(2)"], text: "Now compare this with HTTPS.", sides: ["right", "top"] },
      { to: ["#protocol-toggle [data-value=HTTPS]"], text: "Switch to HTTPS here.", sides: ["bottom", "top", "right"] },
      { to: ["#player [data-action=start]"], text: "Press here to send your message.", sides: ["top", "right", "bottom"] },
    ],
    also: ["#player [data-action=start]"],
  },
  {
    title: "Compare the results",
    text: "HTTP sends information without encryption. HTTPS protects it while it travels. " +
      "With HTTPS, the network can still see which website you visit, but not what you send.",
    todo: "Compare the two columns. Both need a finished HTTP and HTTPS run.",
    needs: ["http-done", "https-done"],
    target: "#compare-box",
    place: "below",   // keep both columns visible; the note goes underneath
    pointers: [
      { to: ["#compare-http-note"], text: "Compare what each one reveals.", sides: ["right", "top"] },
    ],
  },
  {
    title: "Add an eavesdropper",
    text: "Now see the same thing from the attacker's side: someone on the same Wi-Fi " +
      "watching the connection.",
    todo: "Tick the eavesdropper box, send a message and press Next Step until the last step.",
    needs: ["observer-done"],
    target: "#observer-option",
    pointers: [
      { to: ["#observer-option"], text: "Tick this to add an eavesdropper.", sides: ["bottom", "left", "top"] },
    ],
    place: "top",   // above the checkbox, so the diagram (where the eavesdropper appears) stays visible
  },
];

// Shown when the whole HTTP vs HTTPS lab has been completed.
const LAB_COMPLETE = {
  title: "HTTP vs HTTPS Lab Completed",
  text: "You've seen how HTTP and HTTPS handle information differently.",
  nextName: "The Journey of a Website",
  nextUrl: "/journey",
  nextTeaches: "What happens between pressing Enter and seeing the page, one simple stage at a time.",
};

const WARNING_TEXT = "Please complete this section before moving onto the next!";
const NAV_WARNING_TEXT = "Tutorial active \u2014 complete or skip the tutorial to explore other labs.";

/* ---------- The two pieces of tutorial state ---------- */

// True from the moment the tutorial starts until it is skipped or the lab is completed.
// Hiding the tutorial box does NOT change this.
let tutorialActive = false;

// True after the Examiner button is pressed. Remembered for this browser tab only.
let examinerBypassEnabled = readExaminerSetting();

// The single rule for leaving the page. Examiner bypass always wins.
function navigationIsLocked() {
  return tutorialActive && !examinerBypassEnabled;
}

// The tutorial lives on the HTTP vs HTTPS page (the only page with the comparison box).
function onTutorialPage() {
  return Boolean($("#compare-box"));
}

// Remember the tutorial for this browser tab, so a refresh does not lose progress.
// Only the tutorial page saves, so other labs cannot overwrite it.
function saveTutorialState() {
  if (!onTutorialPage()) return;
  const state = {
    active: tutorialActive,
    step: guide.lastStep,
    events: tutorialEvents,
    completionShown: guide.completionShown,
  };
  try {
    window.sessionStorage.setItem("tutorialState", JSON.stringify(state));
  } catch (error) {
    // Storage blocked: the tutorial still works, it just cannot survive a refresh.
  }
}

function loadTutorialState() {
  try {
    return JSON.parse(window.sessionStorage.getItem("tutorialState"));
  } catch (error) {
    return null;
  }
}

// Reached another page while the tutorial is locked (back button, typed address):
// go straight back to the tutorial, which then shows the usual warning.
function returnToTutorialIfNeeded() {
  if (navigationIsLocked() && !onTutorialPage()) {
    window.location.replace("/?tutorial=1&blocked=1");
  }
}

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
  lastStep: 0,          // the step to return to after hiding or a refresh
};

/* ---------- Completion checks ---------- */

// Called by the lab pages when the learner really does something.
function markTutorialEvent(name) {
  tutorialEvents[name] = true;
  saveTutorialState();
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
  return examinerBypassEnabled || hasDone(GUIDE_STEPS[index].needs);
}

// The lab counts as complete when every step's actions have really happened.
function labIsComplete() {
  return GUIDE_STEPS.every(function (step) { return hasDone(step.needs); });
}

/* ---------- Examiner mode ---------- */

// Saved in sessionStorage so it lasts for this browser tab only; ordinary users start guided.
function readExaminerSetting() {
  try {
    return window.sessionStorage.getItem("examinerMode") === "on";
  } catch (error) {
    return false;   // storage blocked: start guided
  }
}

function setExaminerMode(on) {
  examinerBypassEnabled = on;
  try {
    if (on) window.sessionStorage.setItem("examinerMode", "on");
    else window.sessionStorage.removeItem("examinerMode");
  } catch (error) {
    // Storage blocked: the variable above still works for this page.
  }
  updateExaminerButtons();
  refreshGuideStatus();
  returnToTutorialIfNeeded();
  showToast(on ? "Examiner mode enabled — tutorial restrictions removed."
               : "Guided mode restored — each section must be completed again.");
}

function toggleExaminerMode() {
  setExaminerMode(!examinerBypassEnabled);
}

// Every button with data-examiner-toggle shows the current mode.
function updateExaminerButtons() {
  const on = examinerBypassEnabled;
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
  // Already running: show it again at the same step instead of restarting.
  if (tutorialActive) {
    if (guide.box) showHiddenGuide();
    else showGuideStep(guide.lastStep);
    return;
  }
  tutorialActive = true;
  guide.moved = false;
  showGuideStep(0);
}

// Skip tutorial (after unlocking the padlock): the only normal way to leave early.
function endTutorial() {
  tutorialActive = false;
  saveTutorialState();
  closeGuide();
}

// Hide the box without ending the tutorial. Navigation stays locked.
function hideGuide() {
  if (!guide.box) return;
  guide.box.classList.add("is-hidden");
  updatePointers();   // removes the arrows and shows the "Start here" box again
  document.body.style.paddingBottom = "";
  let tab = $("#guide-restore");
  if (!tab) {
    tab = document.createElement("button");
    tab.id = "guide-restore";
    tab.type = "button";
    tab.className = "btn guide-restore";
    tab.addEventListener("click", showHiddenGuide);
    document.body.appendChild(tab);
  }
  tab.textContent = "Show tutorial \u2014 step " + (guide.index + 1) + " of " + GUIDE_STEPS.length;
  tab.hidden = false;
}

function showHiddenGuide() {
  if (!guide.box) return;
  guide.box.classList.remove("is-hidden");
  const tab = $("#guide-restore");
  if (tab) tab.hidden = true;
  positionGuide();
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
  clearInterval(guide.pointerTimer);
  removePointers();
  document.body.classList.remove("guide-visible");
  const tab = $("#guide-restore");
  if (tab) tab.hidden = true;
  window.removeEventListener("scroll", positionGuide, true);
  window.removeEventListener("resize", positionGuide);
}

function closeGuide() {
  removeGuideBox();
  guide.moved = false;
}

// Create an empty tutorial box with the draggable header and the examiner button.
function buildGuideBox(headerRight, bodyHtml, canHide) {
  const box = document.createElement("div");
  box.className = "guide";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "Learn HTTPS tutorial");
  box.innerHTML =
    '<div class="guide-count guide-head" title="Drag to move"><span>Learn HTTPS</span><span>' + headerRight +
    (canHide ? '<button class="guide-hide" type="button" data-guide="hide">Hide</button>' : "") + "</span></div>" +
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
  guide.lastStep = index;
  saveTutorialState();
  const step = GUIDE_STEPS[index];
  const last = index === GUIDE_STEPS.length - 1;

  const box = buildGuideBox("Step " + (index + 1) + " of " + GUIDE_STEPS.length, 
    '<div class="guide-title">' + escapeHtml(step.title) + "</div>" +
    '<p class="guide-text">' + escapeHtml(step.text) + "</p>" +
    '<p class="guide-todo"><strong>What to do:</strong> ' + escapeHtml(step.todo) + "</p>" +
    '<p class="guide-status" aria-live="polite"></p>' +
    '<p class="guide-warning" role="alert"></p>' +
    '<p class="guide-next-hint">Continue when you have completed this action \u2193</p>' +
    '<div class="guide-controls">' +
    (index > 0 ? '<button class="btn btn-sm" data-guide="back">Back</button>' : "") +
    '<button class="btn btn-sm skip" data-guide="skip">' + skipLabel(false) + "</button>" +
    '<button class="btn btn-sm btn-primary next" data-guide="next">' + (last ? "Finish" : "Next") + "</button>" +
    "</div>", true);

  $all("[data-guide]", box).forEach(function (button) {
    button.addEventListener("click", function () {
      const action = button.dataset.guide;
      if (action === "back") showGuideStep(guide.index - 1);
      else if (action === "hide") hideGuide();
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
  // Keep the user's dragged position, unless it would hide this step's target.
  if (guide.moved && guide.target && boxWouldCover(guide.target)) guide.moved = false;
  positionGuide();
  window.addEventListener("scroll", positionGuide, true);
  window.addEventListener("resize", positionGuide);
  // Packets and panels move while a simulation runs, so re-place the arrows twice a second.
  guide.pointerTimer = setInterval(updatePointers, 500);
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
    endTutorial();
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

  if (examinerBypassEnabled) status.textContent = "Examiner mode: you can move on freely.";
  else if (complete) status.textContent = "✓ Section complete. Press " + next.textContent + " to continue.";
  else status.textContent = "Not complete yet. Do the task above to unlock " + next.textContent + ".";
  status.classList.toggle("is-complete", complete);

  // Only the look changes; the button stays clickable so an early click can show the warning.
  next.classList.toggle("is-locked", !complete);
  $(".guide-next-hint", guide.box).hidden = complete;
  if (complete) {
    $(".guide-warning", guide.box).classList.remove("show");
    clearTimeout(guide.warningTimer);
  }
}

// The end of the lab: say so, and let the learner choose whether to continue.
function showLabComplete() {
  removeGuideBox();
  guide.completionShown = true;
  tutorialActive = false;   // the whole lab is done, so the other labs open again
  saveTutorialState();
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
  if (!box || box.classList.contains("is-hidden")) return;
  const boxWidth = box.offsetWidth;
  const boxHeight = box.offsetHeight;
  const viewWidth = window.innerWidth;
  const viewHeight = window.innerHeight;

  // Once dragged, the box stays where the user put it (kept inside the window).
  if (guide.moved) {
    document.body.style.paddingBottom = "";
    moveGuideTo(guide.savedLeft, guide.savedTop);
    box.className = "guide at-moved";
    updatePointers();
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
    const spot = chooseGuideSpot(guide.target.getBoundingClientRect(), boxWidth, boxHeight);
    side = spot.side;
    left = spot.left;
    top = spot.top;
  }
  box.className = "guide at-" + side;
  moveGuideTo(left, top);

  // Point the little arrow at the middle of the target (or its left part if it is wide).
  if (guide.target) {
    const rect = guide.target.getBoundingClientRect();
    const aim = Math.min(rect.left + rect.width / 2, rect.left + 60) - parseFloat(box.style.left) - 5;
    box.style.setProperty("--arrow-x", Math.max(14, Math.min(aim, boxWidth - 24)) + "px");
  }
  updatePointers();
}

// True if two rectangles overlap.
function rectsOverlap(a, b) {
  return !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
}

// Work out where the tutorial box should go. Every candidate is scored by what it would hide:
// the step's own target (very bad), the controls this step needs (bad), anything else clickable
// (a little). The cheapest wins; ties go to the step's preferred side, then to spots beside
// the target rather than at the window edge.
function chooseGuideSpot(targetRect, boxWidth, boxHeight) {
  const gap = 14;
  const minTop = $(".site-header").offsetHeight + 8;
  const step = GUIDE_STEPS[guide.index];
  const sidebar = $("#sidebar");
  const leftEdge = isVisible(sidebar) ? sidebar.getBoundingClientRect().right + 8 : 8;
  const rightEdge = window.innerWidth - boxWidth - 16;
  const bottomEdge = window.innerHeight - boxHeight - 16;
  const middle = (minTop + bottomEdge) / 2;

  const candidates = [];
  // Beside the target (only worth trying while the target is on screen).
  const targetOnScreen = targetRect.bottom > minTop && targetRect.top < window.innerHeight;
  if (targetOnScreen) {
    candidates.push({ side: "right", left: targetRect.right + gap, top: targetRect.top });
    candidates.push({ side: "bottom", left: targetRect.left, top: targetRect.bottom + gap });
    candidates.push({ side: "left", left: targetRect.left - gap - boxWidth, top: targetRect.top });
    candidates.push({ side: "top", left: targetRect.right - boxWidth, top: targetRect.top - gap - boxHeight });
  }
  // Along the left and right edges of the window.
  [rightEdge, leftEdge].forEach(function (left) {
    [bottomEdge, minTop, middle].forEach(function (top) {
      candidates.push({ side: "corner", left: left, top: top });
    });
  });

  // The controls this step needs: what it highlights, what its arrows point at,
  // and the simulation's Send / Next Step buttons.
  const needed = [step.target].concat(step.also || []);
  (step.pointers || []).forEach(function (pointer) { needed.push.apply(needed, pointer.to); });
  needed.push("#player [data-action=start]", "#player [data-action=next]");
  const neededRects = needed.map(function (selector) { return $(selector); })
    .filter(isVisible)
    .map(function (element) { return element.getBoundingClientRect(); });
  const otherRects = $all("button, a, input, textarea, select, .packet, .net-node")
    .filter(function (element) { return isVisible(element) && !guide.box.contains(element); })
    .map(function (element) { return element.getBoundingClientRect(); });

  let best = null;
  let lowestCost = Infinity;
  candidates.forEach(function (candidate) {
    // Keep every candidate inside the window, exactly as moveGuideTo will.
    const left = Math.max(8, Math.min(candidate.left, window.innerWidth - boxWidth - 8));
    const top = Math.max(minTop, Math.min(candidate.top, window.innerHeight - boxHeight - 8));
    const area = { left: left, top: top, right: left + boxWidth, bottom: top + boxHeight };

    let cost = 0;
    if (rectsOverlap(area, targetRect)) cost += 1000;
    neededRects.forEach(function (rect) { if (rectsOverlap(area, rect)) cost += 20; });
    otherRects.forEach(function (rect) { if (rectsOverlap(area, rect)) cost += 1; });
    if (candidate.side === "corner") cost += 0.5;                         // prefer beside the target
    if (step.place && candidate.side !== placeToSide(step.place)) cost += 0.25;

    if (cost < lowestCost) {
      lowestCost = cost;
      best = { side: candidate.side, left: left, top: top };
    }
  });
  return best;
}

// The steps say "below" for the bottom side; everything else uses the side's own name.
function placeToSide(place) {
  return place === "below" ? "bottom" : place;
}

// True if the box, at the position the user dragged it to, would overlap the element.
function boxWouldCover(element) {
  const target = element.getBoundingClientRect();
  const left = guide.savedLeft;
  const top = guide.savedTop;
  const right = left + guide.box.offsetWidth;
  const bottom = top + guide.box.offsetHeight;
  return !(right <= target.left || left >= target.right || bottom <= target.top || top >= target.bottom);
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

/* ---------- Blocking navigation while the tutorial is active ---------- */

// Click listener for the whole page: stop any link while navigation is locked.
function blockNavigationIfLocked(event) {
  const link = event.target.closest("a[href]");
  if (!link || !navigationIsLocked()) return;
  event.preventDefault();
  event.stopPropagation();
  showNavigationWarning();
}

// Shake the page and show one corner notification. Repeat clicks within the
// cooldown are ignored, so warnings never stack and shakes never overlap.
let lastNavigationWarning = 0;
let navigationWarningTimer = null;
function showNavigationWarning() {
  const now = Date.now();
  if (now - lastNavigationWarning < 1200) return;
  lastNavigationWarning = now;

  const main = $(".main");
  main.classList.remove("nav-shake");
  void main.offsetWidth;          // lets the same animation play again
  main.classList.add("nav-shake");

  let note = $("#nav-warning");
  if (!note) {
    note = document.createElement("div");
    note.id = "nav-warning";
    note.className = "nav-warning";
    note.setAttribute("role", "alert");
    document.body.appendChild(note);
  }
  note.textContent = NAV_WARNING_TEXT;
  note.classList.add("show");
  clearTimeout(navigationWarningTimer);
  navigationWarningTimer = setTimeout(function () { note.classList.remove("show"); }, 2500);
}

/* ---------- Small arrows that point at what to read or press ---------- */

function removePointers() {
  $all(".tut-pointer").forEach(function (pointer) { pointer.remove(); });
  $all(".pointer-fallback").forEach(function (element) { element.classList.remove("pointer-fallback"); });
}

// Draw the current step's arrows. Called on scroll, resize, drag and twice a second.
function updatePointers() {
  removePointers();
  const showing = guide.box && guide.index >= 0 && !guide.box.classList.contains("is-hidden");
  // The "Start here" box is not needed while the tutorial is on screen; hiding it gives arrows room.
  document.body.classList.toggle("guide-visible", Boolean(guide.box) && !guide.box.classList.contains("is-hidden"));
  if (!showing) return;
  const step = GUIDE_STEPS[guide.index];
  (step.pointers || []).forEach(function (pointer) {
    const target = pointer.to.map(function (selector) { return $(selector); }).find(isVisible);
    if (target) placePointer(target, pointer.text, pointer.sides);
  });
}

// Things an arrow must never cover.
const POINTER_OBSTACLES = "h1, h2, h3, p, dt, dd, label, button, a, input, textarea, select, pre, li, " +
  ".tag, .packet, .net-node, .diagram-caption, .diagram-hint, .output-label, .guide, .tut-pointer";

// For text, measure the words themselves rather than the whole (often much wider) box.
function obstacleRect(element) {
  if (element.matches("p, dt, dd, label, li, h1, h2, h3, .output-label")) {
    const range = document.createRange();
    range.selectNodeContents(element);
    const rect = range.getBoundingClientRect();
    if (rect.width > 0) return rect;
  }
  return element.getBoundingClientRect();
}

// Try each side in order and use the first spot that is on screen and covers nothing.
function placePointer(target, text, sides) {
  const pointer = document.createElement("div");
  pointer.className = "tut-pointer";
  document.body.appendChild(pointer);

  const goal = target.getBoundingClientRect();
  const minTop = $(".site-header").offsetHeight + 4;
  const obstacles = $all(POINTER_OBSTACLES)
    .filter(function (element) {
      return element !== pointer && isVisible(element) && !element.contains(target) && !target.contains(element);
    })
    .map(obstacleRect);

  // Try every side on one line first, then wrapped onto a narrower label. On each side the
  // label can be centred on the target or lined up with either of its edges.
  const attempts = [];
  ["none", "150px"].forEach(function (width) {
    sides.forEach(function (side) {
      ["middle", "start", "end"].forEach(function (align) {
        attempts.push({ side: side, width: width, align: align });
      });
    });
  });

  for (let i = 0; i < attempts.length; i++) {
    const side = attempts[i].side;
    const align = attempts[i].align;
    pointer.style.maxWidth = attempts[i].width;
    // The arrow always points from the label towards the target.
    const arrows = { right: "\u2190 ", left: "", top: "", bottom: "\u2191 " };
    const endings = { right: "", left: " \u2192", top: " \u2193", bottom: "" };
    pointer.textContent = arrows[side] + text + endings[side];
    const width = pointer.offsetWidth;
    const height = pointer.offsetHeight;

    let left;
    let top;
    if (side === "right" || side === "left") {
      left = side === "right" ? goal.right + 8 : goal.left - 8 - width;
      if (align === "middle") top = goal.top + goal.height / 2 - height / 2;
      if (align === "start") top = goal.top;
      if (align === "end") top = goal.bottom - height;
    } else {
      top = side === "top" ? goal.top - 4 - height : goal.bottom + 4;
      if (align === "middle") left = goal.left + goal.width / 2 - width / 2;
      if (align === "start") left = goal.left;
      if (align === "end") left = goal.right - width;
    }

    const spot = { left: left, top: top, right: left + width, bottom: top + height };
    const onScreen = spot.left >= 4 && spot.right <= window.innerWidth - 4 && spot.top >= minTop && spot.bottom <= window.innerHeight - 4;
    const free = obstacles.every(function (rect) {
      return rect.right <= spot.left || rect.left >= spot.right || rect.bottom <= spot.top || rect.top >= spot.bottom;
    });
    if (onScreen && free) {
      pointer.style.left = left + "px";
      pointer.style.top = top + "px";
      pointer.classList.add("at-" + side);
      return true;
    }
  }
  // Nowhere free: rather than cover something, outline the element itself instead.
  pointer.remove();
  target.classList.add("pointer-fallback");
  return false;
}

/* ---------- Dragging by the header ---------- */

function setupDragging(box) {
  const handle = $(".guide-head", box);

  handle.addEventListener("mousedown", function (event) {
    if (event.button !== 0) return;              // left mouse button only
    if (event.target.closest("button")) return;  // the Hide button is a button, not a handle
    event.preventDefault();           // stops text being selected
    startDrag(event.clientX, event.clientY);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", stopDrag);
  });

  handle.addEventListener("touchstart", function (event) {
    if (event.target.closest("button")) return;
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
  updatePointers();
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

  // Escape hides the tutorial (it does not end it). Leave it alone while a packet window is open.
  // "true" = capture phase: this runs before the packet window's own Escape handler closes it.
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || !guide.box || $("#modal.open")) return;
    if (tutorialActive) hideGuide();
    else closeGuide();   // the "lab complete" message
  }, true);

  // One listener for every link on the page (sidebar, header, cards...). It runs in the
  // capture phase, so it sees the click before the browser follows the link.
  document.addEventListener("click", blockNavigationIfLocked, true);
  document.addEventListener("auxclick", blockNavigationIfLocked, true);   // middle-click

  // Pick up a tutorial that was running before a refresh or a page change.
  const saved = loadTutorialState();
  if (saved && saved.active) {
    tutorialActive = true;
    if (onTutorialPage()) {
      Object.assign(tutorialEvents, saved.events || {});
      guide.completionShown = Boolean(saved.completionShown);
      guide.lastStep = Math.min(Math.max(Number(saved.step) || 0, 0), GUIDE_STEPS.length - 1);
    }
  }
  returnToTutorialIfNeeded();

  // Wait for "load" so the page's own script has finished drawing the diagram first.
  const params = new URLSearchParams(window.location.search);
  window.addEventListener("load", function () {
    if (!onTutorialPage()) return;
    if (tutorialActive) showGuideStep(guide.lastStep);
    else if (params.get("tutorial") === "1") startGuide();
    // Sent back here from another page while locked.
    if (params.get("blocked") === "1" && navigationIsLocked()) showNavigationWarning();
    // Tidy the address bar, so a later refresh does not start the tutorial again.
    if (params.has("tutorial") || params.has("blocked")) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  });
}

document.addEventListener("DOMContentLoaded", setupGuide);
