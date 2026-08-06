import { addLog } from "./eventLog.js";
import { loadIncidents } from "./incidents.js";
import { toast } from "./utils.js";

let socket;
let retryTimer;

function socketUrl() {
  const host = window.location.hostname || "127.0.0.1";
  return `ws://${host}:8000/api/v1/ws`;
}

export function initializeWebSocket() {
  clearTimeout(retryTimer);
  socket = new WebSocket(socketUrl());

  socket.addEventListener("open", () => addLog("WebSocket live gateway connected"));
  socket.addEventListener("message", async event => {
    const message = JSON.parse(event.data);
    if (message.type === "incident.created" || message.type === "incident.status") {
      await loadIncidents();
      toast(`Live update: ${message.type}`);
    }
    if (message.type === "timeline.event") {
      addLog(`Timeline update received for ${message.incident_id}`);
    }
  });
  socket.addEventListener("close", () => {
    addLog("WebSocket disconnected; retrying");
    retryTimer = setTimeout(initializeWebSocket, 3000);
  });
  socket.addEventListener("error", () => socket?.close());
}
