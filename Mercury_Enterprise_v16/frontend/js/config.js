export const API_BASE = "http://127.0.0.1:8000/api/v1";
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
