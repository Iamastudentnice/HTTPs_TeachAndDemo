/* http_https.js - Module 1 page. */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#diagram"));
  const getProtocol = setupSegmented($("#protocol-toggle"), settingsChanged);
  const eavesdropperBox = $("#eavesdropper");
  const messageBox = $("#message");

  // Read the user's choices from the page.
  function currentSettings() {
    return {
      protocol: getProtocol(),
      message: messageBox.value,
      eavesdropper: eavesdropperBox.checked,
    };
  }

  // Show the three devices before anything is played.
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

  // Put text in an output box, or a placeholder if empty.
  function setOutput(element, text, emptyText, className) {
    if (text) {
      element.className = "output " + className;
      element.textContent = text;
    } else {
      element.className = "output empty";
      element.textContent = emptyText;
    }
  }

  // Empty all the information panels.
  function clearPanels() {
    setOutput($("#wire-view"), "", 'Press "Send message" to see the data leave your browser.');
    setOutput($("#attacker-view"), "", "Nothing captured yet.");
    setOutput($("#server-view"), "", "Nothing received yet.");
    $("#attacker-status").innerHTML = "";
    $("#client-view").textContent = messageBox.value;
  }

  const player = new StepPlayer({
    diagram: diagram,
    mount: $("#player"),
    logElement: $("#packet-log"),
    startLabel: "Send message",
    introTitle: "Choose HTTP or HTTPS, then press Send message",
    introText: "Watch your login travel from the browser (left) to the server (right). Tick the eavesdropper box to see what a Wi-Fi sniffer captures.",
    loadSteps: function () {
      clearPanels();
      return apiPost("/api/http-https/simulate", currentSettings());
    },
    onStep: function (step, index, panels) {
      updateAddress(panels);
      if (panels.client_view) $("#client-view").textContent = panels.client_view;
      setOutput($("#wire-view"), panels.wire_data, "The request has not been built yet.",
        getProtocol() === "HTTPS" ? "cipher" : "plain");
      setOutput($("#attacker-view"), panels.attacker_view, "Nothing captured yet.",
        panels.attacker_can_read ? "danger" : "cipher");
      $("#attacker-status").innerHTML = panels.attacker_view === undefined ? "" :
        panels.attacker_can_read
          ? '<div class="callout danger"><strong>Readable!</strong> The password is exposed.</div>'
          : '<div class="callout good"><strong>Ciphertext only.</strong> Metadata is visible, content is not.</div>';
      setOutput($("#server-view"), panels.server_view, "Nothing received yet.", "plain");
    },
    onFinish: function () {
      recordProgress("http_https", getProtocol().toLowerCase());
    },
    onReset: clearPanels,
  });

  // Any change to the settings resets the simulation so it matches what is shown.
  function settingsChanged() {
    player.reset();
    previewDiagram();
  }
  eavesdropperBox.addEventListener("change", settingsChanged);
  messageBox.addEventListener("input", function () {
    if (player.steps.length) player.reset();
    $("#client-view").textContent = messageBox.value;
  });

  previewDiagram();
});
