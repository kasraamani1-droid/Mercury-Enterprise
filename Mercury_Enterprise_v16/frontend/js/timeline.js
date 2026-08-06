import { esc, fmt } from "./utils.js";
export function buildTimelineEvents(incident){
  const real=Array.isArray(incident.events)?incident.events:[];
  if(real.length)return real;
  const base=new Date(incident.created_at||Date.now());
  const add=seconds=>new Date(base.getTime()+seconds*1000).toISOString();
  const confidence=String(incident.severity).toLowerCase()==="high"?88:72;
  return [
    {occurred_at:add(0),event_type:"detection",source:"RF-01",description:"Unknown airborne control signal detected.",confidence:confidence-8},
    {occurred_at:add(3),event_type:"visual",source:"Camera-02",description:"Electro-optical sensor acquired the target.",confidence},
    {occurred_at:add(6),event_type:"correlation",source:"Mercury AI",description:"RF and visual observations correlated.",confidence:confidence+3},
    {occurred_at:add(9),event_type:"assessment",source:"Mercury AI",description:`Threat classified ${String(incident.severity).toUpperCase()}.`,confidence:confidence+4}
  ];
}
export function renderTimeline(events){
  return events.map((event,index)=>`<article class="timeline-card"><span class="timeline-line"></span><span class="timeline-dot"></span><span class="badge">${esc(event.event_type)}</span><h3>${esc(event.description)}</h3><div class="meta">${fmt(event.occurred_at)} · ${esc(event.source)} · ${Math.round(Number(event.confidence)||0)}%</div></article>`).join("");
}
