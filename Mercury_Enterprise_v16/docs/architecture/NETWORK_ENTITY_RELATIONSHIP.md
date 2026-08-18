# Aviation Network — Entity Relationship

```
Organization
  ├── NetworkOrgProfile (typed profiles; directory opt-in)
  ├── NetworkProfessionalProfile (username + role)
  ├── NetworkPartnership ──► partner_organization_id
  │         ├── NetworkCollaboration
  │         ├── NetworkDocumentShare
  │         └── NetworkMessageThread ──► NetworkMessage
  ├── NetworkEvent
  └── NetworkDirectoryEntry (search projection)
```

## Tables

| Table | Purpose |
|-------|---------|
| `network_org_profiles` | Company network profile |
| `network_professional_profiles` | Professional profiles |
| `network_partnerships` | Explicit relationships + permissions |
| `network_collaborations` | Authorized collaboration requests |
| `network_document_shares` | Controlled document sharing |
| `network_message_threads` | Secure messaging threads |
| `network_messages` | Thread messages |
| `network_events` | Published network events |
| `network_directory_entries` | Directory search index |

Alembic: `20260814_0017`.
