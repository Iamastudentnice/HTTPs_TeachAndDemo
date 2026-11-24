/* presentation.js - Presentation Mode (the two-minute demo). */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#diagram"));
  const buttons = {
    start: $("#btn-start"), pause: $("#btn-pause"), resume: $("#btn-resume"),
    prev: $("#btn-prev"), next: $("#btn-next"), restart: $("#btn-restart"),
  };

  let script = null;        // the data from Python
  let flatSteps = [];       // every step in time order, with its scene number
  let elapsedMs = 0;        // presentation clock
  let playing = false;
  let finished = false;
  let lastTick = 0;
  let shownStep = -1;       // index into flatSteps currently on screen
  let shownScene = -1;

  // Format seconds as m:ss.
  function formatTime(seconds) {
    const whole = Math.floor(seconds);
    return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
  }

  /* ---------- Timeline bar (one segment per scene) ---------- */

  // Create one timeline segment per scene.
  function buildTimeline() {
    const timeline = $("#timeline");
    timeline.innerHTML = "";
    script.scenes.forEach(function (scene, sceneIndex) {
      const segment = document.createElement("button");
      segment.className = "timeline-seg";
      segment.style.flex = String(scene.end - scene.start);
      segment.innerHTML = '<span class="fill"></span><span class="seg-label">' +
        formatTime(scene.start) + " · " + escapeHtml(scene.title) + "</span>";
      segment.addEventListener("click", function () { jumpToScene(sceneIndex); });
      timeline.appendChild(segment);
    });
  }

  // Update the timer and the timeline fill.
  function updateTimeline() {
    const seconds = elapsedMs / 1000;
    $("#timer").textContent = formatTime(seconds);
    $all(".timeline-seg", $("#timeline")).forEach(function (segment, sceneIndex) {
      const scene = script.scenes[sceneIndex];
      let fraction = (seconds - scene.start) / (scene.end - scene.start);
      fraction = Math.max(0, Math.min(1, fraction));
      $(".fill", segment).style.width = (fraction * 100) + "%";
      segment.classList.toggle("current", sceneIndex === shownScene && !finished);
    });
  }

  /* ---------- Showing a step ---------- */

  // Which step the clock has reached.
  function currentStepIndex() {
    let found = 0;
    flatSteps.forEach(function (item, index) {
      if (item.step.at * 1000 <= elapsedMs) found = index;
    });
    return found;
  }

  // Show one presentation step (diagram, caption, cards).
  function showStep(index, animate) {
    const item = flatSteps[index];
    const scene = script.scenes[item.scene];
    const sceneChanged = item.scene !== shownScene;
    shownStep = index;
    shownScene = item.scene;

    if (sceneChanged) {
      diagram.setNodes(scene.nodes);
      $("#scene-title").textContent = scene.title;
      $("#headline").textContent = scene.headline;
    }

    // How long until the next step? Use about half of it for the packet animation.
    const next = flatSteps[index + 1];
    const gap = next ? (next.step.at - item.step.at) : 6;
    const duration = Math.min(2000, gap * 1000 * 0.5);

    // Colour lines used earlier in this scene so the story stays visible.
    function draw() {
      diagram.resetVisuals();
      flatSteps.forEach(function (earlier, earlierIndex) {
        if (earlier.scene === item.scene && earlierIndex < index && earlier.step.packet) {
          diagram.colourPath(earlier.step.packet);
        }
      });
      diagram.setHighlights(item.step.highlight);
      if (item.step.packet) {
        diagram.showPacket(item.step.packet, animate, duration);
        if (!playing) diagram.pause();
      }
    }
    // A new scene needs one frame for the diagram to measure itself.
    if (sceneChanged) requestAnimationFrame(draw); else draw();

    $("#caption").textContent = item.step.caption;
    renderCards(item.step.cards);
  }

  // Show the information cards for a step.
  function renderCards(cards) {
    const container = $("#cards");
    container.innerHTML = "";
    cards.forEach(function (info) {
      const box = document.createElement("div");
      box.className = "present-card tone-" + info.tone;
      box.innerHTML = '<div class="pc-label">' + escapeHtml(info.label) + '</div><div class="pc-value">' +
        escapeHtml(info.value) + "</div>";
      container.appendChild(box);
    });
  }

  /* ---------- The clock ---------- */

  // Advance the clock and show the step it has reached.
  function tick() {
    if (!script) return;
    if (playing) {
      const now = performance.now();
      elapsedMs += now - lastTick;
      lastTick = now;
      if (elapsedMs >= script.total_seconds * 1000) {
        elapsedMs = script.total_seconds * 1000;
        finish();
      }
    }
    const index = currentStepIndex();
    if (index !== shownStep) showStep(index, playing);
    updateTimeline();
  }

  // End of the simulation / presentation.
  function finish() {
    playing = false;
    finished = true;
    $("#end-card").classList.remove("hidden");
    $("#scene-title").textContent = "Demonstration complete";
    updateButtons();
  }

  /* ---------- Controls ---------- */

  // Fetch the steps from Python and start playing.
  async function start() {
    buttons.start.disabled = true;
    try {
      script = await apiGet("/api/presentation");
    } catch (error) {
      buttons.start.disabled = false;
      showError($("#caption"), error.message);
      return;
    }
    flatSteps = [];
    script.scenes.forEach(function (scene, sceneIndex) {
      scene.steps.forEach(function (step) { flatSteps.push({ scene: sceneIndex, step: step }); });
    });
    buildTimeline();
    restart();
  }

  // Start the presentation again from 0:00.
  function restart() {
    elapsedMs = 0;
    shownStep = -1;
    shownScene = -1;
    finished = false;
    $("#end-card").classList.add("hidden");
    play();
  }

  // Start or continue the clock.
  function play() {
    playing = true;
    lastTick = performance.now();
    diagram.resume();
    updateButtons();
  }

  // Pause the animation.
  function pause() {
    playing = false;
    diagram.pause();
    updateButtons();
  }

  // Continue after a pause.
  function resume() {
    if (finished) return;
    play();
  }

  // Move the clock to the start of a scene.
  function jumpToScene(sceneIndex) {
    if (!script) return;
    sceneIndex = Math.max(0, Math.min(script.scenes.length - 1, sceneIndex));
    elapsedMs = script.scenes[sceneIndex].start * 1000;
    finished = false;
    $("#end-card").classList.add("hidden");
    shownStep = -1;
    shownScene = -1;
    tick();
    updateButtons();
  }

  // Enable/disable the control buttons for the current state.
  function updateButtons() {
    const loaded = Boolean(script);
    buttons.start.disabled = loaded;
    buttons.pause.disabled = !loaded || !playing;
    buttons.resume.disabled = !loaded || playing || finished;
    buttons.prev.disabled = !loaded || shownScene <= 0;
    buttons.next.disabled = !loaded || shownScene >= (script ? script.scenes.length - 1 : 0);
    buttons.restart.disabled = !loaded;
  }

  buttons.start.addEventListener("click", start);
  buttons.pause.addEventListener("click", pause);
  buttons.resume.addEventListener("click", resume);
  buttons.restart.addEventListener("click", restart);
  buttons.prev.addEventListener("click", function () { jumpToScene(shownScene - 1); });
  buttons.next.addEventListener("click", function () { jumpToScene(shownScene + 1); });

  document.addEventListener("keydown", function (event) {
    if (!script || event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA") return;
    if (event.code === "Space") {
      event.preventDefault();
      if (playing) pause(); else resume();
    } else if (event.key === "ArrowRight") {
      jumpToScene(shownScene + 1);
    } else if (event.key === "ArrowLeft") {
      jumpToScene(shownScene - 1);
    }
  });

  setInterval(function () {
    tick();
    updateButtons();
  }, 100);

  // Before starting, show the first scene's devices so the screen isn't empty.
  diagram.setNodes([
    { id: "client", label: "Your Browser", sublabel: "you", icon: "laptop", role: "client" },
    { id: "server", label: "Website", sublabel: "shop.example.com", icon: "server", role: "server" },
  ]);
});
