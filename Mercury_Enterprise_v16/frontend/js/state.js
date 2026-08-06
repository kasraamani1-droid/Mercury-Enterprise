export const state = {
  incidents: [], selectedIncidentId: null, selectedIncident: null, selectedAssessment: null,
  operatorLog: [], map: null, droneMarker: null, droneTrail: null, dronePath: [],
  trackingTimer: null, trackingIndex: 0, simulationSpeed: 1, aircraftMarkers: [], aircraftIndex: 0,
  sensorMarkers: [], zoneLayers: [], trailLayer: null, layersVisible: {zones:true,sensors:true,aircraft:true,trail:true},
  fusion: {rf:92,radar:84,eo:97,thermal:88,adsb:100}, liveEvents: [], missionStarted:null, missionElapsed:0, replayMode:false, dynamicThreat:92, secondaryDrone:null, secondaryTrail:null, criticalAlertShown:false
};
