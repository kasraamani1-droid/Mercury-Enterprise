import { el } from "./utils.js";
import { getHealth, getDashboardSummary, getSessionStatus, getSessionContext, updateSessionContext, login } from "./api.js";
import { initializeMap, toggleTracking, pauseTracking, resetTracking, setSimulationSpeed, toggleLayer, changeAirport, seekReplay } from "./map.js";
import { loadIncidents, renderIncidentList, loadIncident, showTab, simulateIncident, performOperatorAction, resolveSelected, generateSelectedReport } from "./incidents.js";
import { askCopilot } from "./copilot.js";
import { addLog, clearLog } from "./eventLog.js";
import { onTrackingTick, updateFusion, updateThreatMatrix, acknowledgeThreat } from "./liveOps.js";
import { initializeMissionOps, updateWeather, updateProactiveBrief } from "./missionOps.js";
import { initializeCommandCenter } from "./commandCenter.js";
import { initializeRealtimeConsole } from "./realtimeConsole.js";
import { initializeEnterprise, refreshEnterpriseAudit } from "./enterprise.js";
import { initializeEnterprise8 } from "./enterprise8.js";
import { initializeWebSocket } from "./websocket.js";
let currentSession = null;
let currentContext = null;

async function checkHealth(){try{const health=await getHealth();el("statusText").textContent=`API v${health.version}`;el("backendDot").classList.add("online")}catch{el("statusText").textContent="Backend offline";el("backendDot").classList.remove("online")}}
function bindEvents(){
  el("incidentSearch").addEventListener("input",renderIncidentList);el("severityFilter").addEventListener("change",renderIncidentList);el("sortFilter").addEventListener("change",renderIncidentList);el("simulateButton").addEventListener("click",simulateIncident);
  el("incidentList").addEventListener("click",event=>{const card=event.target.closest("[data-incident-id]");if(card)loadIncident(card.dataset.incidentId).then(()=>{updateFusion();updateThreatMatrix()})});
  document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>showTab(button.dataset.tab)));document.querySelectorAll("[data-action]").forEach(button=>button.addEventListener("click",()=>performOperatorAction(button.dataset.action,addLog)));
  el("resolveButton").addEventListener("click",resolveSelected);el("reportButton").addEventListener("click",generateSelectedReport);el("copilotButton").addEventListener("click",askCopilot);el("copilotQuestion").addEventListener("keydown",event=>{if(event.key==="Enter")askCopilot()});
  el("trackingButton").addEventListener("click",()=>toggleTracking(onTrackingTick));el("pauseButton").addEventListener("click",pauseTracking);el("resetTrackButton").addEventListener("click",resetTracking);el("clearLogButton").addEventListener("click",clearLog);
  el("speedSelect").addEventListener("change",e=>setSimulationSpeed(e.target.value,onTrackingTick));el("airportSelect").addEventListener("change",e=>changeAirport(e.target.value));el("ackButton").addEventListener("click",acknowledgeThreat);el("dismissAlert").addEventListener("click",()=>el("criticalAlert").classList.add("hidden"));el("replaySlider").addEventListener("input",e=>seekReplay(e.target.value,onTrackingTick));el("replayButton").addEventListener("click",()=>{pauseTracking();seekReplay(0,onTrackingTick);});
  document.querySelectorAll("[data-layer]").forEach(x=>x.addEventListener("change",()=>toggleLayer(x.dataset.layer,x.checked)));
  const organizationSelect = el("organizationSelect");
  if (organizationSelect) {
    organizationSelect.addEventListener("change", onOrganizationChange);
  }
  const siteSelect = el("siteSelect");
  if (siteSelect) {
    siteSelect.addEventListener("change", onSiteChange);
  }
}

function renderOrgSiteSelectors(context){
  const organizationSelect = el("organizationSelect");
  const siteSelect = el("siteSelect");
  if (!organizationSelect || !siteSelect) return;

  const organizations = Array.isArray(context.organizations) ? context.organizations : [];
  const sites = Array.isArray(context.sites) ? context.sites : [];

  organizationSelect.innerHTML = organizations
    .map(item => `<option value="${item.organization_id}">${item.name}</option>`)
    .join("");
  siteSelect.innerHTML = sites
    .map(item => `<option value="${item.site_id}">${item.name}</option>`)
    .join("");

  if (context.organization?.organization_id) {
    organizationSelect.value = context.organization.organization_id;
  }
  if (context.site?.site_id) {
    siteSelect.value = context.site.site_id;
  }
}

async function loadSessionContext(){
  currentContext = await getSessionContext();
  renderOrgSiteSelectors(currentContext);
}

async function onOrganizationChange(event){
  const organization_id = event.target.value;
  currentContext = await updateSessionContext({ organization_id });
  renderOrgSiteSelectors(currentContext);
  try { await refreshEnterpriseAudit(); } catch { /* ignore audit refresh errors */ }
}

async function onSiteChange(event){
  const site_id = event.target.value;
  currentContext = await updateSessionContext({ site_id });
  renderOrgSiteSelectors(currentContext);
  try { await refreshEnterpriseAudit(); } catch { /* ignore audit refresh errors */ }
}

function setStatusIndicator(dotId, labelId, status, text){
  const dot=el(dotId);if(dot){dot.classList.remove("online","degraded","offline");if(["online","active","stable","clear"].includes(status))dot.classList.add("online");else if(["degraded","critical","review_required"].includes(status))dot.classList.add("degraded");else dot.classList.add("offline")}
  const label=el(labelId);if(label)label.textContent=text;
}

function renderDashboardSummary(summary){
  const platform = summary.platform || {};
  const alerts = summary.alerts || {};
  const missions = summary.missions || {};
  const services = summary.services || {};
  const decisions = summary.decisions || {};
  const fleet = summary.fleet_health || {};
  const connectors = summary.connector_health || {};
  const alertSummary = summary.active_alerts_summary || {};
  const sensorHealth = summary.sensor_health || {};
  const decisionTimeline = summary.decision_timeline || [];
  const missionStatus = String(missions.status || (missions.active ? "active" : "idle")).toLowerCase();
  const alertStatus = String(alerts.status || (alertSummary.critical ? "critical" : alertSummary.active ? "active" : "stable")).toLowerCase();
  const decisionStatus = String(decisions.status || (decisions.pending_human_review ? "review_required" : "clear")).toLowerCase();
  const connectorStatus = String(connectors.status || "offline").toLowerCase();
  el("dashboardPlatformStatus").textContent = platform.status ? platform.status.toUpperCase() : "UNKNOWN";
  el("dashboardActiveMissions").textContent = missions.active ?? 0;
  el("dashboardActiveAlerts").textContent = alerts.active ?? 0;
  el("dashboardActiveTracks").textContent = services.active_tracks ?? 0;
  el("dashboardHighestThreat").textContent = (decisions.highest_threat_level || "UNKNOWN").toString().toUpperCase();
  el("dashboardPendingDecisions").textContent = decisions.pending_human_review ?? 0;
  el("dashboardStatus").textContent = `Connected ${platform.connected_services ?? 0} services`;
  setStatusIndicator("dashboardMissionDot","dashboardMissionStatus",missionStatus,missionStatus.replaceAll("_"," ").toUpperCase());
  setStatusIndicator("dashboardAlertDot","dashboardAlertStatus",alertStatus,alertStatus.replaceAll("_"," ").toUpperCase());
  setStatusIndicator("dashboardDecisionDot","dashboardDecisionStatus",decisionStatus,decisionStatus.replaceAll("_"," ").toUpperCase());
  setStatusIndicator("connectorStatusDot","connectorStatusLabel",connectorStatus,`Status ${connectorStatus.replaceAll("_"," ").toUpperCase()}`);
  el("fleetAircraftOnline").textContent = fleet.aircraft_online ?? 0;
  el("fleetActiveSensors").textContent = fleet.active_sensors ?? 0;
  el("fleetIncidents").textContent = fleet.incidents ?? 0;
  el("fleetAiConfidence").textContent = `${Math.round(Number(fleet.ai_confidence ?? 0))}%`;
  el("fleetStatusLabel").textContent = platform.status ? `Backend ${platform.status} · Connectors ${connectorStatus}` : "Status unknown";

  el("connectorAdsb").textContent = String(connectors.ads_b || "offline").toUpperCase();
  el("connectorRf").textContent = String(connectors.rf || "offline").toUpperCase();
  el("connectorCameras").textContent = String(connectors.cameras || "offline").toUpperCase();
  el("connectorWeather").textContent = String(connectors.weather || "offline").toUpperCase();
  el("connectorMl").textContent = String(connectors.ml_engine || "offline").toUpperCase();

  el("alertsActiveTotal").textContent = alertSummary.active ?? 0;
  el("alertsCriticalTotal").textContent = alertSummary.critical ?? 0;
  el("alertsAcknowledgedTotal").textContent = alertSummary.acknowledged ?? 0;
  el("sensorOnlineTotal").textContent = sensorHealth.online ?? 0;
  el("sensorWarningTotal").textContent = sensorHealth.warning ?? 0;
  el("sensorOfflineTotal").textContent = sensorHealth.offline ?? 0;

  el("decisionTimelineList").innerHTML = decisionTimeline.length
    ? decisionTimeline
      .map(item => `<div class="log-entry"><span>${item.timestamp || "Unknown time"}</span><strong>${item.decision || "Decision update"}</strong><small>${item.operator_acknowledged ? "Acknowledged by operator" : "Operator acknowledgement pending"}</small></div>`)
      .join("")
    : '<div class="empty">No decision timeline entries yet. Operator review required.</div>';

  if (decisions.selected_recommendation && decisions.selected_recommendation.name) {
    el("dashboardSummaryMessage").textContent = `Recommended: ${decisions.selected_recommendation.name}. Operator review required.`;
  } else {
    el("dashboardSummaryMessage").textContent = "No active recommendation. Operator review pending.";
  }
}

function renderDashboardError(message){
  el("dashboardPlatformStatus").textContent = "OFFLINE";
  el("dashboardActiveMissions").textContent = "—";
  el("dashboardActiveAlerts").textContent = "—";
  el("dashboardActiveTracks").textContent = "—";
  el("dashboardHighestThreat").textContent = "UNKNOWN";
  el("dashboardPendingDecisions").textContent = "—";
  el("dashboardStatus").textContent = "Dashboard unavailable";
  el("dashboardSummaryMessage").textContent = message;
  setStatusIndicator("dashboardMissionDot","dashboardMissionStatus","offline","OFFLINE");
  setStatusIndicator("dashboardAlertDot","dashboardAlertStatus","offline","OFFLINE");
  setStatusIndicator("dashboardDecisionDot","dashboardDecisionStatus","offline","OFFLINE");
  setStatusIndicator("connectorStatusDot","connectorStatusLabel","offline","Status OFFLINE");
  el("fleetAircraftOnline").textContent = "—";
  el("fleetActiveSensors").textContent = "—";
  el("fleetIncidents").textContent = "—";
  el("fleetAiConfidence").textContent = "—";
  el("fleetStatusLabel").textContent = "Unavailable";
  el("connectorAdsb").textContent = "OFFLINE";
  el("connectorRf").textContent = "OFFLINE";
  el("connectorCameras").textContent = "OFFLINE";
  el("connectorWeather").textContent = "OFFLINE";
  el("connectorMl").textContent = "OFFLINE";
  el("alertsActiveTotal").textContent = "—";
  el("alertsCriticalTotal").textContent = "—";
  el("alertsAcknowledgedTotal").textContent = "—";
  el("sensorOnlineTotal").textContent = "—";
  el("sensorWarningTotal").textContent = "—";
  el("sensorOfflineTotal").textContent = "—";
  el("decisionTimelineList").innerHTML = '<div class="empty">Decision timeline unavailable.</div>';
}

async function loadDashboardSummary(){
  el("dashboardSummaryMessage").textContent = "Loading dashboard summary…";
  try {
    const summary = await getDashboardSummary();
    renderDashboardSummary(summary);
  } catch (error) {
    renderDashboardError(`Dashboard unavailable: ${error.message}`);
  }
}

async function ensureSession(){
  let session = await getSessionStatus();
  if (!session.authenticated) {
    session = await login({ operator: "operator", password: "mercury-demo" });
  }
  currentSession = session;
  return session;
}

function applyRoleAccess(){
  const role = String(currentSession?.role || "Viewer");
  const isViewer = role === "Viewer";
  const isReviewer = role === "Reviewer";
  const disableOperate = isViewer || isReviewer;

  const simulateButton = el("simulateButton");
  if (simulateButton) simulateButton.disabled = disableOperate;

  const resolveButton = el("resolveButton");
  if (resolveButton) resolveButton.disabled = disableOperate;

  document.querySelectorAll("[data-action]").forEach(button => {
    button.disabled = disableOperate;
  });
}

async function initialize(){initializeMap();bindEvents();initializeMissionOps();initializeCommandCenter();initializeRealtimeConsole();initializeEnterprise();initializeEnterprise8();await ensureSession();await loadSessionContext();applyRoleAccess();initializeWebSocket();updateFusion();updateThreatMatrix();await checkHealth();await loadDashboardSummary();await loadIncidents();setInterval(checkHealth,5000);setInterval(loadDashboardSummary,15000);setInterval(loadIncidents,10000)}
initialize();
