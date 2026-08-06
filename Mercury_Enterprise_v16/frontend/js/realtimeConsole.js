import { el } from './utils.js';
import { state } from './state.js';
import { pushNotification } from './commandCenter.js';

let uptimeStart = Date.now();
let lastNarrationStep = -1;
let narrationMuted = false;

const phaseForThreat = score => {
  if (score >= 90) return 'CRITICAL RESPONSE';
  if (score >= 80) return 'INTERDICTION';
  if (score >= 65) return 'VERIFICATION';
  return 'DETECTION';
};

const fmtClock = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;

function updateClocks() {
  const now = new Date();
  el('utcClock').textContent = now.toLocaleTimeString('en-GB', { timeZone: 'UTC', hour12: false });
  el('localClock').textContent = now.toLocaleTimeString([], { hour12: false });
  el('systemUptime').textContent = fmtClock(Math.floor((Date.now() - uptimeStart) / 1000));
}

function updateMissionOverview() {
  const threat = state.dynamicThreat || 0;
  el('missionPhase').textContent = phaseForThreat(threat);
  el('activeTargets').textContent = threat >= 70 ? '2' : '1';
  el('currentRisk').textContent = threat >= 90 ? 'CRITICAL' : threat >= 75 ? 'HIGH' : 'ELEVATED';
  el('currentRisk').className = `risk-value ${threat >= 90 ? 'critical' : threat >= 75 ? 'high' : 'elevated'}`;
  el('nearestAircraft').textContent = `${Math.max(0.8, 4.2 - (state.trackingIndex || 0) * 0.35).toFixed(1)} km`;
}

function buildNarration(step) {
  const threat = state.dynamicThreat || 0;
  const eta = el('targetEta')?.textContent || 'unknown';
  const altitude = el('targetAltitude')?.textContent || 'unknown';
  const confidence = el('selectedConfidence')?.textContent || 'unknown';
  if (threat >= 90) return `Critical update: UAV-01 remains inside the runway protection zone at ${altitude}. Fused confidence is ${confidence}. Estimated runway arrival is ${eta}. Immediate ATC coordination and patrol dispatch are recommended.`;
  if (threat >= 80) return `Operational update: UAV-01 is converging toward protected airspace. Confidence is ${confidence}, with runway arrival estimated in ${eta}. Maintain sensor lock and prepare airside response.`;
  return `Monitoring update: UAV-01 remains under multi-sensor observation. Current confidence is ${confidence}. Continue tracking while the fusion engine evaluates intent.`;
}

export function updateRealtimeConsole(step = 0) {
  updateMissionOverview();
  if (step > 0 && step % 3 === 0 && step !== lastNarrationStep) {
    lastNarrationStep = step;
    const narration = buildNarration(step);
    el('autoNarration').textContent = narration;
    el('autoNarration').classList.remove('narration-pulse');
    void el('autoNarration').offsetWidth;
    el('autoNarration').classList.add('narration-pulse');
    if (!narrationMuted && state.dynamicThreat >= 90) pushNotification('Mercury Copilot', narration);
  }
}

export function initializeRealtimeConsole() {
  updateClocks();
  updateMissionOverview();
  setInterval(updateClocks, 1000);
  el('muteNarration').addEventListener('click', () => {
    narrationMuted = !narrationMuted;
    el('muteNarration').textContent = narrationMuted ? '🔇 Muted' : '🔊 Alerts';
  });
}
