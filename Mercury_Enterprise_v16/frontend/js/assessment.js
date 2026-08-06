import { esc } from "./utils.js";
export function renderAssessment(assessment){
  return `<div class="assessment-card"><div class="assessment-head"><h3>🧠 AI THREAT ASSESSMENT</h3><span class="level ${esc(String(assessment.level).toLowerCase())}">${esc(assessment.level)}</span></div><div class="metric-row"><strong>Threat score</strong><span>${assessment.score}/100</span></div><div class="bar"><span style="width:${Math.max(0,Math.min(100,assessment.score))}%"></span></div><div class="metric-row"><strong>AI confidence</strong><span>${assessment.score}%</span></div><h4>Reasoning</h4><ul>${assessment.reasoning.map(x=>`<li>${esc(x)}</li>`).join("")}</ul><h4>Recommended actions</h4><ul class="recommendations">${assessment.recommendations.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
}
