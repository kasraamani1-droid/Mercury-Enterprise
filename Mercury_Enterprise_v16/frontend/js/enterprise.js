import { el, toast } from "./utils.js";
import { state } from "./state.js";

const workspaces=["command","digitalTwin","radar","executive","history","admin","cloud","integrations","compliance"];
const audits=[];
const historyRows=[
  ["INC-30018","CYUL","Unauthorized UAV","HIGH","Open","12:17","34 s","K. Amani"],
  ["INC-30017","CYUL","Unknown RF","MEDIUM","Resolved","11:42","51 s","M. Chen"],
  ["INC-30016","CYYZ","Perimeter vehicle","HIGH","Resolved","10:28","42 s","S. Patel"],
  ["INC-30015","CYVR","Bird activity","LOW","Resolved","09:51","38 s","A. Roy"],
  ["INC-30014","CYUL","Laser illumination","HIGH","Resolved","08:36","29 s","K. Amani"],
  ["INC-30013","CYYZ","Unknown track","MEDIUM","Resolved","07:14","47 s","L. Martin"],
  ["INC-30012","CYUL","Drone near apron","HIGH","Resolved","06:49","31 s","K. Amani"],
  ["INC-30011","CYVR","RF anomaly","LOW","Resolved","05:22","55 s","J. Singh"]
];
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
function addAudit(action){audits.unshift({time:new Date().toLocaleTimeString(),actor:el("roleSelect")?.value||"Commander",action});audits.splice(30);renderAudit()}
function renderAudit(){const node=el("auditLog");if(!node)return;node.innerHTML=audits.map(x=>`<div class="audit-entry"><time>${x.time}</time><b>${x.actor}</b><span>${x.action}</span></div>`).join("")||'<div class="empty">No session activity.</div>'}
function download(name,data,type="application/json"){const blob=new Blob([data],{type});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
function showWorkspace(name){workspaces.forEach(x=>{el(`${x}Workspace`)?.classList.toggle("hidden",x!==name);el(`${x}Workspace`)?.classList.toggle("active",x===name)});document.querySelectorAll(".product-tab").forEach(b=>b.classList.toggle("active",b.dataset.workspace===name));addAudit(`Opened ${name} workspace`);if(name==="digitalTwin")updateTwin();}
function renderHistory(filter=""){const q=filter.toLowerCase();el("historyBody").innerHTML=historyRows.filter(r=>r.join(" ").toLowerCase().includes(q)).map(r=>`<tr>${r.map((v,i)=>`<td>${i===3?`<span class="severity ${String(v).toLowerCase()}">${v}</span>`:v}</td>`).join("")}</tr>`).join("")}
function renderContacts(){el("radarContacts").innerHTML=contacts.map(r=>`<div class="contact-row"><b>${r[0]}</b><span>${r[1]}<small>${r[2]} · ${r[3]}</small></span><em>${r[5]}</em></div>`).join("")}
function renderPresence(){const html=people.map(p=>`<div><span>●</span><b>${p[0]}<small>${p[1]}</small></b><em>${p[2]}</em></div>`).join("");el("operatorPresence").innerHTML=html;el("responseUnits").innerHTML=people.slice(2).map(p=>`<div><span>●</span><b>${p[0]}<small>${p[1]}</small></b><em>${p[2]}</em></div>`).join("")}
function renderChart(){const values=[2,4,3,7,5,9,12,8,6,10,7,4];el("hourlyChart").innerHTML=values.map((v,i)=>`<i style="height:${v*8+18}px" data-label="${String(i+6).padStart(2,"0")}:00"></i>`).join("")}
function updateTwin(){el("twinAltitude").textContent=el("targetAltitude")?.textContent||"120 m";el("twinTargetCount").textContent=`${state.secondaryDrone?2:1} TARGETS`}
function executiveData(){return {generated_at:new Date().toISOString(),airport:"CYUL",incidents_today:14,median_response_seconds:34,sensor_availability_percent:98.7,resolution_rate_percent:92,system_status:"OPERATIONAL",note:"Simulated demonstration data"}}
export function initializeEnterprise(){
 document.querySelectorAll(".product-tab").forEach(b=>b.addEventListener("click",()=>showWorkspace(b.dataset.workspace)));
 el("twinViewToggle")?.addEventListener("click",()=>{const stage=document.querySelector(".twin-stage");stage.classList.toggle("perspective");el("twinViewToggle").textContent=stage.classList.contains("perspective")?"Switch to Top View":"Switch to 3D Perspective";addAudit("Changed Digital Twin perspective")});
 el("centerTwin")?.addEventListener("click",()=>toast("Digital Twin centered on CYUL"));
 el("historySearch")?.addEventListener("input",e=>renderHistory(e.target.value));
 el("exportHistory")?.addEventListener("click",()=>{download("mercury-history.csv",["ID,Airport,Type,Severity,Status,Detected,Response,Operator",...historyRows.map(r=>r.join(","))].join("\n"),"text/csv");addAudit("Exported incident history CSV")});
 el("exportExecutive")?.addEventListener("click",()=>{download("mercury-executive-summary.json",JSON.stringify(executiveData(),null,2));addAudit("Exported executive summary")});
 el("downloadAudit")?.addEventListener("click",()=>download("mercury-audit-log.json",JSON.stringify(audits,null,2)));
 el("roleSelect")?.addEventListener("change",e=>{el("permissionSummary").textContent=roles[e.target.value];addAudit(`Changed role simulation to ${e.target.value}`)});
 renderHistory();renderContacts();renderPresence();renderChart();renderAudit();el("permissionSummary").textContent=roles.Commander;addAudit("Mercury v16.0 enterprise session initialized");
}
export function updateEnterprise(){updateTwin()}
