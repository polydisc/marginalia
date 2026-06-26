# Data model

The relational schema, owned by Alembic (`backend/alembic/versions/`). Entities
are separate aggregates and reference each other by id.

```mermaid
erDiagram
    works ||--o{ manifestations : has
    manifestations ||--o{ items : has
    manifestations ||--o{ holds : "is held"
    patrons ||--o{ loans : borrows
    patrons ||--o{ holds : places
    items ||--o{ loans : "is lent in"
    items |o--o{ holds : "is set aside for"

    works {
        int id PK
        string title
        string author
    }
    manifestations {
        int id PK
        int work_id FK
        string title
        string material_type
        string isbn "nullable"
        string publisher "nullable"
    }
    items {
        int id PK
        int manifestation_id FK
        string barcode UK
        string state
    }
    patrons {
        int id PK
        string card_number UK
        string category
        string status
        date expires_on "nullable"
    }
    loans {
        int id PK
        int item_id FK
        int patron_id FK
        datetime loaned_at
        date due_date
        datetime returned_at "nullable, null = open"
        int renewal_count
    }
    holds {
        int id PK
        int manifestation_id FK
        int patron_id FK
        datetime placed_at
        int queue_position
        string status
        int assigned_item_id FK "nullable"
        date pickup_by "nullable"
    }
```

## Notes

- `loans` has a partial unique index `uq_open_loan_per_item` on `item_id` where
  `returned_at IS NULL`. A copy can have at most one open loan. See
  [ADR 0003](adr/0003-loan-aggregate-db-constraint.md).
- `holds` has a partial unique index
  `uq_open_hold_per_patron_manifestation` on `(manifestation_id, patron_id)`
  where `status IN ('pending', 'ready')`. A patron cannot occupy multiple open
  queue slots for the same manifestation.
- An item's `on_loan` and `on_hold_shelf` are not columns. They are derived from
  an open loan and an assigned ready hold. `items.state` holds only the
  intrinsic state: `available`, `in_repair`, `lost`, `withdrawn`.
- `loans.due_date` and `holds.pickup_by` are dates. The rest of the time fields
  are timestamps.
- `material_type`, `category`, item `state`, and hold `status` store the enum
  value as a string. The enums live in `backend/app/domain/value_objects.py`.
