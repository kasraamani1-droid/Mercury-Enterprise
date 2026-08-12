export function resolveApiBase() {
  if (typeof window !== "undefined" && window.__MERCURY_API_BASE__) {
    return String(window.__MERCURY_API_BASE__).replace(/\/$/, "");
  }
  if (typeof document !== "undefined") {
    const meta = document.querySelector('meta[name="mercury-api-base"]');
    const content = meta && meta.getAttribute("content");
    if (content && content.trim()) {
      return content.trim().replace(/\/$/, "");
    }
  }
  return "/api/v1";
}

export function resolveWsUrl() {
  if (typeof window !== "undefined" && window.__MERCURY_WS_URL__) {
    return String(window.__MERCURY_WS_URL__);
  }
  if (typeof window === "undefined" || !window.location) {
    return "ws://localhost/api/v1/ws";
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1/ws`;
}

/** Same-origin relative API by default; override via window.__MERCURY_API_BASE__ or meta mercury-api-base. */
export const API_BASE = resolveApiBase();

export const AIRPORTS = {
  CYUL: { name: "Montréal–Trudeau", center: [45.4706, -73.7408], zoom: 13 },
  CYYZ: { name: "Toronto Pearson", center: [43.6777, -79.6248], zoom: 13 },
  CYVR: { name: "Vancouver International", center: [49.1967, -123.1815], zoom: 13 }
};
export const AIRPORT = AIRPORTS.CYUL.center;
export const UAV_TRACK = [
  [45.488, -73.765], [45.486, -73.757], [45.483, -73.748],
  [45.480, -73.738], [45.477, -73.728], [45.474, -73.720],
  [45.471, -73.727], [45.469, -73.737]
];
export const SENSOR_SITES = [
  {id:"RF-01",type:"RF",position:[45.475,-73.759],reliability:94},
  {id:"CAM-02",type:"EO",position:[45.461,-73.724],reliability:97},
  {id:"RADAR-01",type:"Radar",position:[45.482,-73.713],reliability:89},
  {id:"THERM-01",type:"Thermal",position:[45.466,-73.772],reliability:86}
];
export const AIRCRAFT_TRACKS = [
  {callsign:"ACA875",points:[[45.502,-73.705],[45.494,-73.715],[45.486,-73.725],[45.478,-73.735]]},
  {callsign:"TS742",points:[[45.445,-73.795],[45.451,-73.781],[45.458,-73.767],[45.465,-73.753]]},
  {callsign:"PD217",points:[[45.507,-73.805],[45.501,-73.789],[45.495,-73.773],[45.489,-73.757]]}
];
export const SEVERITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

export const UAV_TRACK_2 = UAV_TRACK.map(([a,b],i)=>[a-0.012+Math.sin(i)*0.002,b+0.018]);
