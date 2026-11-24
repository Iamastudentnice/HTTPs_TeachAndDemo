/* interactions.js - shared frontend code used by every page. */

"use strict";

/* Talking to the Flask backend */

// Send JSON to a Flask API route and return the JSON reply.
async function apiPost(url, data) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {}),
  });
  if (!response.ok) {
    throw new Error("Server returned " + response.status);
  }
  return response.json();
}

// GET a Flask API route and return the JSON reply.
async function apiGet(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Server returned " + response.status);
  }
  return response.json();
}

/* Small DOM helpers */

function $(selector, root) {
  return (root || document).querySelector(selector);
}

function $all(selector, root) {
  return Array.from((root || document).querySelectorAll(selector));
}

// Make text safe to insert into HTML.
function escapeHtml(text) {
  return String(text === undefined || text === null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Return the HTML for one icon from the sprite in base.html.
function iconSvg(name, extraClass) {
  return '<svg class="icon ' + (extraClass || "") + '"><use href="#i-' + name + '"/></svg>';
}

// Colour names used for packet styles -> human readable tags.
const STYLE_TAGS = {
  plain: '<span class="tag tag-blue">' + iconSvg("unlock") + " Unencrypted</span>",
  encrypted: '<span class="tag tag-green">' + iconSvg("lock") + " Encrypted</span>",
  malicious: '<span class="tag tag-red">' + iconSvg("attacker") + " Intercepted / malicious</span>",
  warning: '<span class="tag tag-yellow">' + iconSvg("warning") + " Suspicious</span>",
};

// Show an error message inside a container.
function showError(container, message) {
  container.innerHTML = '<div class="callout danger"><strong>Something went wrong.</strong> ' +
    escapeHtml(message) + "</div>";
}

/* Mobile sidebar */

// Open/close the sidebar on phones.
function setupSidebar() {
  const sidebar = $("#sidebar");
  const overlay = $("#overlay");
  const button = $("#menu-button");
  if (!sidebar || !button) return;

  function close() {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
  }
  button.addEventListener("click", function () {
    sidebar.classList.add("open");
    overlay.classList.add("open");
  });
  overlay.addEventListener("click", close);
}

/* Progress tracking (stored by Python in the Flask session) */

// Update the progress bar and tick marks in the sidebar.
function updateSidebarProgress(progress) {
  const percent = $("#sidebar-percent");
  const bar = $("#sidebar-bar");
  if (percent) percent.textContent = progress.percent + "%";
  if (bar) bar.style.width = progress.percent + "%";

  progress.modules.forEach(function (module) {
    const status = $('.nav a[data-module="' + module.slug + '"] .status');
    if (!status) return;
    status.className = "status" + (module.complete ? " done" : module.done > 0 ? " partial" : "");
    status.title = module.done + " of " + module.total + " activities";
    status.innerHTML = module.complete ? '<svg><use href="#i-check"/></svg>' : "";
  });
}

// Tell Python an activity was completed, then refresh the sidebar.
async function recordProgress(module, activity) {
  try {
    const result = await apiPost("/api/progress/record", { module: module, activity: activity });
    updateSidebarProgress(result.progress);
  } catch (error) {
    console.warn("Could not record progress", error);
  }
}

// Re-read progress from Python and refresh the sidebar.
async function refreshProgress() {
  try {
    updateSidebarProgress(await apiGet("/api/progress"));
  } catch (error) {
    console.warn("Could not refresh progress", error);
  }
}

/* Modal window (used for packet details) */

// Open the pop-up window with a title and content.
function openModal(title, tagHtml, bodyHtml) {
  $("#modal-title").textContent = title;
  $("#modal-tag").innerHTML = tagHtml || "";
  $("#modal-body").innerHTML = bodyHtml;
  $("#modal").classList.add("open");
  $("#modal-close").focus();
}

// Close the pop-up window.
function closeModal() {
  $("#modal").classList.remove("open");
}

// Close the pop-up on the X button, a backdrop click or Escape.
function setupModal() {
  const modal = $("#modal");
  if (!modal) return;
  $("#modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", function (event) {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeModal();
  });
}

// Turn a {name: value} object into an HTML table.
function detailsTable(details) {
  let rows = "";
  Object.keys(details || {}).forEach(function (key) {
    rows += "<tr><th>" + escapeHtml(key) + "</th><td>" + escapeHtml(details[key]) + "</td></tr>";
  });
  return rows ? '<table class="kv">' + rows + "</table>" : "";
}

// Show a packet's details in the pop-up window.
function showPacketDetails(packet, nodeNames) {
  const fromName = (nodeNames && nodeNames[packet.from]) || packet.from;
  const toName = (nodeNames && nodeNames[packet.to]) || packet.to;
  let body = '<p class="muted small">' + escapeHtml(fromName) + " → " + escapeHtml(toName) +
    " · simulated packet generated by Python</p>";
  body += detailsTable(packet.details);
  if (packet.payload) {
    const outputClass = packet.style === "encrypted" ? "cipher" : packet.style === "malicious" ? "danger" : "plain";
    body += '<div class="output-label">Payload</div><pre class="output ' + outputClass + '">' +
      escapeHtml(packet.payload) + "</pre>";
  }
  openModal(packet.label, STYLE_TAGS[packet.style] || "", body);
}

/* Tabs */

// Make tab buttons switch between tab panels.
function setupTabs(root, onChange) {
  const buttons = $all(".tabs button[data-tab]", root);
  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      buttons.forEach(function (other) { other.classList.toggle("active", other === button); });
      $all(".tab-panel", root).forEach(function (panel) {
        panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab);
      });
      if (onChange) onChange(button.dataset.tab);
    });
  });
}

/* Segmented button groups: returns a function that reads the selected value. */
function setupSegmented(group, onChange) {
  const buttons = $all("button[data-value]", group);
  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      buttons.forEach(function (other) { other.classList.toggle("active", other === button); });
      if (onChange) onChange(button.dataset.value);
    });
  });
  return function () {
    const active = buttons.find(function (button) { return button.classList.contains("active"); });
    return active ? active.dataset.value : null;
  };
}

/* NetworkDiagram - draws devices left-to-right and animates packets. */

class NetworkDiagram {
  constructor(container) {
    this.container = container;
    this.nodes = [];
    this.links = [];
    this.packetElement = null;
    this.parked = null;       // the packet currently resting at its destination
    this.animation = null;
    this.onPacketClick = null;

    const diagram = this;
    window.addEventListener("resize", function () { diagram.layout(); });
  }

  /* Build the devices and connection lines from the node list Python sent. */
  setNodes(nodes, extraLinks) {
    this.cancelAnimation();
    this.nodes = nodes;
    this.links = [];
    this.container.innerHTML = "";
    this.container.classList.toggle("has-top-lane", Boolean(extraLinks && extraLinks.length));

    const row = document.createElement("div");
    row.className = "net-row";
    const diagram = this;

    nodes.forEach(function (node) {
      const element = document.createElement("div");
      element.className = "net-node role-" + node.role;
      element.dataset.node = node.id;
      element.innerHTML =
        '<div class="net-icon"><svg><use href="#i-' + node.icon + '"/></svg>' +
        '<span class="net-badge"></span></div>' +
        '<div class="net-label">' + escapeHtml(node.label) + "</div>" +
        '<div class="net-sublabel">' + escapeHtml(node.sublabel) + "</div>";
      row.appendChild(element);
      node.element = element;
    });
    this.container.appendChild(row);

    // Main horizontal links between each pair of neighbouring nodes.
    for (let index = 0; index < nodes.length - 1; index++) {
      this.addLink(nodes[index].id, nodes[index + 1].id, "main", "");
    }
    (extraLinks || []).forEach(function (link) {
      diagram.addLink(link.from, link.to, "top", link.label || "");
    });

    const hint = document.createElement("div");
    hint.className = "diagram-hint";
    hint.textContent = "Tip: click a packet to inspect it";
    this.container.appendChild(hint);

    // Wait one frame so the browser has measured the nodes before drawing lines.
    requestAnimationFrame(function () { diagram.layout(); });
  }

  // Create one connection line between two devices.
  addLink(fromId, toId, lane, label) {
    const element = document.createElement("div");
    element.className = "net-link" + (lane === "top" ? " lane-top" : "");
    element.innerHTML = '<span class="link-arrow"></span>' +
      (label ? '<span class="lane-label">' + escapeHtml(label) + "</span>" : "");
    this.container.appendChild(element);
    this.links.push({ from: fromId, to: toId, lane: lane, element: element });
  }

  // Position of a device in the row (0 = leftmost).
  nodeIndex(nodeId) {
    return this.nodes.findIndex(function (node) { return node.id === nodeId; });
  }

  // Map of device id -> display name.
  nodeNames() {
    const names = {};
    this.nodes.forEach(function (node) { names[node.id] = node.label; });
    return names;
  }

  /* Measure where each icon is and position the connection lines between them. */
  layout() {
    if (!this.nodes.length) return;
    const box = this.container.getBoundingClientRect();
    const diagram = this;

    this.links.forEach(function (link) {
      const fromIcon = $(".net-icon", diagram.nodes[diagram.nodeIndex(link.from)].element).getBoundingClientRect();
      const toIcon = $(".net-icon", diagram.nodes[diagram.nodeIndex(link.to)].element).getBoundingClientRect();
      const style = link.element.style;

      if (link.lane === "top") {
        const fromCentre = fromIcon.left + fromIcon.width / 2 - box.left;
        const toCentre = toIcon.left + toIcon.width / 2 - box.left;
        link.x1 = fromCentre;
        link.x2 = toCentre;
        link.y = fromIcon.top - box.top - 34;
        style.left = fromCentre + "px";
        style.width = (toCentre - fromCentre) + "px";
        style.top = link.y + "px";
        style.height = "30px";
      } else {
        link.x1 = fromIcon.right - box.left + 8;
        link.x2 = toIcon.left - box.left - 8;
        link.y = fromIcon.top + fromIcon.height / 2 - box.top - 2;
        style.left = link.x1 + "px";
        style.width = Math.max(0, link.x2 - link.x1) + "px";
        style.top = link.y + "px";
      }
    });

    // Keep a resting packet in the right place after the window is resized.
    if (this.parked && this.packetElement && !this.isAnimating()) {
      const geometry = this.packetGeometry(this.parked.path, this.parked.direction);
      this.packetElement.style.top = geometry.y + "px";
      this.packetElement.style.transform = "translateX(" + geometry.endX + "px)";
    }
  }

  /* Which links does a packet travel along to get from one node to another? */
  findPath(fromId, toId, route) {
    if (route === "direct") {
      return this.links.filter(function (link) {
        return link.lane === "top" &&
          ((link.from === fromId && link.to === toId) || (link.from === toId && link.to === fromId));
      });
    }
    const fromIndex = this.nodeIndex(fromId);
    const toIndex = this.nodeIndex(toId);
    const low = Math.min(fromIndex, toIndex);
    const high = Math.max(fromIndex, toIndex);
    return this.links.filter(function (link) {
      if (link.lane !== "main") return false;
      const linkIndex = Math.min(this.nodeIndex(link.from), this.nodeIndex(link.to));
      return linkIndex >= low && linkIndex < high;
    }, this);
  }

  /* Start/end x positions and the y position for a packet on a path. */
  packetGeometry(path, direction) {
    const width = this.packetElement ? this.packetElement.offsetWidth : 120;
    const height = this.packetElement ? this.packetElement.offsetHeight : 26;
    const left = Math.min.apply(null, path.map(function (link) { return link.x1; }));
    const right = Math.max.apply(null, path.map(function (link) { return link.x2; }));
    const y = path[0].y - height / 2 + (path[0].lane === "top" ? 0 : 2);

    // Keep the packet inside the diagram even on narrow screens.
    const maxX = this.container.clientWidth - width - 4;
    let startX = direction === "right" ? left : right - width;
    let endX = direction === "right" ? right - width : left;
    startX = Math.max(4, Math.min(startX, maxX));
    endX = Math.max(4, Math.min(endX, maxX));
    return { startX: startX, endX: endX, y: y };
  }

  /* Colour the lines a packet uses and show an arrow for its direction. */
  colourPath(packet) {
    const path = this.findPath(packet.from, packet.to, packet.route);
    const direction = this.nodeIndex(packet.from) < this.nodeIndex(packet.to) ? "right" : "left";
    path.forEach(function (link) {
      link.element.classList.remove("link-plain", "link-encrypted", "link-malicious", "link-warning", "dir-left", "dir-right");
      link.element.classList.add("link-" + packet.style, "dir-" + direction);
      $(".link-arrow", link.element).textContent = direction === "right" ? "▶" : "◀";
    });
    return { path: path, direction: direction };
  }

  /* Draw a packet and (optionally) animate it. */
  showPacket(packet, animate, duration) {
    this.removePacket();
    const route = this.colourPath(packet);
    if (!route.path.length) return Promise.resolve();

    const element = document.createElement("button");
    element.type = "button";
    element.className = "packet style-" + packet.style;
    const lockIcon = packet.style === "encrypted" ? "lock" : packet.style === "malicious" ? "attacker" :
      packet.style === "warning" ? "warning" : "unlock";
    const arrow = route.direction === "right" ? " →" : "← ";
    element.innerHTML = (route.direction === "left" ? arrow : "") +
      '<svg><use href="#i-' + lockIcon + '"/></svg><span class="label">' + escapeHtml(packet.label) +
      "</span>" + (route.direction === "right" ? arrow : "");
    element.title = "Click to inspect this packet";
    const diagram = this;
    element.addEventListener("click", function () {
      showPacketDetails(packet, diagram.nodeNames());
    });

    this.container.appendChild(element);
    this.packetElement = element;
    this.parked = { packet: packet, path: route.path, direction: route.direction };

    const geometry = this.packetGeometry(route.path, route.direction);
    element.style.top = geometry.y + "px";

    if (!animate) {
      element.style.transform = "translateX(" + geometry.endX + "px)";
      element.classList.add("parked");
      return Promise.resolve();
    }

    // The Web Animations API lets us pause and resume mid-flight.
    this.animation = element.animate(
      [
        { transform: "translateX(" + geometry.startX + "px)", opacity: 0.2 },
        { transform: "translateX(" + (geometry.startX + (geometry.endX - geometry.startX) * 0.08) + "px)", opacity: 1, offset: 0.08 },
        { transform: "translateX(" + geometry.endX + "px)", opacity: 1 },
      ],
      { duration: duration, easing: "ease-in-out", fill: "forwards" }
    );
    return this.animation.finished.then(function () {
      element.style.transform = "translateX(" + geometry.endX + "px)";
      element.classList.add("parked");
    }).catch(function () { /* animation was cancelled - that's fine */ });
  }

  // True while a packet is moving.
  isAnimating() {
    return Boolean(this.animation && this.animation.playState === "running");
  }

  // Pause the animation.
  pause() {
    if (this.animation && this.animation.playState === "running") this.animation.pause();
  }

  // Continue after a pause.
  resume() {
    if (this.animation && this.animation.playState === "paused") this.animation.play();
  }

  // Stop the current packet animation.
  cancelAnimation() {
    if (this.animation) {
      this.animation.cancel();
      this.animation = null;
    }
  }

  // Remove the packet from the diagram.
  removePacket() {
    this.cancelAnimation();
    if (this.packetElement) this.packetElement.remove();
    this.packetElement = null;
    this.parked = null;
  }

  // Colour each device (active, secure, danger, warning, inactive).
  setHighlights(highlights) {
    this.nodes.forEach(function (node) {
      node.element.classList.remove("state-active", "state-secure", "state-danger", "state-warning", "state-inactive");
      const state = highlights ? highlights[node.id] : null;
      if (state) node.element.classList.add("state-" + state);
      const badge = $(".net-badge", node.element);
      if (state === "secure") badge.innerHTML = '<svg><use href="#i-lock"/></svg>';
      else if (state === "danger") badge.innerHTML = "!";
      else if (state === "warning") badge.innerHTML = '<svg><use href="#i-warning"/></svg>';
      else badge.innerHTML = "";
    });
  }

  /* Back to grey lines, no highlights, no packet. */
  resetVisuals() {
    this.removePacket();
    this.setHighlights({});
    this.links.forEach(function (link) {
      link.element.classList.remove("link-plain", "link-encrypted", "link-malicious", "link-warning", "dir-left", "dir-right");
    });
  }
}

/* StepPlayer - plays a list of steps with full user control. */

const SPEEDS = {
  slow: { move: 2800, dwell: 3600 },
  normal: { move: 1900, dwell: 2600 },
  fast: { move: 1100, dwell: 1500 },
};

class StepPlayer {
  /* options: diagram      - a NetworkDiagram mount        - element where the controls are built logElement   - optional element for the clickable packet log loadSteps    - async function returning {nodes, steps, extra_links} from Python onStep       - function(step, index, panels) for page-specific panels onFinish     - function() called once when the last step completes onReset      - function() called after Reset startLabel   - text for the start button introTitle / introText - shown before the simulation starts */
  constructor(options) {
    this.diagram = options.diagram;
    this.mount = options.mount;
    this.logElement = options.logElement || null;
    this.loadSteps = options.loadSteps;
    this.onStep = options.onStep || function () {};
    this.onFinish = options.onFinish || function () {};
    this.onReset = options.onReset || function () {};
    this.startLabel = options.startLabel || "Start Simulation";
    this.introTitle = options.introTitle || "Ready when you are";
    this.introText = options.introText || "Press Start Simulation to begin.";

    this.steps = [];
    this.originalSteps = [];
    this.index = -1;
    this.playing = false;
    this.stepDone = false;
    this.finished = false;
    this.loading = false;
    this.timer = null;
    this.token = 0;     // increases every time we jump, so old timers are ignored

    this.buildControls();
    this.showIntro();
    this.updateButtons();
  }

  // Create the Start/Pause/Resume/Previous/Next/Replay/Reset buttons.
  buildControls() {
    this.mount.innerHTML =
      '<div class="step-progress"><span class="step-counter">Not started</span><div class="step-dots"></div></div>' +
      '<div class="step-panel intro" aria-live="polite"><div class="step-title"></div><p class="step-text"></p><div class="choice-row"></div></div>' +
      '<div class="player">' +
      '  <div class="btn-group">' +
      '    <button class="btn btn-primary" data-action="start">' + iconSvg("play") + " " + escapeHtml(this.startLabel) + "</button>" +
      '    <button class="btn" data-action="pause">' + iconSvg("pause") + " Pause</button>" +
      '    <button class="btn" data-action="resume">' + iconSvg("play") + " Resume</button>" +
      '    <button class="btn" data-action="prev">' + iconSvg("prev") + " Previous</button>" +
      '    <button class="btn" data-action="next">Next ' + iconSvg("next") + "</button>" +
      '    <button class="btn" data-action="replay">' + iconSvg("replay") + " Replay</button>" +
      '    <button class="btn" data-action="reset">' + iconSvg("stop") + " Reset</button>" +
      "  </div>" +
      '  <label class="speed">Speed <select data-action="speed">' +
      '    <option value="slow">Slow</option><option value="normal" selected>Normal</option><option value="fast">Fast</option>' +
      "  </select></label>" +
      "</div>";

    this.counter = $(".step-counter", this.mount);
    this.dots = $(".step-dots", this.mount);
    this.panel = $(".step-panel", this.mount);
    this.titleElement = $(".step-title", this.mount);
    this.textElement = $(".step-text", this.mount);
    this.choiceRow = $(".choice-row", this.mount);
    this.speedSelect = $('select[data-action="speed"]', this.mount);
    this.buttons = {};

    const player = this;
    $all("button[data-action]", this.mount).forEach(function (button) {
      player.buttons[button.dataset.action] = button;
      button.addEventListener("click", function () { player[button.dataset.action](); });
    });
  }

  // Current animation timings from the speed selector.
  speed() {
    return SPEEDS[this.speedSelect.value] || SPEEDS.normal;
  }

  // Show the text displayed before the simulation starts.
  showIntro() {
    this.panel.classList.add("intro");
    this.titleElement.textContent = this.introTitle;
    this.textElement.textContent = this.introText;
    this.choiceRow.innerHTML = "";
    this.counter.textContent = "Not started";
    this.dots.innerHTML = "";
    if (this.logElement) this.logElement.innerHTML = '<li class="muted small">Packets will appear here as the simulation runs.</li>';
  }

  /* ---------------- Control actions ---------------- */

  // Fetch the steps from Python and start playing.
  async start() {
    if (this.loading) return;
    this.loading = true;
    this.updateButtons();
    try {
      const data = await this.loadSteps();
      this.diagram.setNodes(data.nodes, data.extra_links);
      this.steps = data.steps;
      this.originalSteps = data.steps.slice();
      this.finished = false;
      this.playing = true;
      this.loading = false;
      // Give the diagram one frame to lay out before the first packet moves.
      const player = this;
      requestAnimationFrame(function () { player.goTo(0, true); });
    } catch (error) {
      this.loading = false;
      this.titleElement.textContent = "Could not start the simulation";
      this.textElement.textContent = error.message;
      this.updateButtons();
    }
  }

  // Pause the animation.
  pause() {
    this.playing = false;
    clearTimeout(this.timer);
    this.diagram.pause();
    this.updateButtons();
  }

  // Continue after a pause.
  resume() {
    if (!this.steps.length || this.finished) return;
    this.playing = true;
    if (this.stepDone) {
      this.afterStep();
    } else {
      this.diagram.resume();
    }
    this.updateButtons();
  }

  // Go to the next step.
  next() {
    if (this.index < this.steps.length - 1 && !this.waitingForChoice()) {
      this.playing = false;
      this.goTo(this.index + 1, true);
    }
  }

  // Go to the previous step.
  prev() {
    if (this.index > 0) {
      this.playing = false;
      this.finished = false;
      this.goTo(this.index - 1, true);
    }
  }

  // Play the simulation again from the first step.
  replay() {
    if (!this.originalSteps.length) return;
    this.steps = this.originalSteps.slice();
    this.finished = false;
    this.playing = true;
    this.goTo(0, true);
  }

  // Stop and clear the simulation.
  reset() {
    this.token += 1;
    clearTimeout(this.timer);
    this.diagram.resetVisuals();
    this.steps = [];
    this.originalSteps = [];
    this.index = -1;
    this.playing = false;
    this.finished = false;
    this.stepDone = false;
    this.showIntro();
    this.onReset();
    this.updateButtons();
  }

  speedChanged() { /* speed is read fresh for every step */ }

  /* The user picked an option at a decision point (e.g. a certificate warning). */
  choose(choiceId) {
    const step = this.steps[this.index];
    if (!step || !step.branches || !step.branches[choiceId]) return;
    step.chosen = choiceId;
    this.steps = this.steps.slice(0, this.index + 1).concat(step.branches[choiceId]);
    this.playing = true;
    this.goTo(this.index + 1, true);
  }

  // True if the current step is waiting for the user to decide.
  waitingForChoice() {
    const step = this.steps[this.index];
    return Boolean(step && step.choices && !step.chosen);
  }

  /* ---------------- Core: show one step ---------------- */

  // Show one step: rebuild earlier state, then animate this step.
  goTo(index, animate) {
    if (index < 0 || index >= this.steps.length) return;
    this.token += 1;
    const myToken = this.token;
    clearTimeout(this.timer);
    this.index = index;
    this.stepDone = false;
    const step = this.steps[index];

    // Rebuild the state of earlier steps instantly (line colours), so that
    // Previous / jumping works exactly like watching from the start.
    this.diagram.resetVisuals();
    const panels = {};
    for (let earlier = 0; earlier <= index; earlier++) {
      const earlierStep = this.steps[earlier];
      if (earlier < index && earlierStep.packet) this.diagram.colourPath(earlierStep.packet);
      Object.assign(panels, earlierStep.panels || {});
    }
    this.diagram.setHighlights(step.highlight);

    this.renderStep(step, index);
    this.onStep(step, index, panels);

    const duration = this.speed().move;
    const arrival = step.packet ? this.diagram.showPacket(step.packet, animate, duration) : Promise.resolve();
    const player = this;
    arrival.then(function () {
      if (myToken !== player.token) return;   // the user jumped elsewhere meanwhile
      player.stepDone = true;
      player.afterStep();
    });
    this.updateButtons();
  }

  /* Decide what to do once a step's animation has finished. */
  afterStep() {
    const step = this.steps[this.index];
    if (step.choices && !step.chosen) {
      this.playing = false;
      this.updateButtons();
      return;
    }
    if (this.index >= this.steps.length - 1) {
      this.finish();
      return;
    }
    if (this.playing) {
      const wait = this.speed().dwell + (step.packet ? 0 : 600);
      const player = this;
      const myToken = this.token;
      this.timer = setTimeout(function () {
        if (myToken === player.token && player.playing) player.goTo(player.index + 1, true);
      }, wait);
    }
    this.updateButtons();
  }

  // End of the simulation / presentation.
  finish() {
    const firstTime = !this.finished;
    this.playing = false;
    this.finished = true;
    this.updateButtons();
    if (firstTime) this.onFinish(this.steps);
  }

  /* ---------------- Rendering ---------------- */

  // Show the step's title, text, choices and progress dots.
  renderStep(step, index) {
    this.panel.classList.remove("intro");
    this.titleElement.textContent = step.title;
    this.textElement.textContent = step.explanation;
    this.counter.textContent = "Step " + (index + 1) + " of " + this.steps.length;

    // Decision buttons
    this.choiceRow.innerHTML = "";
    if (step.choices && !step.chosen) {
      const player = this;
      step.choices.forEach(function (choice) {
        const button = document.createElement("button");
        button.className = "btn " + (choice.style === "danger" ? "btn-red" : "btn-green");
        button.textContent = choice.label;
        button.addEventListener("click", function () { player.choose(choice.id); });
        player.choiceRow.appendChild(button);
      });
    }

    // Progress dots - click to jump to a step
    this.dots.innerHTML = "";
    for (let dotIndex = 0; dotIndex < this.steps.length; dotIndex++) {
      const dot = document.createElement("button");
      dot.className = "step-dot" + (dotIndex < index ? " done" : "") + (dotIndex === index ? " current" : "");
      dot.title = this.steps[dotIndex].title;
      dot.setAttribute("aria-label", "Go to " + this.steps[dotIndex].title);
      const player = this;
      dot.addEventListener("click", function () {
        player.playing = false;
        player.finished = false;
        player.goTo(dotIndex, true);
      });
      this.dots.appendChild(dot);
    }

    this.renderLog(index);
  }

  // List every packet sent so far (clickable).
  renderLog(index) {
    if (!this.logElement) return;
    const names = this.diagram.nodeNames();
    this.logElement.innerHTML = "";
    let count = 0;
    for (let stepIndex = 0; stepIndex <= index; stepIndex++) {
      const packet = this.steps[stepIndex].packet;
      if (!packet) continue;
      count += 1;
      const item = document.createElement("li");
      item.innerHTML = '<button type="button"><span class="dot dot-' + packet.style + '"></span>' +
        "<span>" + escapeHtml(packet.label) + '</span><span class="route">' +
        escapeHtml(names[packet.from] || packet.from) + " → " + escapeHtml(names[packet.to] || packet.to) +
        "</span></button>";
      $("button", item).addEventListener("click", function () { showPacketDetails(packet, names); });
      this.logElement.appendChild(item);
    }
    if (count === 0) this.logElement.innerHTML = '<li class="muted small">No packets sent yet.</li>';
  }

  // Enable/disable the control buttons for the current state.
  updateButtons() {
    const loaded = this.steps.length > 0;
    const atEnd = this.index >= this.steps.length - 1;
    const choice = this.waitingForChoice();
    this.buttons.start.disabled = this.loading || (loaded && !this.finished && this.index >= 0 && this.playing);
    this.buttons.pause.disabled = !loaded || !this.playing;
    this.buttons.resume.disabled = !loaded || this.playing || this.finished || choice || (atEnd && this.stepDone);
    this.buttons.prev.disabled = !loaded || this.index <= 0;
    this.buttons.next.disabled = !loaded || atEnd || choice;
    this.buttons.replay.disabled = !loaded;
    this.buttons.reset.disabled = !loaded;
  }
}

/* Page start-up */

document.addEventListener("DOMContentLoaded", function () {
  setupSidebar();
  setupModal();
});
