# Integration Analysis: career-ops ↔ CareerPilot

## Section 1: Features in career-ops that CareerPilot is MISSING (with specific file paths)

| Missing Feature | Description (career‑ops file) | Why it’s missing in CareerPilot |
|----------------|------------------------------|--------------------------------|
| **Pattern‑analysis script** | `/tmp/career-ops/modes/patterns.md` – runs `node analyze-patterns.mjs` to produce JSON with metadata, funnel, scoreComparison, archetypeBreakdown, blockerAnalysis, remotePolicy, companySizeBreakdown, scoreThreshold, techStackGaps, recommendations. | CareerPilot currently only stores raw applications and generates PDFs; no automated pattern‑analysis job or report generation endpoint. |
| **Blocker‑analysis generation** | `patterns.md` lines 39‑44 create `blockerAnalysis` (frequency of geo‑restriction, stack‑mismatch, seniority, onsite) – never exported. | No endpoint or DB table to persist blocker frequencies; user cannot see “hard blockers” across their application history. |
| **Remote‑policy breakdown** | `patterns.md` lines 69‑87 generate a table of conversion rates by remote‑policy bucket. | CareerPilot shows remote filter but does not aggregate historic remote‑policy success metrics. |
| **Tech‑stack‑gaps enumeration** | `patterns.md` lines 99‑108 list missing skills in negative/self‑filtered outcomes with frequency. | No UI or data store to surface “skill gaps” for a candidate based on past outcomes. |
| **Recommendation engine** | `patterns.md` lines 109‑141 produce a ranked list of actionable items (e.g., update `portals.yml` filters, set score threshold). | CareerPilot does not automatically edit filter files or suggest a concrete score‑threshold to the user. |
| **Score‑threshold recommendation** | `patterns.md` lines 84‑103 output a data‑driven minimum score (e.g., “no positive outcomes below 4.2/5”). | CareerPilot currently uses a static score cutoff (configurable but not auto‑recommended). |
| **Archetype breakdown report** | `patterns.md` produces `archetypeBreakdown` (total, positive, negative, conversion) per archetype label. | CareerPilot assigns archetypes only for display; no aggregated performance metrics per archetype stored or visualized. |
| **Tracker richer statistics** | `/tmp/career-ops/modes/tracker.md` defines extended status flow (Applied → Responded → Interview → Offer) and raw stats (total, % with PDF, avg. score). | CareerPilot’s tracker only stores status and PDF flag; missing aggregate dashboards and funnel visualization. |
| **Dynamic portal‑filter editor** | `patterns.md` lines 130‑138 show ability to auto‑edit `portals.yml` based on recommendations. | CareerPilot’s `settings.py` can store API keys but does not provide a UI or endpoint to modify portal filter configurations automatically. |
| **Cover‑letter placeholder handling** | `cover.md` Step 2 extracts `## Cover Letter Draft` from existing reports. CareerPilot only generates a cover letter on demand, never pre‑populates it automatically after evaluation. | No post‑evaluation suggestion to auto‑fill a cover‑letter template based on pattern‑analysis outcomes. |

---

## Section 2: Specific code patterns/algorithms that can be directly integrated

| Career‑ops pattern | Location (file/path) | Integration point in CareerPilot |
|--------------------|----------------------|-----------------------------------|
| **Pattern‑detection via `analyze-patterns.mjs`** | `/tmp/career-ops/modes/patterns.md` (executed by `node analyze-patterns.mjs`) | Create a background worker that loads the same JSON output and populates new tables (`pattern_analysis`, `pattern_findings`). |
| **Archetype classification & breakdown** | `patterns.md` → `archetypeBreakdown` section (lines 39‑40) | Extend the jobs table with an `archetype` column and store breakdown per archetype for each user. |
| **Blocker frequency tally** | `patterns.md` → `blockerAnalysis` (lines 39‑44) | Populate a `blocker_frequencies` table linked to each user‑application batch. |
| **Remote‑policy conversion table** | `patterns.md` → remotePolicy section (lines 69‑87) | Add a `remote_policy_stats` table to store conversion rates per remote‑policy bucket. |
| **Tech‑stack‑gap detection** | `patterns.md` → `techStackGaps` (lines 99‑108) | Generate a missing‑skills list per job and expose via API for UI consumption. |
| **Recommendation ranking logic** | `patterns.md` → `recommendations` (lines 109‑141) | Wire the ranking algorithm into a new endpoint that returns top‑N recommendations. |
| **Score‑threshold computation** | `patterns.md` → `scoreThreshold` (lines 84‑103) | Store recommended minimum score per user and use it for PDF auto‑generation gating. |
| **Reserve‑report‑num atomic allocation** | `patterns.md` → “reserve-report-num.mjs” (lines 223‑226) | Re‑use this mechanism for deterministic report IDs in CareerPilot’s reporting pipeline. |
| **Keyword‑mirroring for cover letters** | `cover.md` Step 4 extracts ATS‑critical and language signals; could be enhanced with pattern‑derived keyword lists. | Replace the simple skill‑matching in `backend/app/agents/cover_letter_generator.py` with a weighted keyword‑mirroring step that pulls from the pattern‑derived ATS‑critical list. |
| **Funnel conversion calculation** | `patterns.md` → `funnel` (lines 37‑38) | Compute and store funnel metrics on the frontend dashboard. |

---

## Section 3: Database schema additions needed

```sql
-- 1. Table to hold pattern‑analysis metadata
CREATE TABLE pattern_analysis (
    id               UUID PRIMARY KEY,
    user_id          UUID NOT NULL,
    run_at           TIMESTAMPTZ NOT NULL,
    metadata_json    JSONB,               -- total_entries, date_range, etc.
    funnel_json      JSONB,               -- stage counts
    score_comparison JSONB,               -- avg/min/max by outcome
    archetype_json   JSONB,               -- per‑archetype totals/conversion
    blocker_json     JSONB,               -- blocker frequencies
    remote_policy_json JSONB,           -- bucket conversion rates
    tech_stack_gaps  TEXT[],              -- missing skill strings
    score_threshold  NUMERIC,             -- recommended min score
    recommendations  TEXT[],              -- ranked actions
    report_id        UUID                 -- link to generated evaluation report
);

-- 2. Table for detailed blocker frequencies (optional normalized)
CREATE TABLE blocker_frequency (
    pattern_analysis_id UUID REFERENCES pattern_analysis(id),
    blocker_type       TEXT,
    count              INT,
    PRIMARY KEY (pattern_analysis_id, blocker_type)
);

-- 3. Add archetype column to job_postings (if not present)
ALTER TABLE job_postings ADD COLUMN archetype TEXT;

-- 4. Table for recommendation logs
CREATE TABLE pattern_recommendation (
    id               UUID PRIMARY KEY,
    user_id          UUID,
    analysis_id      UUID REFERENCES pattern_analysis(id),
    recommendation   TEXT,
    applied_at       TIMESTAMPTZ,
    status           TEXT CHECK (status IN ('pending','applied','rejected'))
);

-- 5. Extend match_scores with missing_skills and tech_gap scores
ALTER TABLE match_scores ADD COLUMN missing_skills JSONB;
ALTER TABLE match_scores ADD COLUMN tech_gap_score NUMERIC;
```

These additions will let CareerPilot persist the richer analysis data generated by the career‑ops patterns engine.

---

## Section 4: New API endpoints needed

| Endpoint | Method | Purpose | Request / Response Highlights |
|----------|--------|---------|-------------------------------|
| **/api/pattern-analysis** | `POST` | Trigger a new pattern analysis for the authenticated user. | Returns `analysis_id`. Optionally accepts `force: true` flag. |
| **/api/pattern-analysis/{id}** | `GET` | Retrieve the full pattern‑analysis payload (funnel, blockerAnalysis, techStackGaps, recommendations, etc.). | Returns JSON matching `pattern_analysis` fields. |
| **/api/pattern-analysis/{id}/recommendations** | `GET` | Load only the ranked recommendations. | Returns list of strings with impact level. |
| **/api/jobs/{job_id}/archetype** | `POST` | Assign or update the `archetype` field for a job posting. | Body: `{ "archetype": "FDE" }`. |
| **/api/patterns/apply-recommendation** | `POST` | Apply a recommendation (e.g., edit `portals.yml`, set score threshold). | Body contains `recommendation_id` and optional `target_file_path`. Uses existing file‑patch logic to edit `config/portals.yml` or `config/profile.yml`. |
| **/api/pattern-threshold** | `GET` | Return the current recommended `score_threshold` for the user. | Returns `{ "score_threshold": 4.2 }`. |
| **/api/blocker-frequencies** | `GET` | List aggregated blocker frequencies across all user applications. | Returns `{ "geo_restriction": 12, "stack_mismatch": 8, ... }`. |

These endpoints will expose the newly‑created database tables and enable the front‑end to display analysis results.

---

## Section 5: New frontend pages/components needed

| Component | Location (proposed) | Functionality |
|-----------|---------------------|---------------|
| **PatternAnalysisReport** | `src/pages/PatternAnalysisReport.tsx` | Shows funnel chart, score distribution, archetype breakdown table, blocker frequency bar chart, remote‑policy conversion table, tech‑stack‑gap list. |
| **TechStackGapsList** | `src/components/TechStackGapsList.tsx` | Displays missing skills with frequency counts, allows copy‑to‑clipboard. |
| **RecommendationPanel** | `src/components/RecommendationPanel.tsx` | Lists top‑N actionable items, each with “Apply now” button that calls `/api/patterns/apply-recommendation`. |
| **ArchetypePerformanceCard** | `src/components/ArchetypePerformanceCard.tsx` | Visual badge per archetype showing conversion rates, positives, negatives. |
| **ScoreThresholdBadge** | `src/components/ScoreThresholdBadge.tsx` | Shows recommended minimum score and updates cover‑letter PDF gating. |
| **PortalFilterEditor** | `src/pages/PortalFilterEditor.tsx` | Reads `portals.yml`, lets user apply suggestions from the recommendation engine, persists changes via API. |
| **EnhancedJobDetail** | `src/pages/JobDetail.tsx` | Embeds funnel status, blocker flags, tech‑gap warnings, and a “Generate Cover Letter” shortcut that pre‑populates with pattern‑derived keywords. |
| **AnalyticsDashboard** | `src/pages/AnalyticsDashboard.tsx` | Consolidates all pattern‑analysis charts and funnel metrics, integrates with existing analytics store. |
| **CoverLetterAutoPrompt** | `src/components/CoverLetterAutoPrompt.tsx` | After pattern analysis, auto‑populates the opening and profile‑intro sections of the cover‑letter draft based on discovered keywords. |

These UI pieces will consume the new API endpoints and surface the previously missing insights directly to the user.

---

## Section 6: Priority order for implementation

| Priority | What to implement | Reason / Business Value |
|----------|-------------------|--------------------------|
| **1️⃣ High** | Add DB tables (`pattern_analysis`, `blocker_frequency`, `pattern_recommendation`) and expose `/api/pattern-analysis` + `/api/pattern-analysis/{id}` endpoints. | Provides the foundation for all downstream insights; without persistence the analysis cannot be reused. |
| **2️⃣ High** | Integrate pattern‑analysis worker into the evaluation pipeline (run after each evaluation, store results). | Enables automatic generation of the missing blocker/remote‑policy/tech‑gap data. |
| **3️⃣ Medium** | Extend cover‑letter generator to use keyword‑mirroring from pattern analysis (replace simple skill match). | Directly improves cover‑letter relevance and demonstrates tangible user benefit. |
| **4️⃣ Medium** | Build the **PatternAnalysisReport** and **TechStackGapsList** UI components and wire them to the new API. | Gives users immediate visibility into patterns and gaps; core to the “actionable insights” value proposition. |
| **5️⃣ Medium** | Implement **RecommendationPanel** and **PortalFilterEditor** to let users apply suggestions with one click. | Turns analysis into concrete actions (filter updates, score thresholds). |
| **6️⃣ Low** | Add **ArchetypePerformanceCard**, **ScoreThresholdBadge**, and **EnhancedJobDetail** enhancements. | Polished UX features that enrich the experience but are not core to the integration. |
| **7️⃣ Low** | Deploy the **AnalyticsDashboard** and any additional visualizations. | Longer‑term roadmap item for deeper data exploration. |

Following this order ensures that the backend data model and API are in place before investing in UI work, while the cover‑letter improvement delivers an early “wow” factor that can be shipped quickly.

--- 

*End of Integration Analysis.*