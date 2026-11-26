/* mitm.js - Lab 6. */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#diagram"));
  const PRESETS = {
    login: { message: "Username: John Doe\nPassword: example123", find: "John Doe", replace: "Mallory" },
    payment: { message: "Pay £10 to account 12345678", find: "£10 to account 12345678", replace: "£9,000 to account 66666666" },
  };

  const getScenario = setupSegmented($("#scenario-toggle"), scenarioChanged);

  // Collect the attacker options from the page.
  function options() {
    return {
      attacker_modifies: getScenario() === "https_mitm" ? $("#tamper").checked : $("#modify").checked,
      find_text: $("#find").value,
      replace_text: $("#replace").value,
      cert_problem: $("#cert-problem").value,
      protection: $("#protection").value,
    };
  }

  // Call the right Python API for the chosen scenario.
  function request() {
    if (getScenario() === "arp") {
      return apiPost("/api/arp/simulate", { defence: $("#arp-defence").value });
    }
    return apiPost("/api/mitm/simulate", { scenario: getScenario(), message: $("#message").value, options: options() });
  }

  /* ---------------- Panels ---------------- */

  // Put text in an output box, or a placeholder if empty.
  function setOutput(element, text, emptyText, className) {
    element.className = "output " + (text ? className : "empty");
    element.textContent = text || emptyText;
  }

  // Highlight words in the modified text that were not in the original.
  function highlightChanges(original, modified) {
    const originalWords = original.split(/(\s+|&)/);
    return modified.split(/(\s+|&)/).map(function (word) {
      const safe = escapeHtml(word);
      return word.trim() && originalWords.indexOf(word) < 0 ? '<mark class="changed">' + safe + "</mark>" : safe;
    }).join("");
  }

  // Empty all the information panels.
  function clearPanels() {
    setOutput($("#victim-view"), "", "-");
    setOutput($("#attacker-view"), "", "Nothing intercepted yet.");
    setOutput($("#server-view"), "", "Nothing received yet.");
    $("#attacker-status").innerHTML = "";
    $("#victim-address").className = "address";
    $(".addr-text", $("#victim-address")).textContent = "-";
    $("#diff-card").classList.add("hidden");
    $("#cert-card").classList.add("hidden");
    $("#outcome").innerHTML = "";
    $("#arp-detection").innerHTML = "";
    renderArpTables({ victim: [], attacker: [], gateway: [] });
  }

  // Fill the information panels for the current step.
  function renderPanels(panels) {
    if (panels.address) {
      const address = $("#victim-address");
      const secure = panels.secure === true;
      address.className = "address " + (panels.secure === false ? "insecure" : secure ? "secure" : "");
      $("svg use", address).setAttribute("href", secure ? "#i-lock" : "#i-unlock");
      $(".addr-text", address).textContent = panels.address + (panels.secure === false ? "  · Not secure" : "");
    }
    setOutput($("#victim-view"), panels.victim_sent, "-", "plain");
    setOutput($("#attacker-view"), panels.attacker_saw, "Nothing intercepted yet.",
      panels.attacker_can_read ? "danger" : "cipher");
    $("#attacker-status").innerHTML = panels.attacker_saw === undefined ? "" : panels.attacker_can_read
      ? '<div class="callout danger"><strong>Plaintext!</strong> The attacker can read everything.</div>'
      : '<div class="callout good"><strong>Ciphertext only.</strong> Metadata visible, content protected.</div>';
    setOutput($("#server-view"), panels.server_received, "Nothing received yet.",
      panels.tamper_detected ? "cipher" : panels.was_modified ? "danger" : "plain");

    if (panels.original && panels.modified) {
      $("#diff-card").classList.remove("hidden");
      $("#diff-original").textContent = panels.original;
      $("#diff-modified").innerHTML = highlightChanges(panels.original, panels.modified);
    }

    if (panels.checks) {
      $("#cert-card").classList.remove("hidden");
      $("#cert-checks").innerHTML = panels.checks.map(function (check) {
        return '<li class="' + (check.passed ? "pass" : "fail") + '"><span class="mark">' + (check.passed ? "✓" : "✕") +
          "</span><div><strong>" + escapeHtml(check.name) + "</strong>" + escapeHtml(check.detail) + "</div></li>";
      }).join("");
      const verdict = panels.verdict;
      $("#cert-browser").innerHTML = verdict.trusted
        ? '<div class="secure-page"><h3>' + iconSvg("lock") + " Padlock shown - no warning</h3><p class=\"small\">The device trusts the attacker's CA, so the fake certificate passes every check.</p></div>"
        : '<div class="warning-page"><h3>' + iconSvg("warning") + " " + escapeHtml(verdict.headline) + '</h3><p class="small">' +
          escapeHtml(verdict.message) + '</p><div class="code">' + escapeHtml(verdict.error_code) + "</div></div>";
    }

    if (panels.tables) renderArpTables(panels.tables);
    if (panels.detection) {
      $("#arp-detection").innerHTML = panels.detection.map(function (line) {
        return '<div class="callout warn"><strong>Detection:</strong> ' + escapeHtml(line) + "</div>";
      }).join("");
    }

    if (panels.outcome === "safe") {
      $("#outcome").innerHTML = '<div class="callout good"><strong>Attack failed.</strong> The victim\'s data stayed protected.</div>';
    } else if (panels.outcome === "compromised") {
      $("#outcome").innerHTML = '<div class="callout danger"><strong>Attack succeeded.</strong> The attacker is in the middle and can read the victim\'s data.</div>';
    } else {
      $("#outcome").innerHTML = "";
    }
  }

  // Draw the three ARP tables.
  function renderArpTables(tables) {
    [["victim", "#arp-victim"], ["attacker", "#arp-attacker"], ["gateway", "#arp-gateway"]].forEach(function (pair) {
      const rows = tables[pair[0]] || [];
      $(pair[1]).innerHTML = rows.length === 0 ? '<p class="small muted">(empty)</p>' :
        '<table class="arp-table"><tr><th>IP address</th><th>MAC address</th></tr>' + rows.map(function (row) {
          const note = row.status === "poisoned" ? " ⚠" : row.status === "static" ? " (static)" : "";
          return '<tr class="' + row.status + '"><td>' + escapeHtml(row.ip) + "</td><td>" + escapeHtml(row.mac) + note + "</td></tr>";
        }).join("") + "</table>";
    });
  }

  /* ---------------- Player ---------------- */

  const player = new StepPlayer({
    diagram: diagram,
    mount: $("#player"),
    logElement: $("#packet-log"),
    startLabel: "Start Simulation",
    introTitle: "Press Start Simulation",
    introText: "Then use Next Step to go at your own pace.",
    loadSteps: function () { clearPanels(); return request(); },
    onStep: function (step, index, panels) {
      $("#mitm-panels").hidden = false;
      renderPanels(panels);
    },
    onFinish: function () {
      const scenario = getScenario();
      if (scenario !== "normal_http" && scenario !== "normal_https") recordProgress("mitm", scenario);
    },
    onReset: function () {
      $("#mitm-panels").hidden = true;
      clearPanels();
    },
  });

  /* ---------------- Scenario switching ---------------- */

  // Show the options and devices for the chosen scenario.
  async function scenarioChanged() {
    const scenario = getScenario();
    player.reset();
    $all("[data-for]").forEach(function (group) { group.classList.toggle("hidden", group.dataset.for !== scenario); });
    $("#message-group").classList.toggle("hidden", scenario === "arp");
    $("#flow-panels").classList.toggle("hidden", scenario === "arp");
    $("#arp-panels").classList.toggle("hidden", scenario !== "arp");
    const notes = SCENARIO_NOTES[scenario] || {};
    $("#scenario-goal").textContent = notes.goal || "";
    $("#note-defence").textContent = notes.defence || "";
    // Show the right devices straight away (nothing plays until Start).
    const data = await request();
    diagram.setNodes(data.nodes, data.extra_links);
  }

  $all("[data-preset]").forEach(function (button) {
    button.addEventListener("click", function () {
      const preset = PRESETS[button.dataset.preset];
      $("#message").value = preset.message;
      $("#find").value = preset.find;
      $("#replace").value = preset.replace;
      player.reset();
    });
  });
  ["#modify", "#tamper", "#cert-problem", "#protection", "#arp-defence"].forEach(function (id) {
    $(id).addEventListener("change", function () { player.reset(); });
  });
  ["#message", "#find", "#replace"].forEach(function (id) {
    $(id).addEventListener("input", function () { if (player.steps.length) player.reset(); });
  });

  // A link such as mitm?scenario=arp opens that scenario. (Flask also marks it on the
  // server; this line is what makes it work on the GitHub Pages copy.)
  const linked = new URLSearchParams(window.location.search).get("scenario");
  const scenarioButtons = $all("#scenario-toggle button[data-value]");
  const linkedButton = scenarioButtons.find(function (button) { return button.dataset.value === linked; });
  if (linkedButton) {
    scenarioButtons.forEach(function (button) { button.classList.toggle("active", button === linkedButton); });
  }

  scenarioChanged();
});
