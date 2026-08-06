import { state } from "./state.js";
import { el, esc } from "./utils.js";
export function addLog(message){state.operatorLog.unshift({message,time:new Date()});renderLog()}
export function clearLog(){state.operatorLog=[];renderLog()}
export function renderLog(){el("eventLog").innerHTML=state.operatorLog.length?state.operatorLog.map(x=>`<div class="log-entry"><strong>${esc(x.message)}</strong><time>${x.time.toLocaleTimeString()}</time></div>`).join(""):'<div class="empty">No operator activity.</div>'}
