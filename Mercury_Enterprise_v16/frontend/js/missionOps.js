import { state } from "./state.js";
import { el, toast } from "./utils.js";

const briefs = [
  "Primary track remains inside the protected zone. Maintain EO and RF correlation.",
  "Runway conflict window is narrowing. Confirm ATC coordination and patrol status.",
  "Secondary track remains outside the inner ring. Continue monitoring; no escalation yet.",
  "Wind is from the west at 18 km/h. Predicted UAV drift is toward the east apron.",
  "Sensor agreement is above 90%. Evidence preservation is recommended before resolution."
];

export function initializeMissionOps(){
  updateWeather();
  updateTaskProgress();
  document.querySelectorAll("[data-task]").forEach(box=>box.addEventListener("change",()=>{
    box.closest(".task-item").classList.toggle("done",box.checked);
    updateTaskProgress();
    toast(`${box.dataset.task}: ${box.checked?"complete":"reopened"}`);
  }));
}

export function updateTaskProgress(){
  const tasks=[...document.querySelectorAll("[data-task]")];
  const done=tasks.filter(x=>x.checked).length;
  el("taskProgress").textContent=`${done}/${tasks.length} complete`;
}

export function updateWeather(step=0){
  const wind=18+Math.round(Math.sin(step/3)*3);
  const visibility=24-Math.round(Math.abs(Math.sin(step/5))*4);
  el("weatherSummary").textContent=`${wind} km/h · ${visibility} km`;
}

export function updateProactiveBrief(step=0){
  if(!state.selectedIncidentId)return;
  const panel=el("proactiveBrief");
  panel.querySelector("span").textContent=briefs[step%briefs.length];
  panel.classList.remove("mission-update");
  void panel.offsetWidth;
  panel.classList.add("mission-update");
}
