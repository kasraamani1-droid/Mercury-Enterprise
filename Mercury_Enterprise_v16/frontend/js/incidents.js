import { state } from "./state.js";
import { SEVERITY_RANK } from "./config.js";
import { el, esc, fmt, confidenceAverage, toast } from "./utils.js";
import { getIncidents, getIncident, getAssessment, createIncident, addEvent, resolveIncident, downloadReport, getSessionStatus, requestApproval } from "./api.js";
import { buildTimelineEvents, renderTimeline } from "./timeline.js";
import { renderAssessment } from "./assessment.js";

export function updateStats(){
  const total=el("totalIncidents"),open=el("openIncidents"),high=el("highSeverity");
  if(total) total.textContent=state.incidents.length;
  if(open) open.textContent=state.incidents.filter(x=>String(x.status).toLowerCase()==="open").length;
  if(high) high.textContent=state.incidents.filter(x=>["high","critical"].includes(String(x.severity).toLowerCase())).length;
  renderThreatBars();
}
function renderThreatBars(){
  const counts={high:0,medium:0,low:0};
  state.incidents.forEach(x=>{const s=String(x.severity).toLowerCase();if(counts[s]!==undefined)counts[s]++});
  const total=Math.max(1,state.incidents.length);
  el("threatBars").innerHTML=Object.entries(counts).map(([name,count])=>`<div class="threat-row"><span>${name}</span><div class="mini-bar"><span class="${name}" style="width:${count/total*100}%"></span></div><strong>${count}</strong></div>`).join("");
}
export async function loadIncidents(){
  try{
    state.incidents=(await getIncidents()).filter(x=>String(x.status).toLowerCase()!=="resolved");
    renderIncidentList();updateStats();el("incidentError").innerHTML="";
    if(state.incidents.length&&!state.selectedIncidentId) await loadIncident(state.incidents[0].id);
  }catch(error){el("incidentError").innerHTML=`<div class="error">${esc(error.message)}</div>`}
}
function filteredIncidents(){
  const query=el("incidentSearch").value.toLowerCase();
  const severity=el("severityFilter").value;
  const sort=el("sortFilter").value;
  const list=state.incidents.filter(x=>(severity==="all"||String(x.severity).toLowerCase()===severity)&&`${x.title} ${x.summary}`.toLowerCase().includes(query));
  list.sort(sort==="severity"?(a,b)=>(SEVERITY_RANK[String(b.severity).toLowerCase()]||0)-(SEVERITY_RANK[String(a.severity).toLowerCase()]||0):(a,b)=>new Date(b.created_at)-new Date(a.created_at));
  return list;
}
export function renderIncidentList(){
  const list=filteredIncidents();
  el("incidentList").innerHTML=list.length?list.map(x=>`<article class="incident ${x.id===state.selectedIncidentId?"active":""}" data-incident-id="${esc(x.id)}"><h3>${esc(x.title)}</h3><span class="severity ${esc(String(x.severity).toLowerCase())}">${esc(x.severity)}</span><div class="meta">${esc(x.status)} · ${fmt(x.created_at)}</div></article>`).join(""):'<div class="empty">No matching incidents.</div>';
}
export async function loadIncident(id){
  state.selectedIncidentId=id;renderIncidentList();
  try{
    const [incident,assessment]=await Promise.all([getIncident(id),getAssessment(id)]);
    state.selectedIncident=incident;state.selectedAssessment=assessment;
    const events=buildTimelineEvents(incident);
    const average=confidenceAverage([...(incident.events||[]),...(incident.evidence||[])]);
    el("selectedConfidence").textContent=`${average??assessment.score}%`;
    el("incidentDetail").innerHTML=`<div class="detail-header"><h2>${esc(incident.title)}</h2></div><article class="detail-card card"><span class="severity ${esc(String(incident.severity).toLowerCase())}">${esc(incident.severity)}</span><div class="meta"><strong>Status:</strong> ${esc(incident.status)}<br><strong>Created:</strong> ${fmt(incident.created_at)}</div><p>${esc(incident.summary||"No summary available.")}</p></article><h3>Timeline</h3>${renderTimeline(events)}`;
    el("assessmentTab").innerHTML=renderAssessment(assessment);
    renderEvidence(incident.evidence||[]);
    showTab("assessment");
  }catch(error){el("incidentDetail").innerHTML=`<div class="error">${esc(error.message)}</div>`}
}
function renderEvidence(evidence){
  el("evidenceDetails").innerHTML=evidence.length?evidence.map(item=>{
    const meta=[item.provenance,item.created_by,item.site_id,item.evidence_type,item.source,`${Math.round(Number(item.confidence)||0)}%`]
      .filter(value=>value!=null&&String(value).trim()!=="")
      .map(value=>esc(String(value)))
      .join(" · ");
    return `<article class="evidence-item"><h3>${esc(item.title)}</h3><p>${esc(item.content)}</p><div class="meta">${meta}</div></article>`;
  }).join(""):'<div class="empty">No database evidence available for this incident.</div>';
}
export function showTab(name){
  ["assessment","evidence","actions","analytics"].forEach(tab=>{
    el(`${tab}Tab`).classList.toggle("hidden",tab!==name);
    document.querySelector(`[data-tab="${tab}"]`).classList.toggle("active",tab===name);
  });
}
export async function simulateIncident(){
  const cases=[
    {title:"Unauthorized drone approaching Runway 24R",severity:"high",summary:"Target crossed the warning zone and continued toward protected airspace."},
    {title:"Unknown RF control signal near cargo apron",severity:"medium",summary:"Persistent control-band activity requires operator verification."},
    {title:"Possible drone near north perimeter",severity:"low",summary:"Low-confidence visual detection under review."}
  ];
  try{const incident=await createIncident({...cases[Math.floor(Math.random()*cases.length)],status:"open"});toast("New simulated incident created");await loadIncidents();await loadIncident(incident.id)}catch(error){toast(error.message)}
}
export async function performOperatorAction(description,logCallback){
  if(!state.selectedIncidentId)return toast("Select an incident first");
  try{await addEvent(state.selectedIncidentId,{occurred_at:new Date().toISOString(),event_type:"operator_action",source:"Operator Console",description,confidence:100});toast(description);logCallback(description);await loadIncident(state.selectedIncidentId)}catch(error){toast(error.message)}
}
export async function resolveSelected(){
  if(!state.selectedIncidentId)return toast("Select an incident first");
  try{
    const session = await getSessionStatus();
    const role = String(session.role || "Viewer");
    if (role === "Viewer" || role === "Reviewer") return toast("Current role is read-only for incident resolution");
    if (role === "Operator") {
      await requestApproval({ action: "incident.resolve", target_id: state.selectedIncidentId, reason: "Operator requested incident resolution" });
      return toast("Approval request submitted for reviewer/administrator");
    }
    await resolveIncident(state.selectedIncidentId);
    toast("Incident resolved");state.selectedIncidentId=null;state.selectedIncident=null;state.selectedAssessment=null;await loadIncidents();el("incidentDetail").innerHTML='<div class="empty">Select an incident</div>';el("assessmentTab").innerHTML='<div class="empty">No incident selected.</div>';el("evidenceTab").innerHTML='<div class="empty">No evidence selected.</div>';el("selectedConfidence").textContent="—"
  }catch(error){toast(error.message)}
}
export async function generateSelectedReport(){
  if(!state.selectedIncidentId)return toast("Select an incident first");
  try{const response=await downloadReport(state.selectedIncidentId);const blob=await response.blob();const url=URL.createObjectURL(blob);const anchor=document.createElement("a");anchor.href=url;anchor.download=`mercury-incident-${state.selectedIncidentId}.json`;anchor.click();URL.revokeObjectURL(url);toast("JSON report downloaded")}catch(error){toast(error.message)}
}
