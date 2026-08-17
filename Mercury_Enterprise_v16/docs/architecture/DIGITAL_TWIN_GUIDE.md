# Digital Twin Guide

## What a twin is

A Digital Twin is the authoritative lifecycle record for one aviation asset or entity. It answers:

- What is this object?
- Who owns it now / previously?
- How is it configured?
- What happened to it (install, remove, inspect, repair, modify)?
- Which SB/AD apply (compliance refs)?
- What are its architecture reliability metrics?
- Where is its permanent passport?

## Twin types

Aircraft, Engine, APU, Landing Gear, Propeller, Flight Control, Serialized/Non-serialized Component, Tool, Test Equipment, GSE, Hangar, Facility, Organization, Personnel.

## Contained data (model)

Permanent UUID, Digital Passport link, ownership, configuration baselines, installation/removal/maintenance/inspection/repair/modification history, SB/AD compliance JSON, LLP, utilization, certificates/documents/publications/images/attachments/signatures refs, relationship summary, audit via history + AuditEngine, AI metadata.

## Not included (explicit)

- Live 3D rendering (future visualization hooks only)
- Live reliability analytics engines (snapshots + architecture flags)
- Autonomous AI answers (metadata questions ready only)
