/* http_https.js - Lab 01, HTTP vs HTTPS (the start page). */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#diagram"));
  const getProtocol = setupSegmented($("#protocol-toggle"), settingsChanged);
  const eavesdropperBox = $("#eavesdropper");
  const messageBox = $("#message");

  // Which protocols the user has already sent a message with (for the hints).
  const tried = { HTTP: false, HTTPS: false };

  // Read the user's choices from the page.
  function currentSettings() {
    return {
      protocol: getProtocol(),
      message: messageBox.value,
      eavesdropper: eavesdropperBox.checked,
    };
  }

  // Draw the devices before anything is sent.
  async function previewDiagram() {
    const data = await apiPost("/api/http-https/simulate", currentSettings());
    diagram.setNodes(data.nodes);
    updateAddress(null);
  }

  // Update the fake browser address bar.
  function updateAddress(panels) {
    const address = $("#address");
    if (!panels || !panels.address) {
      const protocol = getProtocol();
      address.className = "address";
      address.innerHTML = '<svg><use href="#i-' + (protocol === "HTTPS" ? "lock" : "unlock") + '"/></svg>' +
        '<span class="addr-text">' + protocol.toLowerCase() + "://shop.example.com/login</span>";
      return;
    }
    address.className = "address " + (panels.secure ? "secure" : "insecure");
    address.innerHTML = '<svg><use href="#i-' + (panels.secure ? "lock" : "unlock") + '"/></svg>' +
      '<span class="addr-text">' + escapeHtml(panels.address) + "</span>" +
      (panels.secure ? "" : '<span class="addr-flag">Not secure</span>');
  }

  // Put text in an output box, or a grey placeholder if there is nothing yet.
  function setOutput(element, text, emptyText, className) {
    if (text) {
      element.className = "output " + className;
      element.textContent = text;
    } else {
      element.className = "output empty";
      element.textContent = emptyText;
    }
  }

  // Empty the panels for a new run (the comparison box is kept on purpose).
  function clearPanels() {
    setOutput($("#wire-view"), "", 'Press "Send message" to see the data leave your browser.');
    setOutput($("#attacker-view"), "", "Nothing captured yet.");
    setOutput($("#server-view"), "", "Nothing received yet.");
    $("#attacker-status").innerHTML = "";
    $("#client-view").textContent = messageBox.value;
  }

  // Fill one side of the HTTP / HTTPS comparison.
  function fillComparison(protocol, text, readable) {
    const side = protocol.toLowerCase();
    setOutput($("#compare-" + side), text, "", readable ? "plain" : "cipher");
    $("#compare-" + side + "-note").textContent = readable
      ? "Readable - your details are visible"
      : "Scrambled - only where it is going is visible";
  }

  // Show a short hint about what to do next, and highlight that control.
  function updateHint() {
    const hint = $("#lesson-hint");
    const httpsButton = $('#protocol-toggle [data-value="HTTPS"]');
    const httpButton = $('#protocol-toggle [data-value="HTTP"]');
    const observer = $("#observer-option");
    [httpsButton, httpButton, observer].forEach(function (element) { element.classList.remove("is-next"); });

    if (!player.steps.length) {
      hint.textContent = "Press Send message to begin.";
    } else if (!player.finished) {
      hint.textContent = "Select Next Step to continue. You can select a packet to inspect it.";
    } else if (!tried.HTTPS) {
      hint.textContent = "Switch to HTTPS to compare.";
      httpsButton.classList.add("is-next");
    } else if (!tried.HTTP) {
      hint.textContent = "Switch to HTTP to compare.";
      httpButton.classList.add("is-next");
    } else if (!eavesdropperBox.checked) {
      hint.textContent = "Enable the eavesdropper to see what an attacker can read.";
      observer.classList.add("is-next");
    } else {
      hint.textContent = "Select a packet to inspect it, or open a lab under Explore deeper.";
    }
  }

  const player = new StepPlayer({
    diagram: diagram,
    mount: $("#player"),
    logElement: $("#packet-log"),
    startLabel: "Send message",
    introTitle: "Choose HTTP or HTTPS, then press Send message",
    introText: "Your login travels from your browser (left) to the website (right).",
    loadSteps: function () {
      clearPanels();
      return apiPost("/api/http-https/simulate", currentSettings());
    },
    onStep: function (step, index, panels) {
      updateAddress(panels);
      if (panels.client_view) $("#client-view").textContent = panels.client_view;
      setOutput($("#wire-view"), panels.wire_data, "The message has not been written yet.",
        getProtocol() === "HTTPS" ? "cipher" : "plain");
      if (panels.network_view) fillComparison(getProtocol(), panels.network_view, panels.network_can_read);
      setOutput($("#attacker-view"), panels.attacker_view, "Nothing captured yet.",
        panels.attacker_can_read ? "danger" : "cipher");
      $("#attacker-status").innerHTML = panels.attacker_view === undefined ? "" :
        panels.attacker_can_read
          ? '<div class="callout danger"><strong>Readable.</strong> The password is exposed.</div>'
          : '<div class="callout good"><strong>Scrambled.</strong> They see where it goes, not what it says.</div>';
      setOutput($("#server-view"), panels.server_view, "Nothing received yet.", "plain");
      updateHint();
    },
    onFinish: function () {
      tried[getProtocol()] = true;
      recordProgress("http_https", getProtocol().toLowerCase());
      updateHint();
    },
    onReset: function () {
      clearPanels();
      updateHint();
    },
  });

  // Any change to the settings starts again, so the diagram always matches the options.
  function settingsChanged() {
    $("#attacker-box").classList.toggle("hidden", !eavesdropperBox.checked);
    player.reset();
    previewDiagram();
  }
  eavesdropperBox.addEventListener("change", settingsChanged);
  messageBox.addEventListener("input", function () {
    if (player.steps.length) player.reset();
    $("#client-view").textContent = messageBox.value;
  });

  // Some browsers remember a ticked checkbox after a refresh; start from the simple view.
  eavesdropperBox.checked = false;
  previewDiagram();
  updateHint();
});
