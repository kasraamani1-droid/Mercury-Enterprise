# MERCURY ENTERPRISE v16
## TASK 4 — Timeline Engine

Branch:
develop

Commit after completion:
Sprint 4 - Timeline Engine

--------------------------------------------

GOAL

Create the mission timeline system used by Command Center.

This timeline records every important event occurring during a mission.

Example:

Mission Started

Drone detected

Radar confirmed

Camera locked

Threat classified

Operator acknowledged

Interceptor launched

Mission complete

--------------------------------------------

CREATE

backend/app/timeline/

Inside create:

__init__.py

timeline.py

timeline_models.py

--------------------------------------------

TimelineEntry

Store

id

timestamp

event_type

severity

source

message

metadata

--------------------------------------------

TimelineManager

Functions

add_event()

get_events()

clear()

last()

export_json()

--------------------------------------------

Timeline events should automatically subscribe to EventBus.

Whenever EventBus publishes an event,
TimelineManager records it.

--------------------------------------------

Support

Filtering

Sorting

Maximum history size

JSON export

--------------------------------------------

Integrate into

backend/app/main.py

Initialize timeline manager during startup.

--------------------------------------------

QUALITY

Use

type hints

logging

docstrings

clean architecture

thread safety

--------------------------------------------

TEST

Create

backend/tests/test_timeline.py

Test

adding events

event subscription

ordering

JSON export

--------------------------------------------

Do NOT modify frontend.

Backend only.

--------------------------------------------

When complete execute

python -m compileall app

Commit

Sprint 4 - Timeline Engine

Push develop
