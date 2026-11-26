/* journey.js - Lab 02, the journey of a website.

   Python builds the eight stages (see simulations/website_journey.py); this file only shows them.
   Each stage has one or more parts. Next Step shows the next part, then the next stage.
   Nothing moves on by itself: when an animation ends, Next Step just starts to pulse. */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#journey-diagram"));
  setupSegmented($("#journey-protocol"), addressChanged);

  // Short names for the stage list at the top of the journey.
  const STAGE_NAMES = ["Address", "Saved copies", "DNS", "Way out", "Connection", "Security", "Request", "Page"];
  const PACKET_TIME = 1500;   // milliseconds for a packet to cross the diagram

  let journey = null;                  // the data from Python
  let stageIndex = 0;
  let partIndex = 0;
  let furthest = { stage: 0, part: 0 };  // the furthest point reached, so it can be returned to
  let diagramStage = -1;               // which stage's devices the diagram is currently showing
  let token = 0;                       // ignores an animation that finishes after the user moved on

  /* ---------- Starting ---------- */

  function chosenProtocol() {
    return $("#journey-protocol button.active").dataset.value;
  }

  // Show the protocol the journey is really using (an address typed with http:// wins).
  function setProtocolButtons(scheme) {
    $all("#journey-protocol button").forEach(function (button) {
      button.classList.toggle("active", button.dataset.value === scheme.toUpperCase());
    });
  }

  async function startJourney(event) {
    event.preventDefault();
    const error = $("#journey-error");
    let result;
    try {
      result = await apiPost("/api/journey", { address: $("#journey-address").value, protocol: chosenProtocol() });
    } catch (problem) {
      result = { ok: false, error: "The journey could not be built: " + problem.message };
    }
    if (!result.ok) {
      error.textContent = result.error;
      error.hidden = false;
      return;
    }
    error.hidden = true;
    $("#journey-changed").hidden = true;
    journey = result;
    setProtocolButtons(journey.address.scheme);
    $("#journey-summary-tls").textContent = journey.address.scheme === "https"
      ? "TLS secured the connection."
      : "No TLS: with HTTP the connection was not secured.";
    $("#journey").classList.remove("hidden");
    restartJourney();
    $("#journey").scrollIntoView({ block: "start", behavior: "smooth" });
  }

  // After a change to the address or protocol, say how to apply it.
  function addressChanged() {
    if (journey) $("#journey-changed").hidden = false;
  }

  /* ---------- Moving through the stages ---------- */

  function isLastPosition() {
    return stageIndex === journey.stages.length - 1 &&
      partIndex === journey.stages[stageIndex].parts.length - 1;
  }

  // True if position a comes after position b.
  function isLater(a, b) {
    return a.stage > b.stage || (a.stage === b.stage && a.part > b.part);
  }

  function nextStep() {
    if (isLastPosition()) return;
    if (partIndex < journey.stages[stageIndex].parts.length - 1) showPosition(stageIndex, partIndex + 1);
    else showPosition(stageIndex + 1, 0);
  }

  function previousStep() {
    if (partIndex > 0) showPosition(stageIndex, partIndex - 1);
    else if (stageIndex > 0) showPosition(stageIndex - 1, journey.stages[stageIndex - 1].parts.length - 1);
  }

  function replayStep() {
    diagramStage = -1;   // redraw the devices too
    showPosition(stageIndex, partIndex);
  }

  function restartJourney() {
    furthest = { stage: 0, part: 0 };
    diagramStage = -1;
    $("#journey-end").classList.add("hidden");
    showPosition(0, 0);
  }

  function finishJourney() {
    $("#journey-end").classList.remove("hidden");
    $("#journey-end").scrollIntoView({ block: "start", behavior: "smooth" });
    recordProgress("journey", "journey");
  }

  /* ---------- Drawing one position ---------- */

  function showPosition(stage, part) {
    stageIndex = stage;
    partIndex = part;
    if (isLater({ stage: stage, part: part }, furthest)) furthest = { stage: stage, part: part };

    const current = journey.stages[stage];
    const moment = current.parts[part];
    $("#journey-count").textContent = "Step " + (stage + 1) + " of " + journey.stages.length;
    $("#journey-concept").textContent = current.concept;
    $("#journey-title").textContent = current.title;
    $("#journey-explanation").textContent = current.explanation;
    $("#journey-points").innerHTML = current.points.map(function (point) { return "<li>" + escapeHtml(point) + "</li>"; }).join("");
    $("#journey-details").innerHTML = current.details.map(function (line) { return "<li>" + escapeHtml(line) + "</li>"; }).join("");

    $("#journey-part-count").textContent = current.parts.length > 1 ? "Part " + (part + 1) + " of " + current.parts.length : "";
    $("#journey-caption").textContent = moment.caption;
    showPanel(moment.panel);
    renderStageList();

    const isNetwork = current.visual === "network";
    $("#journey-diagram").classList.toggle("hidden", !isNetwork);
    $("#journey-legend").classList.toggle("hidden", !isNetwork);
    $("#journey-visual").classList.toggle("hidden", isNetwork);
    if (isNetwork) {
      drawNetworkPart(current, part);
    } else {
      $("#journey-visual").innerHTML = drawPicture(current.visual, part);
      if (current.visual === "render") connectExampleButton(part);
      setReady(true);
    }
    updateButtons();
  }

  // The packet for this part moves across the diagram. Earlier parts keep their line colours.
  function drawNetworkPart(stage, part) {
    token += 1;
    const myToken = token;
    setReady(false);

    function draw() {
      diagram.resetVisuals();
      for (let earlier = 0; earlier < part; earlier++) {
        if (stage.parts[earlier].packet) diagram.colourPath(stage.parts[earlier].packet);
      }
      diagram.setHighlights(stage.parts[part].highlight);
      const packet = stage.parts[part].packet;
      const arrival = packet ? diagram.showPacket(packet, true, PACKET_TIME) : Promise.resolve();
      arrival.then(function () {
        if (myToken === token) setReady(true);
      });
    }

    if (diagramStage !== stageIndex) {
      diagram.setNodes(stage.nodes);
      diagramStage = stageIndex;
      requestAnimationFrame(draw);   // let the new devices be measured first
    } else {
      draw();
    }
  }

  // When this part has finished, point at Next Step (or Finish Journey). Never move on automatically.
  function setReady(ready) {
    const last = isLastPosition();
    $("#journey-next").classList.toggle("is-next", ready && !last);
    $("#journey-finish-button").classList.toggle("is-next", ready && last);
    $("#journey-wait").textContent = !ready ? "" : last
      ? "That was the last stage. Press Finish Journey."
      : "Press Next Step when you are ready.";
  }

  function updateButtons() {
    const last = isLastPosition();
    $("#journey-prev").disabled = stageIndex === 0 && partIndex === 0;
    $("#journey-next").hidden = last;
    $("#journey-finish-button").hidden = !last;
  }

  function showPanel(panel) {
    const box = $("#journey-panel");
    box.classList.toggle("hidden", !panel);
    if (!panel) return;
    $("#journey-panel-title").textContent = panel.title;
    const text = $("#journey-panel-text");
    text.textContent = panel.text;
    text.className = "output " + (panel.readable ? "plain" : "cipher");
  }

  // The eight stages along the top. Stages already reached can be opened again.
  function renderStageList() {
    const list = $("#journey-stages");
    list.innerHTML = "";
    journey.stages.forEach(function (stage, index) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = (index + 1) + " " + STAGE_NAMES[index];
      button.title = stage.title;
      button.className = index === stageIndex ? "current" : index <= furthest.stage ? "reached" : "";
      button.disabled = index > furthest.stage;
      if (index === stageIndex) button.setAttribute("aria-current", "step");
      button.addEventListener("click", function () {
        // The furthest stage reopens where the user had got to; others open at their start.
        if (index === furthest.stage) showPosition(furthest.stage, furthest.part);
        else showPosition(index, 0);
      });
      item.appendChild(button);
      list.appendChild(item);
    });
  }

  /* ---------- The three stages that are not network diagrams ---------- */

  function drawPicture(type, part) {
    const address = journey.address;
    if (type === "address") {
      // Everything between "https://" and the path is the domain (plus a port, if one was typed).
      const host = address.full.slice(address.scheme.length + 3, address.full.length - address.path.length);
      const pieces = [
        { text: address.scheme + "://", label: "Protocol" },
        { text: host, label: "Domain" },
        { text: address.path, label: "Path" },
      ];
      return '<div class="url-pieces">' + pieces.map(function (piece, index) {
        return '<span class="url-piece piece-' + index + stateClass(index, part) + '"><span class="url-text">' +
          escapeHtml(piece.text) + '</span><span class="url-label">' + piece.label + "</span></span>";
      }).join("") + "</div>";
    }

    if (type === "cache") {
      const boxes = [
        { title: "Browser cache", keeps: "Saved copies of website files: pages, pictures, styles." },
        { title: "DNS cache", keeps: "Saved website names and their IP addresses." },
      ];
      return '<div class="cache-boxes">' + boxes.map(function (box, index) {
        const checked = index <= part;
        return '<div class="cache-box' + stateClass(index, part) + '"><strong>' + box.title + "</strong>" +
          '<p class="small">' + box.keeps + "</p>" +
          '<p class="cache-result">' + (checked ? "Checked: not saved - cache miss" : "Not checked yet") + "</p></div>";
      }).join("") + "</div>" +
        '<div class="cache-compare"><div><strong>Cache hit</strong> Already saved, so it is used straight away and time is saved.</div>' +
        "<div><strong>Cache miss</strong> Not saved (or too old), so it has to be fetched again.</div></div>";
    }

    // "render": files received on the left, the page as it appears on the right.
    const files = ["HTML", "CSS", "JavaScript"];
    const look = ["page-html", "page-css", "page-js"][part];
    return '<div class="render-flow"><div class="render-files"><div class="output-label">Files received</div>' +
      files.map(function (file, index) {
        return '<span class="render-file' + stateClass(index, part) + '">' + file + "</span>";
      }).join("") + '</div><span class="render-arrow" aria-hidden="true">&rarr;</span>' +
      '<div class="render-screen"><div class="output-label">Your screen</div><div class="mock-page ' + look + '">' +
      "<h3>Example page for " + escapeHtml(address.domain) + "</h3>" +
      "<p>This page is made up for the demo.</p>" +
      '<button type="button" class="mock-button">Say hello</button>' +
      '<p class="mock-output" aria-live="polite"></p></div></div></div>';
  }

  // Pieces already explained are "shown"; the one being explained now is "current".
  function stateClass(index, part) {
    if (index === part) return " shown current";
    return index < part ? " shown" : "";
  }

  // The example page's button only works once JavaScript has "arrived" (the last part).
  function connectExampleButton(part) {
    const button = $("#journey-visual .mock-button");
    const output = $("#journey-visual .mock-output");
    button.addEventListener("click", function () {
      output.textContent = part === 2
        ? "Hello! JavaScript made this happen."
        : "Nothing happens yet - the JavaScript has not arrived.";
    });
  }

  /* ---------- Buttons ---------- */

  $("#journey-form").addEventListener("submit", startJourney);
  $("#journey-address").addEventListener("input", addressChanged);
  $("#journey-next").addEventListener("click", nextStep);
  $("#journey-prev").addEventListener("click", previousStep);
  $("#journey-replay").addEventListener("click", replayStep);
  $("#journey-restart").addEventListener("click", restartJourney);
  $("#journey-finish-button").addEventListener("click", finishJourney);
  $("#journey-again").addEventListener("click", function () {
    restartJourney();
    $("#journey").scrollIntoView({ block: "start", behavior: "smooth" });
  });
});
