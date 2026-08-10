import { el, esc } from "./utils.js";
import { state } from "./state.js";

const notifications=[];
const messages=[
  "RF-01 correlation increased above 90%.",
  "EO camera maintained visual lock on UAV-01.",
  "Radar track quality improved.",
  "Predicted runway conflict window updated.",
  "Nearby aircraft route deconfliction recalculated.",
  "Thermal sensor confirmed persistent target signature."
];

function renderNotifications(){
  const list=el("notificationList");
  const count=el("notificationCount");
  count.textContent=String(notifications.length);
  count.classList.toggle("active",notifications.length>0);
  list.innerHTML=notifications.length?notifications.map((n,i)=>`<article class="notification-item ${i===0?"latest":""}"><time>${esc(n.time)}</time><strong>${esc(n.title)}</strong><span>${esc(n.text)}</span></article>`).join(""):'<div class="empty">No notifications.</div>';
}

export function pushNotification(title,text){
  notifications.unshift({title,text,time:new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"})});
  notifications.splice(10);
  renderNotifications();
}

export function initializeCommandCenter(){
  el("notificationButton").addEventListener("click",()=>el("notificationCenter").classList.toggle("hidden"));
  el("clearNotifications").addEventListener("click",()=>{notifications.length=0;renderNotifications()});
  document.addEventListener("click",event=>{
    const panel=el("notificationCenter"),button=el("notificationButton");
    if(!panel.classList.contains("hidden")&&!panel.contains(event.target)&&!button.contains(event.target))panel.classList.add("hidden");
  });
  renderNotifications();
  pushNotification("System ready","Mercury Enterprise V2.0 (16.0.0) integrated services are online.");
}

export function updateCommandCenter(step=0){
  const temp=12+Math.round(Math.sin(step/4)*2);
  const pressure=1014+Math.round(Math.cos(step/5)*3);
  const gps=step%9===0?"FAIR":"GOOD";
  el("weatherDetails").textContent=`${temp}°C · ${pressure} hPa · GPS ${gps}`;
  const sweep=el("radarSweep");
  sweep.classList.toggle("critical",state.dynamicThreat>=90);
  if(step>0&&step%3===0)pushNotification(state.dynamicThreat>=90?"High-priority update":"Sensor update",messages[step%messages.length]);
}
