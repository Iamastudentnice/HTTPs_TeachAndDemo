/* packet_inspection.js - Lab 7. */

document.addEventListener("DOMContentLoaded", function () {
  const diagram = new NetworkDiagram($("#diagram"));
  diagram.setNodes([
    { id: "client", label: "Client", sublabel: "192.168.1.20", icon: "laptop", role: "client" },
    { id: "router", label: "Router / DNS", sublabel: "192.168.1.1", icon: "router", role: "router" },
    { id: "server", label: "Web Server", sublabel: "203.0.113.10", icon: "server", role: "server" },
  ]);
  const NODE_FOR_IP = { "192.168.1.20": "client", "192.168.1.1": "router", "203.0.113.10": "server" };

  const getMode = setupSegmented($("#mode-toggle"), function () { selected = null; load(); });
  let packets = [];
  let selected = null;

  // Ask Python for the data and redraw the page.
  async function load() {
    const result = await apiPost("/api/packets", { mode: getMode(), filter: $("#filter").value });
    packets = result.packets;
    const filterInput = $("#filter");
    filterInput.classList.toggle("invalid", Boolean(result.error));
    filterInput.classList.toggle("valid", !result.error && filterInput.value.trim() !== "");
    $("#filter-status").innerHTML = result.error
      ? '<span style="color:var(--red)">' + escapeHtml(result.error) + "</span>"
      : '<span class="muted">Showing ' + packets.length + " of " + result.total + " packets.</span>";
    renderTable();
    renderVisibility(result.visibility);
  }

  // CSS class used to colour a row by protocol.
  function protocolClass(protocol) {
    return protocol.indexOf("TLS") === 0 ? "TLS" : protocol;
  }

  // Draw the packet list table.
  function renderTable() {
    const body = $("#packet-rows");
    body.innerHTML = "";
    packets.forEach(function (packet) {
      const row = document.createElement("tr");
      row.className = "proto-" + protocolClass(packet.protocol) + (selected === packet.number ? " selected" : "");
      [packet.number, packet.time, packet.source_ip, packet.destination_ip, packet.protocol,
        packet.source_port, packet.destination_port, packet.length, packet.info].forEach(function (value) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      row.addEventListener("click", function () { selectPacket(packet); });
      body.appendChild(row);
    });
    if (packets.length === 0) body.innerHTML = '<tr><td colspan="9" class="muted">No packets match this filter.</td></tr>';
  }

  // Show a packet's layers and replay it on the diagram.
  function selectPacket(packet) {
    selected = packet.number;
    renderTable();

    // Layers, Wireshark style: each one expandable.
    let html = "";
    packet.layers.forEach(function (layer, index) {
      const isApp = index === packet.layers.length - 1 && index > 2;
      const layerClass = isApp ? (packet.payload_readable ? "app-plain" : "app-encrypted") : "";
      html += '<details class="layer ' + layerClass + '"' + (isApp || index === 1 ? " open" : "") + "><summary>" +
        escapeHtml(layer.name) + "</summary>" + detailsTable(Object.fromEntries(layer.fields)) + "</details>";
    });
    $("#packet-layers").innerHTML = html;

    const hex = $("#hex-dump");
    hex.className = "output " + (packet.payload_readable ? "plain" : "cipher");
    hex.textContent = packet.hex_dump;

    // Replay the packet on the diagram (style follows whether the payload is readable).
    const hasEncryptedPayload = packet.protocol.indexOf("TLS") === 0 && !packet.payload_readable;
    diagram.setHighlights({});
    diagram.showPacket({
      from: NODE_FOR_IP[packet.source_ip], to: NODE_FOR_IP[packet.destination_ip],
      style: hasEncryptedPayload ? "encrypted" : "plain",
      label: "#" + packet.number + " " + packet.protocol,
      details: { Source: packet.source_ip + ":" + packet.source_port, Destination: packet.destination_ip + ":" + packet.destination_port,
                 Protocol: packet.protocol, Length: packet.length + " bytes", Info: packet.info },
      payload: packet.payload_text || packet.hex_dump,
    }, true, 1400);

    recordProgress("packet_inspection", getMode());
  }

  // List what an observer can and cannot see.
  function renderVisibility(visibility) {
    $("#visible-list").innerHTML = visibility.visible.map(function (item) { return "<li>" + escapeHtml(item) + "</li>"; }).join("");
    $("#hidden-list").innerHTML = visibility.hidden.map(function (item) { return "<li>" + escapeHtml(item) + "</li>"; }).join("");
  }

  $("#filter-form").addEventListener("submit", function (event) { event.preventDefault(); load(); });
  $("#clear-filter").addEventListener("click", function () { $("#filter").value = ""; load(); });
  $all("[data-filter]").forEach(function (button) {
    button.addEventListener("click", function () { $("#filter").value = button.dataset.filter; load(); });
  });

  load();
});
