import { el, toast, esc, download } from "./utils.js";
import { listConnectors, startConnector, stopConnector, recoverConnector } from "./api.js";

const topology=[["API Gateway","Online","3 regions"],["Incident Service","Online","6 replicas"],["AI Assessment","Online","4 workers"],["Event Stream","Online","12 partitions"],["Evidence Vault","Standby","Encrypted"],["Analytics","Online","2 replicas"]];
const catalogFallback=[["ADS-B / aircraft feed","Online","Aviation"],["EO/IR camera gateway","Online","Sensors"],["RF detection gateway","Online","Sensors"],["Airport operations API","Sandbox","Airport"],["Microsoft Teams","Online","Messaging"],["Email / SMTP","Online","Messaging"],["SIEM event export","Sandbox","Security"],["Weather / METAR","Online","Weather"],["Identity provider","Online","Access"],["Object storage","Online","Evidence"],["Patrol dispatch","Sandbox","Response"],["Webhook relay","Online","Developer"]];
const controls=[["Access control","94%","2 findings"],["Audit & accountability","96%","0 findings"],["Configuration management","91%","1 finding"],["Incident response","95%","0 findings"],["System integrity","89%","1 finding"],["Continuity & recovery","93%","0 findings"]];
let connectorRecords=[];

function rows(items){
  return items.map(x=>`<div><span class="health-dot online"></span><b>${esc(x[0])}<small>${esc(x[2])}</small></b><em>${esc(x[1])}</em></div>`).join("");
}

function renderConnectorCatalog(records){
  const node=el("integrationCatalog");
  if(!node)return;
  if(!records.length){
    node.innerHTML=rows(catalogFallback);
    return;
  }
  node.innerHTML=records.map(item=>{
    const state=String(item.state||"offline");
    const dot=state==="online"?"online":state==="degraded"?"degraded":"offline";
    return `<div data-connector-id="${esc(item.id)}">
      <span class="health-dot ${dot}"></span>
      <b>${esc(item.name)}<small>${esc(item.category)} · ${esc(item.provider)}</small></b>
      <em>${esc(state)}</em>
      <span class="connector-actions">
        <button type="button" data-connector-action="start" data-connector-id="${esc(item.id)}">Start</button>
        <button type="button" data-connector-action="stop" data-connector-id="${esc(item.id)}">Stop</button>
        <button type="button" data-connector-action="recover" data-connector-id="${esc(item.id)}">Recover</button>
      </span>
    </div>`;
  }).join("");
}

async function loadConnectorCatalog(){
  try{
    connectorRecords=await listConnectors();
    if(!Array.isArray(connectorRecords)) connectorRecords=[];
    renderConnectorCatalog(connectorRecords);
  }catch(error){
    connectorRecords=[];
    renderConnectorCatalog([]);
    const node=el("integrationCatalog");
    if(node && /insufficient|403|401|forbidden|authentication/i.test(String(error.message||""))){
      node.insertAdjacentHTML("afterbegin",`<div class="empty">${esc(error.message||"Connector visibility unavailable")}</div>`);
    }
  }
}

async function onConnectorAction(event){
  const button=event.target.closest("[data-connector-action]");
  if(!button) return;
  const id=button.dataset.connectorId;
  const action=button.dataset.connectorAction;
  try{
    if(action==="start") await startConnector(id);
    if(action==="stop") await stopConnector(id);
    if(action==="recover") await recoverConnector(id);
    toast(`Connector ${action} requested`);
    await loadConnectorCatalog();
  }catch(error){
    toast(error.message||`Unable to ${action} connector`);
  }
}

export async function refreshIntegrations(){
  await loadConnectorCatalog();
}

export function initializeEnterprise8(){
  el("cloudTopology").innerHTML=rows(topology);
  el("complianceControls").innerHTML=rows(controls);
  el("integrationCatalog")?.addEventListener("click",onConnectorAction);
  el("exportCloud")?.addEventListener("click",()=>download("mercury-v2.0-cloud-topology.json",{version:"16.0.0",simulated:true,topology}));
  el("exportIntegrations")?.addEventListener("click",()=>download("mercury-v16-integrations.json",{version:"16.0.0",simulated:true,connectors:connectorRecords,catalog:catalogFallback}));
  el("exportCompliance")?.addEventListener("click",()=>download("mercury-v16-controls.json",{version:"16.0.0",simulated:true,controls,disclaimer:"Demonstration only; no certification is claimed."}));
  loadConnectorCatalog();
  setInterval(()=>{const n=35+Math.floor(Math.random()*20);if(el("cloudLatency"))el("cloudLatency").textContent=`${n} ms`},3000);
  toast("Mercury Enterprise v16.0 initialized");
}
