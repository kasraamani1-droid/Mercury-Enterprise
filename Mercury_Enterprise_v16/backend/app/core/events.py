from enum import StrEnum


class EventType(StrEnum):
    DRONE_DETECTED = "drone.detected"
    MISSION_CREATED = "mission.created"
    MISSION_UPDATED = "mission.updated"
    MISSION_STARTED = "mission.started"
    MISSION_PAUSED = "mission.paused"
    MISSION_RESUMED = "mission.resumed"
    MISSION_COMPLETED = "mission.completed"
    MISSION_CANCELLED = "mission.cancelled"
    MISSION_ARCHIVED = "mission.archived"
    MISSION_OBJECTIVE_CREATED = "mission.objective_created"
    MISSION_OBJECTIVE_UPDATED = "mission.objective_updated"
    MISSION_OBJECTIVE_COMPLETED = "mission.objective_completed"
    MISSION_RESOURCE_ASSIGNED = "mission.resource_assigned"
    MISSION_RESOURCE_RELEASED = "mission.resource_released"
    MISSION_OPERATOR_ASSIGNED = "mission.operator_assigned"
    MISSION_OPERATOR_REMOVED = "mission.operator_removed"
    MISSION_STOPPED = "mission.stopped"
    AIRCRAFT_DETECTED = "aircraft.detected"
    AIRCRAFT_LANDED = "aircraft.landed"
    AIRCRAFT_TAKEOFF = "aircraft.takeoff"

    RADAR_CONTACT = "sensor.radar_contact"
    RF_SIGNAL = "sensor.rf_signal"
    CAMERA_DETECTION = "sensor.camera_detection"

    AI_ALERT = "ai.alert"

    WEATHER_UPDATE = "weather.updated"
    NOTAM_UPDATE = "notam.updated"

    TRACK_LOST = "track.lost"
    TRACK_REACQUIRED = "track.reacquired"

    SYSTEM_WARNING = "system.warning"
    SYSTEM_ERROR = "system.error"