import { el, toast, esc, download } from "./utils.js";
import { state } from "./state.js";
import { listAudit, getReportSummary, getReportHistory } from "./api.js";
import { refreshIntegrations } from "./enterprise8.js";

const workspaces=["command","digitalTwin","radar","executive","history","admin","cloud","integrations","compliance"];
let serverAudits=[];
let historyRows=[];
let latestSummary=null;
const contacts=[
  ["UAV-01","UNKNOWN","2.1 NM","146°","134 m","CRITICAL"],
  ["UAV-02","UNKNOWN","3.8 NM","278°","86 m","MEDIUM"],
  ["ACA875","FRIENDLY","4.2 NM","094°","220 kt","CLEARED"],
  ["PD217","FRIENDLY","6.7 NM","181°","290 kt","CLEARED"],
  ["TS742","FRIENDLY","7.4 NM","032°","255 kt","CLEARED"]
];
const people=[
  ["Kasra Amani","Commander","ONLINE"],["Maya Chen","Supervisor","ONLINE"],["Sam Patel","EO Operator","ONLINE"],["Alex Roy","Airside Patrol","EN ROUTE"],["Jordan Singh","Radar","ONLINE"]
];
const roles={
  Commander:"Full command authority, incident resolution, exports, role assignment and system controls.",
  Supervisor:"Incident oversight, evidence review, reporting and operator assignment.",
  Operator:"Track targets, acknowledge alerts, execute assigned response actions and preserve evidence.",
  "Read Only":"View live operations, history and executive dashboards. No operational actions."
};

function renderAudit(){
  const node=el("auditLog");
  if(!node)return;
  if(!serverAudits.length){
    node.innerHTML='<div class="empty">No session activity.</div>';
    return;
  }
  node.innerHTML=serverAudits.map(item=>{
    const when=item.occurred_at?new Date(item.occurred_at).toLocaleString():"";
    const actor=item.actor_role?`${item.actor} (${item.actor_role})`:item.actor;
    const detail=[item.action,item.site_id,item.origin,item.details].filter(Boolean).join(" · ");
    return `<div class="audit-entry"><time>${esc(when)}</time><b>${esc(actor||"—")}</b><span>${esc(detail)}</span></div>`;
  }).join("");
}

async function loadServerAudit(){
  const node=el("auditLog");
  try{
    serverAudits=await listAudit({limit:100});
    if(!Array.isArray(serverAudits))serverAudits=[];
    renderAudit();
  }catch(error){
    serverAudits=[];
    if(node){
      const message=String(error?.message||error);
      if(/insufficient|403|forbidden/i.test(message)){
        node.innerHTML='<div class="empty">Insufficient permissions for audit review.</div>';
      }else{
        node.innerHTML=`<div class="empty">${esc(message)}</div>`;
      }
    }
  }
}

export async function refreshEnterpriseAudit(){
  await loadServerAudit();
}
function renderExecutive(summary){
  latestSummary=summary;
  const kpis=summary?.kpis||{};
  if(el("execIncidentsTotal")) el("execIncidentsTotal").textContent=String(kpis.incidents_total ?? "—");
  if(el("execIncidentsNote")) el("execIncidentsNote").textContent=`Open ${kpis.incidents_open ?? 0} · site ${summary?.site_id||"—"}`;
  if(el("execMedianResponse")) {
    el("execMedianResponse").textContent=kpis.median_response_seconds==null?"—":`${kpis.median_response_seconds} s`;
  }
  if(el("execConnectorOnline")) el("execConnectorOnline").textContent=String(kpis.connector_online ?? "—");
  if(el("execConnectorNote")) {
    el("execConnectorNote").textContent=`Degraded ${kpis.connector_degraded ?? 0} · Error ${kpis.connector_error ?? 0}`;
  }
  if(el("execResolutionRate")) el("execResolutionRate").textContent=`${kpis.resolution_rate ?? 0}%`;
  if(el("execResolutionNote")) {
    el("execResolutionNote").textContent=`${kpis.incidents_resolved ?? 0} of ${kpis.incidents_total ?? 0} resolved`;
  }
  const trend=summary?.trends?.incidents_by_hour||[];
  const values=trend.length?trend.map(item=>Number(item.count)||0):Array(24).fill(0);
  const max=Math.max(1,...values);
  el("hourlyChart").innerHTML=values.map((v,i)=>`<i style="height:${Math.round((v/max)*80)+18}px" data-label="${String(i).padStart(2,"0")}:00"></i>`).join("");
}

async function loadExecutive(){
  try{
    const summary=await getReportSummary();
    renderExecutive(summary);
  }catch(error){
    toast(error.message||"Unable to load executive report");
  }
}

function renderHistory(filter=""){
  const q=filter.toLowerCase();
  const rows=historyRows.filter(r=>Object.values(r).join(" ").toLowerCase().includes(q));
  el("historyBody").innerHTML=rows.length?rows.map(r=>{
    const severity=String(r.severity||"").toLowerCase();
    const provenance=r.provenance?` · ${r.provenance}`:"";
    return `<tr>
      <td>${esc(r.id||"")}</td>
      <td>${esc(r.site_id||"")}</td>
      <td>${esc(r.type||r.title||"")}</td>
      <td><span class="severity ${esc(severity)}">${esc(r.severity||"")}</span></td>
      <td>${esc(r.status||"")}</td>
      <td>${esc(r.detected_at?new Date(r.detected_at).toLocaleString():"")}</td>
      <td>${esc(r.response_seconds!=null?`${r.response_seconds} s`:"")}</td>
      <td>${esc((r.operator||"")+provenance)}</td>
    </tr>`;
  }).join(""):'<tr><td colspan="8">No historical records for current site/window.</td></tr>';
}

async function loadHistory(){
  try{
    historyRows=await getReportHistory({limit:200});
    if(!Array.isArray(historyRows)) historyRows=[];
    renderHistory(el("historySearch")?.value||"");
  }catch(error){
    historyRows=[];
    el("historyBody").innerHTML=`<tr><td colspan="8">${esc(error.message||"Unable to load history")}</td></tr>`;
  }
}

export async function refreshEnterpriseReports(){
  await Promise.allSettled([loadExecutive(), loadHistory()]);
}

function showWorkspace(name){
  workspaces.forEach(x=>{el(`${x}Workspace`)?.classList.toggle("hidden",x!==name);el(`${x}Workspace`)?.classList.toggle("active",x===name)});
  document.querySelectorAll(".product-tab").forEach(b=>b.classList.toggle("active",b.dataset.workspace===name));
  if(name==="admin")loadServerAudit();
  if(name==="executive")loadExecutive();
  if(name==="history")loadHistory();
  if(name==="integrations")refreshIntegrations();
  if(name==="digitalTwin")updateTwin();
}
function renderContacts(){el("radarContacts").innerHTML=contacts.map(r=>`<div class="contact-row"><b>${r[0]}</b><span>${r[1]}<small>${r[2]} · ${r[3]}</small></span><em>${r[5]}</em></div>`).join("")}
function renderPresence(){const html=people.map(p=>`<div><span>●</span><b>${p[0]}<small>${p[1]}</small></b><em>${p[2]}</em></div>`).join("");el("operatorPresence").innerHTML=html;el("responseUnits").innerHTML=people.slice(2).map(p=>`<div><span>●</span><b>${p[0]}<small>${p[1]}</small></b><em>${p[2]}</em></div>`).join("")}
function updateTwin(){el("twinAltitude").textContent=el("targetAltitude")?.textContent||"120 m";el("twinTargetCount").textContent=`${state.secondaryDrone?2:1} TARGETS`}
export function initializeEnterprise(){
 document.querySelectorAll(".product-tab").forEach(b=>b.addEventListener("click",()=>showWorkspace(b.dataset.workspace)));
 el("twinViewToggle")?.addEventListener("click",()=>{const stage=document.querySelector(".twin-stage");stage.classList.toggle("perspective");el("twinViewToggle").textContent=stage.classList.contains("perspective")?"Switch to Top View":"Switch to 3D Perspective"});
 el("centerTwin")?.addEventListener("click",()=>toast("Digital Twin centered on CYUL"));
 el("historySearch")?.addEventListener("input",e=>renderHistory(e.target.value));
 el("exportHistory")?.addEventListener("click",()=>{
   const header="ID,Airport,Type,Severity,Status,Detected,Response,Operator,Provenance";
   const lines=historyRows.map(r=>[r.id,r.site_id,r.type||r.title,r.severity,r.status,r.detected_at,r.response_seconds,r.operator,r.provenance].join(","));
   download("mercury-history.csv",[header,...lines].join("\n"),"text/csv");
 });
 el("exportExecutive")?.addEventListener("click",async()=>{
   try{
     const summary=latestSummary||await getReportSummary();
     download("mercury-executive-summary.json",JSON.stringify(summary,null,2));
   }catch(error){
     toast(error.message||"Unable to export executive summary");
   }
 });
 el("downloadAudit")?.addEventListener("click",async()=>{
   try{
     const rows=serverAudits.length?serverAudits:await listAudit({limit:100});
     download("mercury-audit-log.json",JSON.stringify(rows,null,2));
   }catch(error){
     toast(error.message||"Unable to download audit log");
   }
 });
 el("roleSelect")?.addEventListener("change",e=>{el("permissionSummary").textContent=roles[e.target.value]});
 renderContacts();renderPresence();el("permissionSummary").textContent=roles.Commander;
}
export function updateEnterprise(){updateTwin()}
