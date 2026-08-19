import { el, esc } from "./utils.js";
import {
  getHealth,
  getDashboardSummary,
  getSessionStatus,
  getSessionContext,
  updateSessionContext,
  login,
  logout,
  listConnectors,
  evaluateDecision,
  getDecision,
  reviewDecision,
} from "./api.js";
import { initializeMap, toggleTracking, pauseTracking, resetTracking, setSimulationSpeed, toggleLayer, changeAirport, seekReplay } from "./map.js";
import { loadIncidents, renderIncidentList, loadIncident, showTab, simulateIncident, performOperatorAction, resolveSelected, generateSelectedReport } from "./incidents.js";
import { askCopilot } from "./copilot.js";
import { addLog, clearLog } from "./eventLog.js";
import { onTrackingTick, updateFusion, updateThreatMatrix, acknowledgeThreat } from "./liveOps.js";
import { initializeMissionOps, updateWeather, updateProactiveBrief } from "./missionOps.js";
import { initializeCommandCenter } from "./commandCenter.js";
import { initializeRealtimeConsole } from "./realtimeConsole.js";
import { initializeEnterprise, refreshEnterpriseAudit, refreshEnterpriseReports, showWorkspace } from "./enterprise.js";
import { initializeEnterprise8, refreshIntegrations } from "./enterprise8.js";
import { initializeMaintenance } from "./maintenance.js";
import { initializePlanning } from "./planning.js";
import { initializeLogistics } from "./logistics.js";
import { initializeLibrary } from "./library.js";
import { initializePersonnel } from "./personnel.js";
import { initializeWebSocket } from "./websocket.js";
import { initializeUx2 } from "./ux2/index.js";
let currentSession = null;
let currentContext = null;
let latestConnectors = [];
let selectedDecisionId = null;
let reauthInProgress = false;
let eventsBound = false;

async function checkHealth(){
  try{
    const health=await getHealth();
    const db = health.database || "unknown";
    const connectors = health.connectors || {};
    const degraded = Number(connectors.degraded || 0) + Number(connectors.error || 0);
    const statusLabel = health.status === "ok" && !degraded
      ? `API v${health.version}`
      : `API v${health.version} · ${String(health.status || "degraded").toUpperCase()}${degraded ? ` · connectors ${degraded} degraded/error` : ""}`;
    el("statusText").textContent = statusLabel;
    if (health.status === "ok" && db === "online") {
      el("backendDot").classList.add("online");
      el("backendDot").classList.remove("degraded");
    } else {
      el("backendDot").classList.remove("online");
      el("backendDot").classList.add("degraded");
    }
    if (el("dashboardPlatformStatus") && !el("dashboardPlatformStatus").textContent) {
      el("dashboardPlatformStatus").textContent = String(health.status || "UNKNOWN").toUpperCase();
    }
  }catch{
    el("statusText").textContent="Backend offline";
    el("backendDot").classList.remove("online");
    el("backendDot").classList.remove("degraded");
  }
}
function bindEvents(){
  if (eventsBound) return;
  eventsBound = true;
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
  const signOutButton = el("ux2SignOut");
  if (signOutButton) {
    signOutButton.addEventListener("click", signOut);
  }
  window.addEventListener("mercury:auth-required", () => {
    void recoverExpiredSession();
  });
  const evaluateButton = el("decisionEvaluateButton");
  if (evaluateButton) evaluateButton.addEventListener("click", evaluateDecisionFromUi);
  const reviewSubmit = el("decisionReviewSubmit");
  if (reviewSubmit) reviewSubmit.addEventListener("click", () => submitDecisionReview("acknowledged"));
  const reviewCommentBtn = el("decisionReviewCommentBtn");
  if (reviewCommentBtn) reviewCommentBtn.addEventListener("click", () => submitDecisionReview("commented"));
  const reviewRejectBtn = el("decisionReviewRejectBtn");
  if (reviewRejectBtn) reviewRejectBtn.addEventListener("click", () => submitDecisionReview("rejected_advisory"));
  const timeline = el("decisionTimelineList");
  if (timeline) {
    timeline.addEventListener("click", event => {
      const row = event.target.closest("[data-decision-id]");
      if (!row || !row.dataset.decisionId) return;
      loadDecisionDetail(row.dataset.decisionId);
    });
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
    .map(item => `<option value="${esc(item.organization_id)}">${esc(item.name)}</option>`)
    .join("");
  siteSelect.innerHTML = sites
    .map(item => `<option value="${esc(item.site_id)}">${esc(item.name)}</option>`)
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
  try { await refreshEnterpriseReports(); } catch { /* ignore report refresh errors */ }
  try { await refreshIntegrations(); } catch { /* ignore connector refresh errors */ }
}

async function onSiteChange(event){
  const site_id = event.target.value;
  currentContext = await updateSessionContext({ site_id });
  renderOrgSiteSelectors(currentContext);
  try { await refreshEnterpriseAudit(); } catch { /* ignore audit refresh errors */ }
  try { await refreshEnterpriseReports(); } catch { /* ignore report refresh errors */ }
  try { await refreshIntegrations(); } catch { /* ignore connector refresh errors */ }
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

  // Task 18: overlay live ConnectorManager states onto Command connector panel when available.
  if (latestConnectors.length) {
    const byCategory = Object.fromEntries(latestConnectors.map(item => [item.category, item.state]));
    if (byCategory.aviation) el("connectorAdsb").textContent = String(byCategory.aviation).toUpperCase();
    if (byCategory.weather) el("connectorWeather").textContent = String(byCategory.weather).toUpperCase();
    const online = latestConnectors.filter(item => item.state === "online").length;
    const degraded = latestConnectors.filter(item => item.state === "degraded").length;
    const errored = latestConnectors.filter(item => item.state === "error").length;
    const liveStatus = errored ? "critical" : degraded ? "degraded" : online ? "online" : "offline";
    setStatusIndicator("connectorStatusDot","connectorStatusLabel",liveStatus,`Status ${liveStatus.toUpperCase()} · ${online}/${latestConnectors.length} online`);
  }

  el("alertsActiveTotal").textContent = alertSummary.active ?? 0;
  el("alertsCriticalTotal").textContent = alertSummary.critical ?? 0;
  el("alertsAcknowledgedTotal").textContent = alertSummary.acknowledged ?? 0;
  el("sensorOnlineTotal").textContent = sensorHealth.online ?? 0;
  el("sensorWarningTotal").textContent = sensorHealth.warning ?? 0;
  el("sensorOfflineTotal").textContent = sensorHealth.offline ?? 0;

  el("decisionTimelineList").innerHTML = decisionTimeline.length
    ? decisionTimeline
      .map(item => {
        const decisionId = item.decision_id ? String(item.decision_id) : "";
        const reviewState = item.review_state || (item.operator_acknowledged ? "acknowledged" : "pending");
        const selectedName = item.selected_name || "Decision update";
        const warnings = item.warning_count ?? 0;
        return `<div class="log-entry" data-decision-id="${esc(decisionId)}" style="cursor:${decisionId ? "pointer" : "default"}">
          <span>${esc(item.timestamp || "Unknown time")}</span>
          <strong>${esc(selectedName)}</strong>
          <small>${esc(reviewState)} · warnings ${esc(warnings)}${item.operator_acknowledged ? " · acknowledged" : " · review pending"}</small>
        </div>`;
      })
      .join("")
    : '<div class="empty">No decision timeline entries yet. Operator review required.</div>';

  if (decisions.selected_recommendation && decisions.selected_recommendation.name) {
    el("dashboardSummaryMessage").textContent = `Advisory recommended: ${decisions.selected_recommendation.name}. Human review required.`;
  } else {
    el("dashboardSummaryMessage").textContent = "No active advisory recommendation. Operator review pending.";
  }

  if (decisions.latest_decision_id && !selectedDecisionId) {
    loadDecisionDetail(decisions.latest_decision_id);
  } else if (selectedDecisionId) {
    loadDecisionDetail(selectedDecisionId);
  }
}

function renderDecisionExplain(decision) {
  if (!decision) {
    if (el("decisionReviewState")) el("decisionReviewState").textContent = "—";
    if (el("decisionFactorsList")) {
      el("decisionFactorsList").innerHTML = '<div class="empty">Select a decision to inspect factors, warnings, assumptions, and uncertainty.</div>';
    }
    if (el("decisionAlternativesList")) {
      el("decisionAlternativesList").innerHTML = '<div class="empty">No alternatives selected.</div>';
    }
    return;
  }
  selectedDecisionId = decision.decision_id || selectedDecisionId;
  const review = decision.review || {};
  if (el("decisionReviewState")) {
    el("decisionReviewState").textContent = `${review.state || "pending"}${review.reviewed_by ? ` · ${review.reviewed_by}` : ""}`;
  }

  const factorRows = [];
  factorRows.push(`<div class="log-entry"><strong>Reasoning</strong><small>${esc(decision.reasoning || "")}</small></div>`);
  (decision.warnings || []).forEach(item => {
    factorRows.push(`<div class="log-entry"><strong>Warning</strong><small>${esc(item)}</small></div>`);
  });
  (decision.assumptions || []).forEach(item => {
    factorRows.push(`<div class="log-entry"><strong>Assumption</strong><small>${esc(item)}</small></div>`);
  });
  (decision.uncertainty || []).forEach(item => {
    factorRows.push(`<div class="log-entry"><strong>Uncertainty</strong><small>${esc(item)}</small></div>`);
  });
  (decision.factor_breakdown || []).forEach(item => {
    factorRows.push(
      `<div class="log-entry"><strong>${esc(item.name || "factor")}</strong><small>${esc(item.detail || "")} · ${esc(item.weight_or_score)}</small></div>`
    );
  });
  const connector = decision.connector_context || {};
  if ((connector.degraded || []).length || (connector.error || []).length) {
    factorRows.push(
      `<div class="log-entry"><strong>Connector trust</strong><small>degraded=${esc((connector.degraded || []).join(", ") || "none")}; error=${esc((connector.error || []).join(", ") || "none")}</small></div>`
    );
  }
  if (el("decisionFactorsList")) {
    el("decisionFactorsList").innerHTML = factorRows.length
      ? factorRows.join("")
      : '<div class="empty">No explanation factors available.</div>';
  }

  const alternatives = decision.ranked_actions || [];
  if (el("decisionAlternativesList")) {
    el("decisionAlternativesList").innerHTML = alternatives.length
      ? alternatives
          .map(
            (item, index) =>
              `<div class="log-entry"><span>#${index + 1}</span><strong>${esc(item.name)}</strong><small>score ${esc(item.overall_score)} · confidence ${esc(item.confidence)}</small></div>`
          )
          .join("")
      : '<div class="empty">No alternatives available.</div>';
  }
}

async function loadDecisionDetail(decisionId) {
  if (!decisionId) return;
  try {
    const decision = await getDecision(decisionId);
    renderDecisionExplain(decision);
  } catch (error) {
    if (el("decisionFactorsList")) {
      el("decisionFactorsList").innerHTML = `<div class="empty">Decision detail unavailable: ${esc(error.message)}</div>`;
    }
  }
}

async function evaluateDecisionFromUi() {
  try {
    const decision = await evaluateDecision({
      mission_id: "mission-command-1",
      track_id: `track-command-${Date.now()}`,
      threat_level: "high",
      threat_score: 80,
      response_recommendations: ["Dispatch patrol", "Escalate to operations", "Monitor current state"],
      operator_constraints: ["human_review_required"],
    });
    selectedDecisionId = decision.decision_id;
    renderDecisionExplain(decision);
    addLog(`Advisory decision evaluated: ${decision.selected_recommendation?.name || decision.decision_id}`);
    await loadDashboardSummary();
    try { await refreshEnterpriseAudit(); } catch { /* optional admin refresh */ }
  } catch (error) {
    addLog(`Decision evaluate failed: ${error.message}`);
  }
}

async function submitDecisionReview(state) {
  if (!selectedDecisionId) {
    addLog("Select or evaluate a decision before review.");
    return;
  }
  const comment = el("decisionReviewComment")?.value || "";
  try {
    const decision = await reviewDecision(selectedDecisionId, { state, comment: comment || null });
    renderDecisionExplain(decision);
    addLog(`Decision review ${state}: ${selectedDecisionId}`);
    await loadDashboardSummary();
    try { await refreshEnterpriseAudit(); } catch { /* optional admin refresh */ }
  } catch (error) {
    addLog(`Decision review failed: ${error.message}`);
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
  renderDecisionExplain(null);
}

async function loadDashboardSummary(){
  el("dashboardSummaryMessage").textContent = "Loading dashboard summary…";
  try {
    const summary = await getDashboardSummary();
    try {
      latestConnectors = await listConnectors();
      if (!Array.isArray(latestConnectors)) latestConnectors = [];
    } catch {
      latestConnectors = [];
    }
    renderDashboardSummary(summary);
  } catch (error) {
    renderDashboardError(`Dashboard unavailable: ${error.message}`);
  }
}

async function ensureSession(){
  let session = await getSessionStatus();
  if (!session.authenticated) {
    session = await promptInteractiveLogin();
  }
  currentSession = session;
  renderSessionIdentity(session);
  return session;
}

function renderSessionIdentity(session){
  const root = el("ux2Session");
  const nameNode = el("ux2SessionOperator");
  const roleNode = el("ux2SessionRole");
  if (!root || !nameNode || !roleNode) return;
  if (session && session.authenticated) {
    nameNode.textContent = String(session.operator || "");
    roleNode.textContent = String(session.role || "");
    root.hidden = false;
  } else {
    nameNode.textContent = "";
    roleNode.textContent = "";
    root.hidden = true;
  }
}

async function signOut(){
  try {
    await logout();
  } catch {
    // Cookie/session may already be gone; still return to the login overlay.
  }
  currentSession = null;
  currentContext = null;
  renderSessionIdentity(null);
  window.location.reload();
}

let loginPromptPromise = null;
let loginSubmitInFlight = false;

function readLoginCredentials(form, operatorInput, passwordInput) {
  const data = form ? new FormData(form) : null;
  const operator = String((data && data.get("operator")) ?? operatorInput?.value ?? "").trim();
  const namedPassword = data ? data.get("password") : null;
  const password = namedPassword != null ? String(namedPassword) : String(passwordInput?.value ?? "");
  return { operator, password };
}

function clearLoginPromptLock() {
  loginPromptPromise = null;
  if (typeof window !== "undefined") window.__mercuryLoginPrompt = null;
}

function promptInteractiveLogin(){
  // Boot and 401 recovery both call this. form.onsubmit cannot stack; window lock
  // covers a second module graph; in-flight flag guarantees one POST per click.
  if (loginPromptPromise) return loginPromptPromise;
  if (typeof window !== "undefined" && window.__mercuryLoginPrompt) {
    return window.__mercuryLoginPrompt;
  }
  loginPromptPromise = new Promise((resolve, reject) => {
    const overlay = el("loginOverlay");
    const form = el("loginForm");
    const errorNode = el("loginError");
    const operatorInput = el("loginOperator");
    const passwordInput = el("loginPassword");
    const submitBtn = el("loginSubmit");
    if (!overlay || !form || !operatorInput || !passwordInput) {
      clearLoginPromptLock();
      reject(new Error("Login UI unavailable"));
      return;
    }
    const overlayWasHidden = overlay.classList.contains("hidden");
    overlay.classList.remove("hidden");
    if (errorNode) {
      errorNode.textContent = "";
      errorNode.classList.add("hidden");
    }
    if (overlayWasHidden) passwordInput.value = "";
    operatorInput.focus();

    const onSubmit = async event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (loginSubmitInFlight) return;
      loginSubmitInFlight = true;
      if (submitBtn) submitBtn.disabled = true;
      try {
        const { operator, password } = readLoginCredentials(form, operatorInput, passwordInput);
        const session = await login({ operator, password });
        if (!session.authenticated) {
          throw new Error("Authentication failed");
        }
        form.onsubmit = null;
        overlay.classList.add("hidden");
        clearLoginPromptLock();
        resolve(session);
      } catch (error) {
        if (errorNode) {
          errorNode.textContent = error.message || "Invalid credentials";
          errorNode.classList.remove("hidden");
        }
      } finally {
        loginSubmitInFlight = false;
        if (submitBtn) submitBtn.disabled = false;
      }
    };
    form.onsubmit = onSubmit;
  });
  if (typeof window !== "undefined") window.__mercuryLoginPrompt = loginPromptPromise;
  return loginPromptPromise;
}

async function recoverExpiredSession(){
  if (reauthInProgress) return;
  const overlay = el("loginOverlay");
  if (overlay && !overlay.classList.contains("hidden")) return;
  reauthInProgress = true;
  currentSession = null;
  currentContext = null;
  renderSessionIdentity(null);
  try {
    const session = await promptInteractiveLogin();
    currentSession = session;
    renderSessionIdentity(session);
    await loadSessionContext();
    applyRoleAccess();
  } catch {
    // Overlay remains until the operator signs in.
  } finally {
    reauthInProgress = false;
  }
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

  const canReview = !(isViewer);
  ["decisionReviewSubmit", "decisionReviewCommentBtn", "decisionReviewRejectBtn"].forEach(id => {
    const node = el(id);
    if (node) node.disabled = !canReview;
  });
}

async function initialize(){
  try {
    initializeMap();
  } catch {
    // Command map depends on Leaflet. A CSP/CDN miss must not skip UX2 navigate() binding.
  }
  bindEvents();
  initializeMissionOps();
  initializeCommandCenter();
  initializeRealtimeConsole();
  initializeEnterprise();
  initializeEnterprise8();
  initializeMaintenance();
  initializePlanning();
  initializeLogistics();
  initializeLibrary();
  initializePersonnel();
  await ensureSession();
  await loadSessionContext();
  applyRoleAccess();
  initializeUx2({
    initial: "home",
    onNavigate: (id) => showWorkspace(id),
  });
  initializeWebSocket();
  updateFusion();
  updateThreatMatrix();
  await checkHealth();
  await loadDashboardSummary();
  await loadIncidents();
  import("./ux2/workspaces.js").then((m) => m.refreshHomeWorkspace()).catch(() => {});
  setInterval(checkHealth,5000);
  setInterval(loadDashboardSummary,15000);
  setInterval(loadIncidents,10000);
}
initialize();
