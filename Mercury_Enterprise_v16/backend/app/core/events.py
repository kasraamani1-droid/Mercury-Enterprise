from enum import StrEnum


class EventType(StrEnum):
    DRONE_DETECTED = "drone.detected"
    AIRCRAFT_DETECTED = "aircraft.detected"
    AIRCRAFT_LANDED = "aircraft.landed"
    AIRCRAFT_TAKEOFF = "aircraft.takeoff"

    RADAR_CONTACT = "sensor.radar_contact"
    RF_SIGNAL = "sensor.rf_signal"
    CAMERA_DETECTION = "sensor.camera_detection"

    AI_ALERT = "ai.alert"

    WEATHER_UPDATE = "weather.updated"
    NOTAM_UPDATE = "notam.updated"

    MISSION_STARTED = "mission.started"
    MISSION_STOPPED = "mission.stopped"
    MISSION_COMPLETED = "mission.completed"

    TRACK_LOST = "track.lost"
    TRACK_REACQUIRED = "track.reacquired"

    SYSTEM_WARNING = "system.warning"
    SYSTEM_ERROR = "system.error"