# Go-Live Tracker

Where we are, what's done, and **what I need from you** to connect real data and host.

## ✅ Done (no real DB needed)
- **Two-database split** — the app reads from a **read-only appraisal DB** and writes its own data (templates, history, saved items) to a **separate app DB**. Routing is automatic; locally both point at the demo DB.
- **Read-only enforced** — in `production` mode the app never creates/alters/seeds the appraisal DB (`APP_ENV=production` gates all of it). Per the rule: *we only read, never write.*
- **Deploy scaffolding** — `Dockerfile` (builds the frontend, serves it + the API from one container), same-origin so no CORS, Cloud Run `$PORT` ready.
- **Flattening view (DRAFT)** — `backend/sql/appraisal_flat_view.sql` maps the real normalized schema → the flat shape the tool expects (enum→label, cents→USD, largest stone per piece). Untested until we connect.
- **Map bundled** — US topojson is local now (works offline / in cloud).

## ⛔ What I need from you (the blockers)

### 1. Read-only access to the real appraisal Postgres
- A **read-only role** (SELECT-only) + connection string: host, port, database, user, password.
- **Network path** from Cloud Run: the **Cloud SQL instance connection name** (`project:region:instance`) if it's Cloud SQL, or an IP allowlist.

### 2. A separate app database (read/write)
- A **new Postgres** (Cloud SQL instance or a dedicated database/schema we're allowed to write to) for the app's own tables. Connection string with read/write.

### 3. Keys / secrets (in Secret Manager)
- `ANTHROPIC_API_KEY` — turns Fact Finder + narratives + image edits live.
- The two DB connection strings (appraisal read-only, app read/write).

### 4. GCP deploy access
- Project ID + region, and permission to deploy a **Cloud Run** service (same pattern as your other BriteCo apps).

## Deploy-time environment variables
| Var | Value |
|-----|-------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | appraisal DB (read-only role) |
| `APP_DATABASE_URL` | app DB (read/write) |
| `ANTHROPIC_API_KEY` | from Secret Manager |

## 🔜 What I do once I have the above
1. Run the flattening view against the real DB and **reconcile the semantic layer** to it (verify enum maps, drop `generation` — not in the schema, adjust gemstone color, etc.).
2. **Validate** a handful of numbers against your live dashboards.
3. Deploy to Cloud Run and smoke-test.

## Open schema notes (from the mapping docs)
- Data is **normalized** (appraisals → jewelry_pieces → stones; watches polymorphic) and **enum-coded**; values in **cents**.
- **No generation/birthdate** field → that cut goes away (geography via `addresses.state` still works).
- "Engagement Ring" = `category = 1 AND piece_type = 1`.
