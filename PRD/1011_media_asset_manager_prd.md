# 1011 Media Asset Manager — Product Requirements Document

> **Version:** PRD v0.1 | **Date:** 2026-04-06 | **Author:** AI Product Manager (Autonomous) | **Status:** Draft for Review

---

## 1. Executive Summary

**1011 Media Asset Manager** is a professional-grade, self-hosted Digital Asset Management (DAM) system evolved from the existing VG Photo Search Tools. It serves 1011 PC's creative team — editors, photographers, videographers, and designers — who manage thousands of photos, videos, and PSD files across LAN network shares and local drives.

The current tool provides basic search, filtering, and file import capabilities. This PRD defines the roadmap to transform it into a complete media asset management platform with:
- **Enhanced taxonomy & tagging** — controlled vocabularies, hierarchical tags, batch tagging
- **Batch workflows** — multi-select operations, bulk metadata editing, batch export
- **Collaboration features** — collections, shared workspaces, activity logs
- **Improved UX** — lightbox, keyboard navigation, drag-and-drop, advanced search
- **Performance hardening** — SQLite optimization, caching, pagination, background processing

Cloud storage integration is **explicitly deferred** to a future release.

### Discovery Inputs

| Parameter | Value |
|---|---|
| **Problem/User** | 1011 PC's creative team needs a centralized tool to catalog, tag, search, and manage multimedia assets across LAN — with better organization, batch workflows, and collaboration |
| **Business Context** | Technical Debt (evolving existing internal tool) |
| **Discovery Confidence** | High |
| **Primary Constraint** | Technical Feasibility |

---

## 2. Research Citations

| # | Source | Key Insight |
|---|---|---|
| [1] | Acquia — DAM Features 2025 | Version control, RBAC, and DRM are core DAM pillars |
| [2] | Aprimo — AI-Powered DAM | Auto-tagging and intelligent search reduce manual effort by 40-60% |
| [3] | Orange Logic — Agentic AI in DAM | Automated workflows and approval routing are emerging capabilities |
| [4] | Virtuall.pro — DAM Best Practices | Phased rollouts and internal champions drive adoption |
| [5] | Hyland — DAM Implementation | Initial content audit before taxonomy design is critical |
| [6] | Frontify — Governance | Clear ownership of taxonomy and processes prevents drift |
| [7] | ImageBankX — ROI Measurement | Track time-saved-searching and content-duplication-reduction |
| [8] | XDA Developers — Self-Hosted DAM | Pimcore, ResourceSpace, Phraseanet as benchmark competitors |
| [9] | Storyteq — MAM Taxonomy | Controlled vocabularies + functional metadata enable self-service |
| [10] | SQLite FTS5 Optimization | WAL mode, prefix indexing, external content tables, periodic VACUUM |

---

## 3. MITRE-Style Problem Framing Canvas

### Approach Selection

Three problem framing approaches were evaluated:

| Approach | Description | Verdict |
|---|---|---|
| **A: Asset Discovery Focus** | Optimize search speed and filtering as the primary value | ❌ Rejected — Already partially solved; doesn't address organizational debt |
| **B: Full DAM Platform** | Build a comprehensive DAM with enterprise features (RBAC, DRM, workflows) | ❌ Rejected — Over-scoped for current team size and tech constraint |
| **C: Organized Asset Workspace** ✅ | Evolve into a structured workspace with batch ops, improved tagging, and light collaboration | ✅ Selected — Right scope, feasible with current stack, addresses real pain points |

### Canvas (Approach C: Organized Asset Workspace)

| Dimension | Detail |
|---|---|
| **Mission / Outcome** | Enable the creative team to find any asset in under 10 seconds and organize their library with minimal manual effort |
| **Stakeholders** | Creative team (primary), Editorial management (secondary), IT/DevOps (infrastructure) |
| **Scope** | Self-hosted on Windows; LAN/local drives only; no cloud sync in v1 |
| **Boundaries** | NOT a cloud DAM, NOT a project management tool, NOT an image editor |
| **Operational Context** | Windows workstations connected to NAS via SMB shares; ~400K+ indexed files; team of 5-15 daily users |
| **Constraints — Tech** | Must stay on Flask + SQLite + vanilla JS stack; no new infra dependencies; must work with existing ~400MB SQLite DB |
| **Constraints — Budget** | Zero additional software licensing costs; all open-source dependencies |
| **Constraints — Policy** | Internal tool only; no external exposure; no PII handling beyond team usage |
| **Risks** | SQLite concurrency limits at scale; NAS connectivity interruptions; adoption friction |
| **Ethics** | No AI auto-tagging of persons without explicit consent policy |
| **Key Assumptions** | [ASSUMPTION] Team will adopt tagging conventions if tooling makes it easy; [ASSUMPTION] Average daily search queries < 500; [ASSUMPTION] NAS uptime > 99% during work hours |
| **Measures of Effectiveness** | ① Avg search-to-find time < 10s ② > 80% of new imports tagged within 24h ③ Zero "can't find the file" complaints per month |
| **Measures of Suitability** | ① System handles 500K+ files without latency ② Background scan completes < 30 min for full index ③ Page load < 2s on LAN |
| **Decision Criteria** | Prioritize features that reduce manual work → improve discoverability → enable collaboration |

---

## 4. Opportunity Solution Tree

### Business Outcome
**Reduce time-to-asset from minutes to seconds while maintaining organized, searchable archives.**

### OST Diagram (ASCII)

```
                        ┌─────────────────────────────┐
                        │   Reduce time-to-asset &    │
                        │   improve organization      │
                        └─────────────┬───────────────┘
               ┌──────────────────────┼──────────────────────┐
               ▼                      ▼                      ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ O1: Better       │   │ O2: Batch        │   │ O3: Collaboration│
    │ Discoverability  │   │ Workflows        │   │ & Organization   │
    └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
    ┌────────┼────────┐    ┌────────┼────────┐    ┌────────┼────────┐
    ▼        ▼        ▼    ▼        ▼        ▼    ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│S1.1  │ │S1.2  │ │S1.3  │ │S2.1  │ │S2.2  │ │S2.3  │ │S3.1  │ │S3.2  │ │S3.3  │
│Adv.  │ │Smart │ │EXIF/ │ │Multi-│ │Batch │ │Batch │ │Collec│ │Activ-│ │User  │
│Search│ │Tags  │ │Meta  │ │Select│ │Tag   │ │Export│ │tions │ │ity   │ │Roles │
│& Filt│ │System│ │Panel │ │Actions│ │Edit  │ │/DL   │ │/Albums│ │Log  │ │(RBAC)│
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

### Ranked Opportunity Scoring

| ID | Solution | Impact (1-5) | Confidence (1-5) | Effort (1-5) | Risk (1-5) | **Weighted Score** |
|---|---|---|---|---|---|---|
| **S1.2** | Smart Tag System | 5 | 5 | 3 | 1 | **9.2** |
| **S2.1** | Multi-Select Actions | 5 | 5 | 2 | 1 | **9.0** |
| **S1.1** | Advanced Search & Filters | 5 | 5 | 3 | 1 | **9.0** |
| **S2.2** | Batch Tag Editing | 5 | 4 | 2 | 1 | **8.4** |
| **S1.3** | EXIF / Metadata Panel | 4 | 5 | 2 | 1 | **8.0** |
| **S3.1** | Collections / Albums | 4 | 4 | 3 | 2 | **7.0** |
| **S2.3** | Batch Export / Download | 4 | 4 | 3 | 2 | **7.0** |
| **S3.2** | Activity Log | 3 | 4 | 2 | 1 | **6.8** |
| **S3.3** | User Roles (RBAC) | 3 | 3 | 4 | 3 | **4.6** |

> **Weights:** Impact × 0.35 + Confidence × 0.25 + (6 - Effort) × 0.25 + (6 - Risk) × 0.15

**Top selections for MVP:** S1.2, S2.1, S1.1, S2.2, S1.3, S3.1

**Deferred:** S3.3 (RBAC) — requires auth system; too much effort for current single-team context. S2.3 (Batch Export) and S3.2 (Activity Log) — nice-to-have, lower impact.

**Trade-off rationale:** Focused on features that maximize findability and reduce repetitive manual work first. Collaboration features like collections are included because they're relatively low-effort and high-value for team workflows. RBAC is deferred because the tool is currently single-team with no auth—adding auth is a large effort with moderate value.

---

## 5. Proof-of-Life Experiment Plan

### Experiment Strategy Selection

| Strategy | Description | Verdict |
|---|---|---|
| **A: Feature Flag Rollout** | Build all features behind flags, A/B test | ❌ Rejected — Too complex for internal team of < 15; no analytics infrastructure |
| **B: Phased MVP Release** ✅ | Ship in 3 phases, measure adoption qualitatively | ✅ Selected — Simple, matches team size, fast feedback |
| **C: Prototype-First** | Design prototypes, test with users before building | ❌ Rejected — Team already uses the tool daily; we know the problems; building is faster than prototyping |

### Experiment Details

| # | Experiment | Hypothesis | Metric | Threshold | Timeline | Owner |
|---|---|---|---|---|---|---|
| **E1** | Ship Phase 1 (Enhanced Tags + Multi-Select) | If we add hierarchical tags + multi-select, then > 70% of imports will be tagged within 24h | % of imported files with ≥1 tag after 24h | ≥ 70% | 2 weeks after launch | Dev Lead |
| **E2** | Ship Phase 2 (Advanced Search + Metadata Panel) | If we add advanced filters and metadata display, search-to-find time drops by > 50% | Avg time from search initiation to file download (self-reported) | ≤ 15s (down from ~30s) | 1 week after launch | Dev Lead |
| **E3** | Ship Phase 3 (Collections + Batch Export) | If we add collections, team creates ≥ 5 shared collections within first month | # of collections created | ≥ 5 | 4 weeks after launch | Dev Lead |

**Success rule:** Move to next phase if threshold met or user feedback clearly positive.
**Stop rule:** If < 30% adoption after 2 weeks, conduct user interviews before proceeding.

---

## 6. PRD v0.1

### 6.1 Context

The 1011 Media Asset Manager evolves an existing internal tool ("VG Photo Search Tools") used by 1011 PC's creative team to search and browse ~400K+ photos, videos, and PSD files stored on LAN network shares and local drives.

The current tool (Flask + SQLite FTS5 + vanilla JS) provides:
- ✅ Keyword search with FTS5
- ✅ File type filtering (image/video/PSD)
- ✅ Sort by date/name
- ✅ Grid and list views
- ✅ Thumbnail generation (PIL for images/PSD, imageio for video)
- ✅ File import with destination selection and tags
- ✅ File rename
- ✅ Open in Explorer / Download
- ✅ Background scanning of source directories
- ✅ Basic tagging (add/remove per file)

**What's missing (validated through daily usage):**
- ❌ No tag hierarchy or controlled vocabulary — tags are freeform, inconsistent
- ❌ No multi-select — every operation is one file at a time
- ❌ No batch tagging — tag 200 match photos individually
- ❌ No advanced search — can't combine filters (e.g., "Persija + 2024 + images only")
- ❌ No metadata display — EXIF data not shown to user
- ❌ No collections/albums — can't group files across folders
- ❌ No activity log — no record of who did what
- ❌ No keyboard navigation — mouse-only interaction

### 6.2 Problem Statement

> 1011 PC's creative team wastes significant time manually searching, organizing, and tagging thousands of multimedia assets across LAN storage. The existing tool lacks batch operations, structured tagging, and collaboration features — forcing repetitive manual work and causing files to become unfindable.

**Target Users:**
| Persona | Role | Primary JTBD | Pain |
|---|---|---|---|
| **Photographer/Videographer** | Captures media at events | Import 200+ files, tag by event/player/date quickly | Tagging one-by-one takes 30+ minutes |
| **Editor** | Finds and uses media for content | Find the right photo in seconds | Keyword search often returns too many results; no way to narrow down |
| **Creative Lead** | Organizes team assets | Create organized collections, maintain naming standards | No way to curate albums or enforce taxonomy |
| **IT Admin** | Maintains infrastructure | Keep system running, configure sources | No monitoring dashboard or health metrics |

### 6.3 Goals and Success Metrics

**North Star Metric:** Average time from "I need a specific photo" to "I have it open" ≤ 10 seconds.

| Category | Metric | Current | Target |
|---|---|---|---|
| **Findability** | Search-to-find time | ~30-60s | < 10s |
| **Organization** | % of assets with ≥ 1 tag | ~5% | > 50% within 3 months |
| **Efficiency** | Time to tag a batch import of 200 files | ~30 min | < 3 min (batch tag) |
| **Reliability** | System uptime during work hours | ~95% | > 99% |
| **Adoption** | Daily active users | ~3 | All team members (5-15) |

**Guardrails:**
- Page load time must stay ≤ 2 seconds
- Full index scan must complete ≤ 30 minutes
- Zero data loss — no file deletion features in v1
- Must not break existing search/import workflows

### 6.4 Scope and Constraints

#### In Scope (v1)
| Feature Area | Details |
|---|---|
| **Enhanced Tag System** | Tag categories, suggested tags, tag autocomplete, tag management page |
| **Multi-Select Operations** | Select multiple files in grid/list, bulk tag, bulk download |
| **Batch Tag Editing** | Apply/remove tags to selected files in one action |
| **Advanced Search** | Combined filters, date range picker, folder filter, saved search queries |
| **Metadata Panel** | Display EXIF data (camera, lens, ISO, etc.), file properties, GPS (if present) |
| **Collections** | Create named collections, add files from search results, share collection links |
| **Keyboard Navigation** | Arrow keys in grid, Enter to open, Esc to close, Shift+Click for range select |
| **UI/UX Refresh** | Rebrand from "VG Search Tool" to "1011 Media Asset Manager", new logo, refined sidebar |
| **Performance Optimization** | SQLite PRAGMA tuning, query caching, lazy-load thumbnails, virtual scrolling |

#### Out of Scope (v1)
| Feature | Reason |
|---|---|
| Cloud storage sync | Explicitly deferred per product owner |
| User authentication / RBAC | Low value for single-team; high effort |
| AI auto-tagging | Requires ML infrastructure; deferred |
| File editing (crop, resize, etc.) | Not a DAM concern; use Adobe tools |
| Mobile app | Desktop-first; responsive web sufficient |
| Real-time collaboration | Over-scoped for current user base |
| File deletion from disk | Safety — no destructive operations in v1 |

#### Non-Goals
- This is NOT a replacement for Adobe Bridge, Lightroom, or file explorer
- This is NOT a project management or editorial workflow tool
- This is NOT a public-facing or externally accessible application

#### Compliance
- Internal use only — no GDPR/external data concerns
- All files remain on existing LAN storage — no data migration

### 6.5 Chosen Approach

**Approach C: Organized Asset Workspace** (from MITRE canvas)

Evolve the existing Flask + SQLite + vanilla JS codebase incrementally. No framework migration. No new infrastructure dependencies.

**Why this over alternatives:**
- **vs. Full DAM rebuild**: Too much effort, breaks existing workflows, requires auth system
- **vs. Search-only optimization**: Doesn't address root cause (organization + batch ops)
- **vs. Adopting open-source DAM (ResourceSpace, etc.)**: Migration cost too high; custom tool already fits workflow; would lose all existing data/thumbnails

### 6.6 User Flows

#### Flow 1: Batch Import & Tag (Primary)
```
1. User clicks "Import Files" on Assets page
2. Drops 200 event photos in dropzone → previews shown
3. Selects destination folder (or creates: "2026/Persija/vs-Persib")
4. Adds batch tags: "persija, persib, liga-1, 2026"
5. Clicks "Import" → progress bar → completion toast
6. All 200 files are now searchable by any of those tags
```

#### Flow 2: Search & Find (Primary)
```
1. User types "Jay Idzes 2024" in search bar
2. System returns results filtered by keyword match
3. User clicks "Images" filter chip → narrows to photos
4. User sorts by "Latest → Oldest"
5. User clicks a result → detail modal with preview + metadata + tags
6. User clicks "Open File Location" or "Download"
```

#### Flow 3: Multi-Select & Batch Tag (Primary)
```
1. User searches for "Persija vs Bali United"
2. User clicks "Select Mode" toggle (or holds Shift)
3. User selects 50 relevant photos (click or Shift+click range)
4. Toolbar appears: "50 selected — [Tag] [Download] [Add to Collection]"
5. User clicks "Tag" → types "bali-united, liga-1" → Apply
6. Tags applied to all 50 files; search haystack updated
```

#### Flow 4: Create & Use Collection (Secondary)
```
1. User clicks "Collections" in sidebar → "New Collection"
2. Names it "Best of Liga 1 2026"
3. Searches for images → selects favorites → "Add to Collection"
4. Collection accessible from sidebar; acts as a virtual album
5. Collection link can be shared with team (same network)
```

#### Edge/Corner Cases
| Case | Handling |
|---|---|
| NAS disconnected during scan | Scan skips unavailable paths; logs warning; partial results preserved |
| Duplicate file imported | Auto-rename with counter suffix (existing behavior preserved) |
| Tag with special characters | Strip to alphanumeric + hyphens; normalize to lowercase |
| Very long filename | Truncate display to 60 chars with ellipsis; full name in tooltip |
| 1000+ search results | Paginate with "Load More" (existing); consider virtual scrolling |
| Concurrent tag edits | SQLite WAL handles concurrent reads; writes serialized (acceptable at this scale) |

#### Accessibility
- Keyboard navigation for all interactive elements
- ARIA labels on all buttons and interactive regions
- Focus management in modals (trap focus, restore on close)
- Minimum 4.5:1 contrast ratio on all text
- Screen reader announcements for search results count changes

### 6.7 Acceptance Criteria (Gherkin-Style)

#### Tag System
```gherkin
GIVEN I am on the asset detail modal
WHEN I type a tag and press Enter or comma
THEN the tag is saved and appears as a removable pill

GIVEN I am typing a tag
WHEN the input has 2+ characters
THEN I see autocomplete suggestions from existing tags

GIVEN I have selected 20 files in multi-select mode
WHEN I click "Tag" and enter "liga-1, persija"
THEN both tags are applied to all 20 files
AND the search index is updated for all 20 files
```

#### Search
```gherkin
GIVEN I type "Persija 2024" in the search bar
AND I select "Images" file type filter
THEN results show only images matching "Persija" AND "2024"

GIVEN I click the date range picker
WHEN I select Jan 2024 - Mar 2024
THEN results are filtered to that date range only

GIVEN I perform a search
WHEN results load
THEN results are paginated (default 50 per page)
AND I see a "Load More" button if more results exist
```

#### Multi-Select
```gherkin
GIVEN I am in grid view
WHEN I hold Shift and click two items
THEN all items between them are selected
AND a floating toolbar shows the selection count and actions

GIVEN I have 30 items selected
WHEN I click "Download" in the toolbar
THEN a ZIP file containing all 30 originals is downloaded

GIVEN I am in select mode
WHEN I press Escape
THEN selection is cleared and select mode exits
```

#### Collections
```gherkin
GIVEN I click "New Collection" in the sidebar
WHEN I enter a name and confirm
THEN the collection appears in my sidebar navigation

GIVEN I have items selected
WHEN I click "Add to Collection" and choose a collection
THEN those items appear when I open that collection

GIVEN I open a collection
WHEN I view its contents
THEN I see all added items with the same grid/list view as search results
```

### 6.8 Data and Instrumentation

#### Events to Track (Log-Based)

| Event | Properties | Purpose |
|---|---|---|
| `search_performed` | query, filters, result_count, duration_ms | Measure search effectiveness |
| `file_imported` | file_id, tags_count, destination_folder | Track import patterns |
| `tag_added` | file_id, tag, source (manual/batch) | Measure tag adoption |
| `tag_removed` | file_id, tag | Track tag lifecycle |
| `collection_created` | collection_name, file_count | Measure collection adoption |
| `batch_action` | action_type, item_count | Track batch feature usage |
| `scan_completed` | duration_s, files_found, files_reused, errors | Monitor index health |

#### Dashboard (Future)
- Per-query log file (existing `search.log`) continued
- New: `activity.log` with JSON-structured events
- [ASSUMPTION] Simple log parsing script sufficient; no real-time dashboard in v1

### 6.9 Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **SQLite lock contention** w/ concurrent writes | Medium | Medium | WAL mode (already enabled); write queue for batch ops; single-writer pattern |
| **NAS connectivity loss** during operations | Medium | High | Graceful error handling; retry logic; partial result caching |
| **Tag taxonomy sprawl** — inconsistent tags | High | Medium | Tag autocomplete; suggested tags; tag management page; controlled vocabulary |
| **Thumbnail generation bottleneck** for large imports | Medium | Low | Background thumbnail generation; lazy-load on first view |
| **Database size growth** with 500K+ files | Low | Medium | Periodic VACUUM + ANALYZE; consider external content FTS table |
| **Browser memory** with large grid results | Medium | Medium | Virtual scrolling; limit initial render to 50 items; lazy-load images |
| **User adoption** — team doesn't use new features | Low | High | Phased rollout; internal champion; training session; defaults that encourage tagging |
| **Breaking existing workflows** during migration | Medium | High | Backward-compatible API; preserve all existing routes; no destructive changes |

### 6.10 Release Plan

#### Phase 1: Foundation (Week 1-3) — "Tag & Select"
| Feature | Status |
|---|---|
| Rebrand to "1011 Media Asset Manager" | New |
| Enhanced tag system (autocomplete, categories) | Enhanced |
| Tag management page | New |
| Multi-select in grid/list view | New |
| Batch tagging (add/remove to selection) | New |
| Keyboard navigation basics | New |
| SQLite performance tuning | Enhanced |

#### Phase 2: Discovery (Week 4-6) — "Search & See"
| Feature | Status |
|---|---|
| Advanced search (combined filters, date range) | New |
| Metadata panel (EXIF display in detail modal) | New |
| Enhanced lightbox (zoom, pan, swipe) | Enhanced |
| Saved search queries | New |
| Virtual scrolling for large result sets | New |
| Folder tree browser in search sidebar | New |

#### Phase 3: Organize (Week 7-10) — "Collect & Share"
| Feature | Status |
|---|---|
| Collections / Albums | New |
| Add-to-collection from search/multi-select | New |
| Batch download (ZIP) | New |
| Activity log (JSON-structured) | New |
| Dashboard health widget (sidebar) | Enhanced |
| Tag analytics (most used, unused) | New |

#### Dependencies
| Dependency | Phase | Resolution |
|---|---|---|
| PIL/Pillow for EXIF parsing | Phase 2 | Already installed; extend usage |
| ZIP library for batch download | Phase 3 | Python `zipfile` stdlib — no new dependency |
| No new infrastructure needed | All | ✅ Confirmed |

### 6.11 Open Questions and Next Decisions

| # | Question | Impact | Proposed Default |
|---|---|---|---|
| 1 | Should tag autocomplete use only existing tags or include a curated preset list? | Tag quality | Start with existing tags; add presets in Phase 2 |
| 2 | Maximum collection size? | Performance | [ASSUMPTION] No limit; virtual scrolling handles display |
| 3 | Should batch download be synchronous or async with notification? | UX | Async with progress bar for > 50 files |
| 4 | Do we want folder-based auto-tagging (e.g., files in `/Persija/` auto-tagged "persija")? | Automation | Yes — implement in Phase 2 as opt-in |
| 5 | Logo and brand colors for "1011 Media Asset Manager"? | UI | Needs design input from team |
| 6 | Should collections persist in SQLite or JSON? | Architecture | SQLite (new `collections` and `collection_items` tables) |
| 7 | Target deployment: single machine or multiple workstations accessing shared instance? | Infra | [ASSUMPTION] Single server instance accessed via browser on LAN |

---

## 7. Stakeholder Gate Review Simulations

### Gate 1: Team Kickoff Review

| Stakeholder | Reaction | Resolution |
|---|---|---|
| **Creative Lead** | "Love batch tagging. But can we have tag *presets* for common events? I don't want people misspelling 'liga-1' as 'liga1'." | ✅ Added: Tag autocomplete with existing tags; controlled vocabulary as Phase 2 feature |
| **Photographer** | "The import flow is already good. Just make it faster — can I just drag a folder?" | ✅ Folder drag-and-drop import added to Phase 1 scope |
| **Editor** | "I search by player name + date all the time. Are date ranges available?" | ✅ Date range picker confirmed for Phase 2 |
| **IT Admin** | "SQLite with 400K files on a NAS path — are we sure this won't lock up?" | ✅ WAL mode already enabled; write serialization; load testing planned |

### Gate 2: Planning Review

| Concern | From | Resolution |
|---|---|---|
| "3-phase plan is 10 weeks. Can we ship Phase 1 sooner?" | Leadership | Phase 1 narrowed to core: batch tag + multi-select + rebrand. Target 2 weeks. |
| "Virtual scrolling is complex. Worth it?" | Engineering | Deferred to Phase 2; "Load More" pagination sufficient for Phase 1 |
| "What if someone adds bad tags? Any moderation?" | Creative Lead | Tag management page (Phase 1) includes: view all tags, merge duplicates, rename, delete |

### Gate 3: Solution Review

| Change | Before | After | Rationale |
|---|---|---|---|
| Collections scope | Full album management | Simple named lists with add/remove | Reduced effort; tests core hypothesis |
| Activity log | Per-user audit trail | Anonymous event log (no auth = no users) | No auth system → anonymous logs only |
| Batch download | Instant ZIP | Async ZIP generation with progress | Large selections would timeout otherwise |

### Gate 4: Launch Readiness

| Checklist | Status |
|---|---|
| All Phase 1 acceptance criteria pass | ⬜ Pending |
| Backward compatibility with existing data | ⬜ Pending |
| SQLite migration script tested | ⬜ Pending |
| ~400K file index loads without error | ⬜ Pending |
| Team training session scheduled | ⬜ Pending |
| Rollback plan documented | ⬜ Pending |

---

## 8. Risks and Decisions Log

### Decisions Made

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| **Tech stack** | Stay on Flask + SQLite + vanilla JS | Migrate to Next.js + Postgres | Technical Feasibility constraint; migration risk too high; existing stack proven |
| **Approach** | Organized Asset Workspace (incremental) | Full DAM rebuild | Lower risk; maintains backward compatibility; team already productive with current tool |
| **Auth system** | Deferred | Build now | < 15 users; single team; effort disproportionate to value |
| **Cloud sync** | Deferred (per product owner) | Build now | Explicit product owner decision |
| **AI auto-tagging** | Deferred | Build now | Requires ML infra; TensorFlow/ONNX adds complexity; not feasible within constraint |
| **Tag storage** | SQLite `tags` table (existing) | JSON in catalog file | DB already has tags table; SQL queries more flexible |
| **Collections storage** | New SQLite tables | JSON files | Consistency with existing data layer; relational queries for membership |
| **Batch download format** | ZIP (stdlib `zipfile`) | Individual download queue | ZIP is simpler; no new dependencies |
| **Frontend framework** | Stay vanilla JS | Add React/Vue | Tech feasibility; vanilla JS already works; no build step required |

### Assumptions Log

| # | Assumption | Risk if Wrong | Validation |
|---|---|---|---|
| A1 | Team will adopt tagging if tooling makes it easy | Low adoption → features wasted | E1 experiment (70% tagging threshold) |
| A2 | Average daily search queries < 500 | Performance issues | Monitor `search.log` post-launch |
| A3 | NAS uptime > 99% during work hours | Scan/search failures | IT Admin confirms SLA |
| A4 | Single-writer SQLite pattern sufficient | Lock contention | Load test with simulated concurrent users |
| A5 | No need for user authentication in v1 | Security risk if tool exposed beyond LAN | Tool is LAN-only; firewall rules confirmed |
| A6 | 50 items per page is sufficient default | UX frustration | User feedback in Phase 1 |
| A7 | Vanilla JS can handle virtual scrolling | Performance issues on complex grid | Prototype in Phase 2; fallback to "Load More" |

---

## 9. Appendix

### A. Current Tech Stack Reference

| Component | Technology | Version |
|---|---|---|
| Backend | Python + Flask | 3.0+ |
| Database | SQLite + FTS5 | Bundled with Python |
| Thumbnail Engine | Pillow (PIL) | 10.0+ |
| Video Thumbnails | imageio + PyAV | 2.34+ |
| EXIF Reader | exifread | 3.0+ |
| WSGI Server | Waitress | 3.0+ |
| Frontend | Vanilla JS + CSS | ES6+ |
| Templating | Jinja2 | Bundled with Flask |
| Config | JSON + env vars | — |

### B. File Structure (Current)

```
VG Photo Search Tools/
├── app.py              # Flask routes & app factory
├── catalog.py          # CatalogManager (scan, search, tags, import)
├── config.py           # AppConfig dataclass + env/JSON loading
├── app_config.json     # Persisted settings
├── photo_catalog.json  # Full catalog (JSON fallback)
├── photo_catalog.db    # SQLite + FTS5 database
├── requirements.txt    # Python dependencies
├── templates/
│   ├── layout.html     # Base template (sidebar + header)
│   ├── index.html      # Search page
│   └── assets.html     # Asset library page
├── static/
│   ├── css/            # styles.css, dashboard_layout.css
│   ├── js/             # app.js, assets.js
│   └── img/            # logo.svg, logo.png
├── thumbs/             # Generated thumbnails
├── logs/               # search.log
├── scripts/            # Setup scripts (PS1, SH)
└── run.bat / setup.bat # Windows launchers
```

### C. New Database Schema (Proposed)

```sql
-- Existing tables preserved as-is:
-- photos (id, path, filename, folder, size, mtime, date, year, month, ext)
-- photos_fts (id, haystack)
-- tags (id, file_id, tag, created_at)

-- New: Tag categories (for controlled vocabulary)
CREATE TABLE IF NOT EXISTS tag_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,        -- e.g., "event", "player", "team", "league"
    color TEXT,                        -- hex color for UI pill display
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- New: Collections
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    cover_file_id TEXT,               -- thumbnail from a member file
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- New: Collection membership
CREATE TABLE IF NOT EXISTS collection_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    UNIQUE(collection_id, file_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);

-- New: Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,          -- search, import, tag_add, tag_remove, collection_create, etc.
    details TEXT,                       -- JSON blob with event-specific data
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_collection_items_collection ON collection_items(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_items_file ON collection_items(file_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_type ON activity_log(event_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at);
```

---

## What to Validate Next

- [ ] Confirm brand identity (logo, colors) for "1011 Media Asset Manager" with creative team
- [ ] Validate proposed tag categories with actual team taxonomy needs
- [ ] Load test SQLite with 500K files + batch tag operations (100 files × 5 tags)
- [ ] Confirm NAS uptime SLA with IT Admin
- [ ] Review proposed database schema with development team
- [ ] Decide on tag autocomplete: existing-tags-only vs. curated presets
- [ ] Schedule Phase 1 kickoff and assign development tasks

---

> **Ready to dive deeper into implementation details, or start building experiments?**
