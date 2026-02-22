# Music DB

A personal music library database for cataloguing albums with full metadata — musicians, personnel, record labels, cover art, and track listings. Built as a self-hosted web app running entirely in Docker.

---

## Features

- **Album catalogue** — store title, artist, release year, record label, producer, track listing, and cover art
- **Musicians & personnel** — tag albums with performers (instrument) and crew (role: producer, engineer, etc.)
- **Collections** — organise albums into named collections
- **MusicBrainz integration** — search and auto-populate album metadata and cover art from MusicBrainz
- **Roon import** — bulk-import your entire Roon library in the background with progress tracking
- **File scanner** — scan a directory tree of audio files (FLAC, MP3, M4A, AIFF, OGG, WAV) for import without Roon
- **Cover art fallback** — embedded art → folder images → MusicBrainz Cover Art Archive
- **JWT authentication** — user accounts with 7-day tokens

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Data validation | [Pydantic v2](https://docs.pydantic.dev/latest/) |
| ORM | [SQLAlchemy 2 (async)](https://docs.sqlalchemy.org/en/20/) |
| Database | SQLite via `aiosqlite` |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) |
| Python package manager | [uv](https://docs.astral.sh/uv/) |
| Audio tag reading | [mutagen](https://mutagen.readthedocs.io/) |
| Frontend framework | [Nuxt 3](https://nuxt.com/) (Vue 3 Composition API) |
| State management | [Pinia](https://pinia.vuejs.org/) |
| Linter / formatter | [Ruff](https://docs.astral.sh/ruff/) |
| Containers | Docker + Docker Compose |

---

## Project Structure

```
music-db/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan (DB init, static files)
│   │   ├── core/
│   │   │   └── config.py              # Settings (JWT, Roon host/port)
│   │   ├── api/
│   │   │   ├── router.py              # Registers all feature routers
│   │   │   ├── deps.py                # get_current_user dependency
│   │   │   └── routes/
│   │   │       ├── auth.py            # /auth — register, login, me
│   │   │       ├── albums.py          # /albums — CRUD + art upload
│   │   │       ├── collections.py     # /collections — CRUD + album membership
│   │   │       ├── musicians.py       # /musicians — search + detail
│   │   │       ├── persons.py         # /persons — personnel search
│   │   │       ├── musicbrainz.py     # /musicbrainz — search + release lookup
│   │   │       ├── roon_import.py     # /import/roon — connect, probe, bulk import
│   │   │       └── flac_import.py     # /import/flac — file scan bulk import
│   │   ├── models/
│   │   │   ├── user.py                # users
│   │   │   ├── album.py               # albums, album_musicians, album_personnel
│   │   │   ├── musician.py            # musicians
│   │   │   ├── person.py              # persons
│   │   │   ├── record_label.py        # record_labels
│   │   │   ├── collection.py          # collections
│   │   │   └── collection_album.py    # collection_albums (junction)
│   │   ├── schemas/
│   │   │   ├── album.py               # AlbumCreate/Read/Update/Summary
│   │   │   ├── collection.py          # CollectionCreate/Read/Update/DetailRead
│   │   │   ├── musician.py            # MusicianRead, AlbumMusicianEntry
│   │   │   ├── person.py              # PersonRead, AlbumPersonnelEntry
│   │   │   ├── record_label.py        # RecordLabelRead
│   │   │   └── user.py                # UserCreate/Read, Token
│   │   ├── services/
│   │   │   ├── album.py               # Album CRUD + bulk delete
│   │   │   ├── collection.py          # Collection CRUD + album management
│   │   │   ├── auth.py                # Password hashing, JWT
│   │   │   ├── musicbrainz.py         # MB search, release lookup, art download
│   │   │   ├── roon.py                # Roon connection + background importer
│   │   │   └── flac_import.py         # File scanner + background importer
│   │   └── db/
│   │       ├── base.py                # DeclarativeBase
│   │       └── session.py             # Async engine, session factory, get_db()
│   ├── alembic/                       # Migration scripts
│   ├── alembic.ini
│   ├── entrypoint.sh                  # Runs migrations then starts server
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── pages/
│   │   ├── index.vue                  # / — redirects based on auth state
│   │   ├── login.vue                  # /login
│   │   ├── register.vue               # /register
│   │   ├── import.vue                 # /import — Roon + file import UI
│   │   ├── albums/
│   │   │   ├── index.vue              # /albums — searchable album list
│   │   │   ├── new.vue                # /albums/new — create form
│   │   │   └── [id]/
│   │   │       ├── index.vue          # /albums/:id — detail + art management
│   │   │       └── edit.vue           # /albums/:id/edit
│   │   ├── collections/
│   │   │   ├── index.vue              # /collections
│   │   │   └── [id].vue               # /collections/:id — albums grid
│   │   └── musicians/
│   │       └── [id].vue               # /musicians/:id — albums by musician
│   ├── components/
│   │   ├── AppHeader.vue              # Navigation (Collections, Albums, Import)
│   │   ├── AlbumCard.vue              # Album thumbnail card
│   │   ├── AlbumForm.vue              # Create/edit form with MusicBrainz search
│   │   ├── CollectionCard.vue         # Collection summary card
│   │   ├── MusicianTagInput.vue       # Musician + instrument tagger
│   │   └── PersonnelTagInput.vue      # Personnel + role tagger
│   ├── composables/
│   │   ├── useApi.ts                  # Authenticated API fetch wrapper
│   │   └── useMusicBrainz.ts          # MB search/release helpers
│   ├── stores/
│   │   ├── auth.ts                    # Login, register, token persistence
│   │   ├── albums.ts                  # Album CRUD + art upload
│   │   ├── collections.ts             # Collection CRUD + album membership
│   │   └── musicians.ts               # Musician search + detail
│   ├── middleware/
│   │   └── auth.ts                    # Route guard (redirect to /login)
│   ├── app.vue
│   ├── nuxt.config.ts
│   └── Dockerfile
│
├── docker-compose.yml                 # Dev (hot reload)
├── docker-compose.prod.yml            # Production
└── CLAUDE.md                          # AI assistant project instructions
```

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Docker + Docker Compose | latest |
| uv (Python package manager) | latest — `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### Run with Docker (recommended)

```bash
git clone <repo>
cd music-db
docker compose up --build
```

- Frontend: http://localhost:3003
- Backend API: http://localhost:8003
- Interactive API docs: http://localhost:8003/docs

Source code is volume-mounted into both containers — edits are reflected immediately without rebuilding.

### First-time setup

1. Open http://localhost:3003/register and create an account
2. Log in — you'll be redirected to your collections
3. Start adding albums manually, or use the **Import** page to bulk-import from Roon or a file scan

---

## Environment Variables

### Backend (`docker-compose.yml` → `backend.environment`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:////app/data/daily_tasks.db` | SQLAlchemy async DB URL |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **change this** |
| `ROON_HOST` | _(empty)_ | IP address of your Roon Core machine |
| `ROON_PORT` | `9330` | Roon extension API port |

### Frontend (`docker-compose.yml` → `frontend.environment`)

| Variable | Default | Description |
|---|---|---|
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8003` | Backend API base URL |

---

## Mounting Your Music Library (File Import)

The file scanner runs inside the Docker container and needs your music drive mounted as a volume.

**1. Mount the network share on your host:**

```bash
# Create a local mount point
sudo mkdir -p /mnt/music

# Mount SMB/CIFS share (get credentials from your keyring if needed)
sudo mount -t cifs //your-server/share /mnt/music \
  -o username=USER,password=PASS,uid=$(id -u),gid=$(id -g)

# Verify
ls /mnt/music
```

**2. Add the volume to `docker-compose.yml`:**

```yaml
services:
  backend:
    volumes:
      - ./backend:/app
      - backend_db:/app/data
      - /mnt/music:/music:ro   # ← add this line
```

**3. Rebuild:**

```bash
docker compose up --build
```

**4. On the Import page → Files tab**, enter `/music` as the scan path.

To make the mount survive reboots, add to `/etc/fstab`:
```
//your-server/share  /mnt/music  cifs  credentials=/etc/samba/music.creds,uid=1000,gid=1000,_netdev  0  0
```

---

## Roon Import

The Roon importer connects to Roon Core's extension API directly via IP (mDNS doesn't work inside Docker bridge networks).

**Setup:**

1. Add your Roon Core IP to `docker-compose.yml`:
   ```yaml
   environment:
     ROON_HOST: 192.168.1.x
   ```
2. Rebuild: `docker compose up --build`
3. Open **Import → Roon tab**
4. Enter your Roon Core IP and click **Connect**
5. In Roon: **Settings → Extensions → Music DB Importer → Enable**
6. Click **Refresh** — status should show Authorized
7. Optionally run **Probe** to preview raw album data
8. Click **Start import**

The import runs in the background. Albums already in the database (matched by title + artist) are updated rather than duplicated. Artwork is sourced from Roon first, then MusicBrainz Cover Art Archive as a fallback.

---

## MusicBrainz Integration

When adding or editing an album, the form includes a MusicBrainz search button (appears once title and artist are filled in). Selecting a release auto-populates:

- Title, artist, release year, record label
- Full track listing
- Cover art (downloaded from Cover Art Archive)

Albums without MusicBrainz coverage can have art uploaded manually from the album detail page.

---

## Data Model

```
User ──────────────────────────────────────────────────────────── owns ──→ Collection
                                                                                │
                                                                    collection_albums
                                                                                │
Album ←─────────────────────────────────────────────────────────────────────────┘
  │
  ├── record_labels (many albums → one label)
  │
  ├── album_musicians ──→ Musician
  │         └── instrument (e.g. "Piano", "Bass")
  │
  └── album_personnel ──→ Person
            └── role (e.g. "Producer", "Engineer")
```

**Key behaviours:**
- Deleting a collection does not delete its albums
- "Delete albums in collection" permanently removes the albums themselves (not just the membership)
- "Delete all albums" on the Import page wipes the entire album table
- Cover art files are stored at `/app/data/album_art/` inside the container (persisted in the `backend_db` Docker volume)
- Record labels and musicians are shared across albums and created on demand

---

## API Reference

All endpoints (except `/auth/register` and `/auth/login`) require a `Bearer` token in the `Authorization` header.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Login — returns JWT |
| `GET` | `/auth/me` | Current user info |

### Albums

| Method | Path | Description |
|---|---|---|
| `GET` | `/albums` | List albums (filterable by artist, label, musician, search) |
| `POST` | `/albums` | Create album |
| `GET` | `/albums/{id}` | Album detail with musicians, personnel, label |
| `PATCH` | `/albums/{id}` | Update album |
| `DELETE` | `/albums/{id}` | Delete one album |
| `DELETE` | `/albums` | Delete **all** albums |
| `POST` | `/albums/{id}/art` | Upload cover art (JPEG/PNG/WebP, max 5 MB) |
| `DELETE` | `/albums/{id}/art` | Remove cover art |

### Collections

| Method | Path | Description |
|---|---|---|
| `GET` | `/collections` | List user's collections |
| `POST` | `/collections` | Create collection |
| `GET` | `/collections/{id}` | Collection + album list |
| `PATCH` | `/collections/{id}` | Rename / update description |
| `DELETE` | `/collections/{id}` | Delete collection (albums kept) |
| `POST` | `/collections/{id}/albums/{album_id}` | Add album to collection |
| `DELETE` | `/collections/{id}/albums/{album_id}` | Remove album from collection |
| `DELETE` | `/collections/{id}/albums` | Delete all albums in collection |

### MusicBrainz

| Method | Path | Description |
|---|---|---|
| `GET` | `/musicbrainz/search?title=&artist=` | Search releases |
| `GET` | `/musicbrainz/release/{mbid}` | Full release data + track list |

### Roon Import

| Method | Path | Description |
|---|---|---|
| `POST` | `/import/roon/connect` | Connect to Roon Core |
| `GET` | `/import/roon/status` | Connection + authorization status |
| `GET` | `/import/roon/probe?count=3` | Fetch raw data for N albums |
| `POST` | `/import/roon/start` | Start background import |
| `GET` | `/import/roon/progress` | Poll import progress |
| `POST` | `/import/roon/cancel` | Request cancellation |

### File Import

| Method | Path | Description |
|---|---|---|
| `POST` | `/import/flac/start` | Start background file scan |
| `GET` | `/import/flac/progress` | Poll scan progress |
| `POST` | `/import/flac/cancel` | Request cancellation |

---

## Common Commands

### Backend

```bash
cd backend

# Install all dependencies
uv sync

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run fastapi dev app/main.py

# Add a dependency
uv add <package>

# Lint
uv run ruff check .
uv run ruff format .

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe change"
```

### Docker

```bash
# Start (dev, hot reload)
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop
docker compose down

# Reset database (removes named volume)
docker compose down -v

# Shell into backend container
docker compose exec backend bash

# Production
docker compose -f docker-compose.prod.yml up --build -d
```

---

## Database Persistence

The SQLite database and cover art files are stored in a Docker named volume (`backend_db` mounted at `/app/data`). This survives `docker compose down` but is cleared by `docker compose down -v`.

Alembic migrations run automatically on container start via `entrypoint.sh` — no manual migration step is needed after rebuilding.
