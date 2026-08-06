import { el } from "./utils.js";
import { getHealth } from "./api.js";
import { initializeMap, toggleTracking, pauseTracking, resetTracking, setSimulationSpeed, toggleLayer, changeAirport, seekReplay } from "./map.js";
import { loadIncidents, renderIncidentList, loadIncident, showTab, simulateIncident, performOperatorAction, resolveSelected, generateSelectedReport } from "./incidents.js";
import { askCopilot } from "./copilot.js";
import { addLog, clearLog } from "./eventLog.js";
import { onTrackingTick, updateFusion, updateThreatMatrix, acknowledgeThreat } from "./liveOps.js";
import { initializeMissionOps, updateWeather, updateProactiveBrief } from "./missionOps.js";
import { initializeCommandCenter } from "./commandCenter.js";
import { initializeRealtimeConsole } from "./realtimeConsole.js";
import { initializeEnterprise } from "./enterprise.js";
import { initializeEnterprise8 } from "./enterprise8.js";
import { initializeWebSocket } from "./websocket.js";
async function checkHealth(){try{const health=await getHealth();el("statusText").textContent=`API v${health.version}`;el("backendDot").classList.add("online")}catch{el("statusText").textContent="Backend offline";el("backendDot").classList.remove("online")}}
function bindEvents(){
  el("incidentSearch").addEventListener("input",renderIncidentList);el("severityFilter").addEventListener("change",renderIncidentList);el("sortFilter").addEventListener("change",renderIncidentList);el("simulateButton").addEventListener("click",simulateIncident);
  el("incidentList").addEventListener("click",event=>{const card=event.target.closest("[data-incident-id]");if(card)loadIncident(card.dataset.incidentId).then(()=>{updateFusion();updateThreatMatrix()})});
  document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>showTab(button.dataset.tab)));document.querySelectorAll("[data-action]").forEach(button=>button.addEventListener("click",()=>performOperatorAction(button.dataset.action,addLog)));
  el("resolveButton").addEventListener("click",resolveSelected);el("reportButton").addEventListener("click",generateSelectedReport);el("copilotButton").addEventListener("click",askCopilot);el("copilotQuestion").addEventListener("keydown",event=>{if(event.key==="Enter")askCopilot()});
  el("trackingButton").addEventListener("click",()=>toggleTracking(onTrackingTick));el("pauseButton").addEventListener("click",pauseTracking);el("resetTrackButton").addEventListener("click",resetTracking);el("clearLogButton").addEventListener("click",clearLog);
  el("speedSelect").addEventListener("change",e=>setSimulationSpeed(e.target.value,onTrackingTick));el("airportSelect").addEventListener("change",e=>changeAirport(e.target.value));el("ackButton").addEventListener("click",acknowledgeThreat);el("dismissAlert").addEventListener("click",()=>el("criticalAlert").classList.add("hidden"));el("replaySlider").addEventListener("input",e=>seekReplay(e.target.value,onTrackingTick));el("replayButton").addEventListener("click",()=>{pauseTracking();seekReplay(0,onTrackingTick);});
  document.querySelectorAll("[data-layer]").forEach(x=>x.addEventListener("change",()=>toggleLayer(x.dataset.layer,x.checked)));
}
async function initialize(){initializeMap();bindEvents();initializeMissionOps();initializeCommandCenter();initializeRealtimeConsole();initializeEnterprise();initializeEnterprise8();initializeWebSocket();updateFusion();updateThreatMatrix();await checkHealth();await loadIncidents();setInterval(checkHealth,5000);setInterval(loadIncidents,10000)}
initialize();
