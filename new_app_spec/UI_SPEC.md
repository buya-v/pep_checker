# UI Specification — PEP Compliance Manager

## Navigation Structure

```
┌─────────────────────────────────────────────────────────┐
│  PEP Compliance Manager              [User] [Logout]    │
├──────┬──────────┬────────────┬──────────┬───────────────┤
│ PEP  │ Screening│ AI Search  │ Scraper  │ Settings (Mgr)│
│Persons│          │            │          │               │
└──────┴──────────┴────────────┴──────────┴───────────────┘
```

**Top-level navigation items:**
1. **PEP Persons** — Main PEP registry (list + detail)
2. **Relationships** — Accessible from PEP Person detail, also as standalone list
3. **Screenings** — Name screening records
4. **AI PEP Search** — Wizard to search for PEPs via AI
5. **AI Position Search** — Wizard to discover PEP positions by country
6. **Scrape Official Source** — Web scraper wizard
7. **Settings** — Configuration (Manager only)

---

## Page 1: PEP Persons List

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ PEP Persons                                    [+ New PEP]  │
├─────────────────────────────────────────────────────────────┤
│ Search: [________________] [PEP Type ▼] [Status ▼] [Risk ▼]│
│ ☐ Show Archived                                             │
├─────────────────────────────────────────────────────────────┤
│ Group By: [PEP Type] [Status] [Risk Level]                  │
├────┬──────────────┬──────────┬──────────┬────┬───┬──────────┤
│ #  │ Name         │ Position │ Org      │Type│Risk│Last Check│
├────┼──────────────┼──────────┼──────────┼────┼───┼──────────┤
│ 1  │ Хүрэлсүх...  │ Head of  │ Gov of MN│ D  │ H │ 2025-01  │
│ 2  │ John Smith   │ Judicial │ Court    │ F  │ H │ 2024-12  │
│ ...│              │          │          │    │   │          │
├────┴──────────────┴──────────┴──────────┴────┴───┴──────────┤
│ Showing 1-25 of 150       [< Prev] [1] [2] [3] ... [Next >]│
└─────────────────────────────────────────────────────────────┘
```

### Table Columns

| Column | Field | Sortable | Notes |
|--------|-------|----------|-------|
| Name | `name` | Yes | Click to open detail |
| Position | `position` | Yes | Show label, not value |
| Organization | `organization` | Yes | |
| PEP Type | `pep_type` | Yes | Badge/chip: Domestic, Foreign, International |
| Status | `status` | Yes | Color-coded: Active=green, Former=yellow, Deceased=gray |
| Risk Level | `risk_level` | Yes | Badge: High=red, Medium=orange, Low=green |
| Last Checked | `last_checked` | Yes | Relative date |

### Filters

- **Search**: Free-text search on `name` (ILIKE + phonetic)
- **PEP Type**: Dropdown multi-select (domestic, foreign, international)
- **Status**: Dropdown multi-select (active, former, deceased)
- **Risk Level**: Dropdown multi-select (low, medium, high)
- **Show Archived**: Toggle to include `active=false` records

### Group By

Optional row grouping by: PEP Type, Status, Risk Level. Shows count per group.

---

## Page 2: PEP Person Detail / Form

### Layout (View Mode)

```
┌─────────────────────────────────────────────────────────────┐
│ [← Back]                                                    │
│                                                             │
│ ┌─ Status Bar ────────────────────────────────────────────┐ │
│ │ [Request Approval] [EDD with xacxom] [Schedule Review]  │ │
│ │ EDD: ● Pending ─── In Progress ─── Completed            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Header ────────────────────────────────┐ ┌─ Archive ─┐  │
│ │  Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)    │ │ [Archive] │  │
│ └─────────────────────────────────────────┘ └───────────┘  │
│                                                             │
│ ┌─ Left Column ──────────┐  ┌─ Right Column ─────────────┐ │
│ │ Date of Birth: 1968-06 │  │ Position: Head of State     │ │
│ │ Nationality: Mongolia  │  │ Custom Position: —          │ │
│ │ PEP Type: Domestic     │  │ Organization: Gov of MN     │ │
│ │ Status: Active         │  │ Org Type: Government        │ │
│ │                        │  │ Risk Level: ● High          │ │
│ └────────────────────────┘  └─────────────────────────────┘ │
│                                                             │
│ ┌─ Position Timeline ────┐  ┌─ Enhanced Due Diligence ───┐ │
│ │ Start Year: 2021       │  │ Monitoring: Quarterly       │ │
│ │ End Year: —            │  │ Last Review: 2025-01-15     │ │
│ │ Last Checked: 2025-01  │  │ Next Review: 2025-04-15     │ │
│ │ Self-Declared: No      │  │ Approved By: Admin User     │ │
│ │                        │  │ Approved Date: 2025-01-15   │ │
│ │                        │  │ Retention: 5 years          │ │
│ └────────────────────────┘  └─────────────────────────────┘ │
│                                                             │
│ ┌─ Tabs ──────────────────────────────────────────────────┐ │
│ │ [Related Persons] [Source of Wealth] [Additional Info]  │ │
│ │                                                         │ │
│ │ ┌─ Family Members ────────────────────────────────────┐ │ │
│ │ │ Name           │ Relation │ Verified  │ EDD Req │   │ │ │
│ │ │ Батсүх Г.      │ Spouse   │ 2024-06   │ Yes     │   │ │ │
│ │ │ [+ Add Family Member]                             │   │ │ │
│ │ └───────────────────────────────────────────────────┘   │ │
│ │                                                         │ │
│ │ ┌─ Close Associates ──────────────────────────────────┐ │ │
│ │ │ Name           │ Assoc Type   │ Verified │ EDD Req │ │ │
│ │ │ [+ Add Associate]                                  │  │ │
│ │ └───────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Activity / Audit Log ──────────────────────────────────┐ │
│ │ 2025-01-15 Admin: Changed edd_status from 'pending'     │ │
│ │                   to 'completed'                         │ │
│ │ 2025-01-15 Admin: Set senior_approval_id                │ │
│ │ 2024-06-01 User1: Created record                        │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Action Buttons (Header)

| Button | Visible When | Action |
|--------|-------------|--------|
| **Request Approval** | `senior_approval_id` is null AND `edd_status != 'completed'` | Opens Approval Modal |
| **EDD with xacxom** | Always | Calls `POST /pep-persons/{id}/edd-xacxom` |
| **Schedule EDD Review** | Always | Calls `POST /pep-persons/{id}/schedule-edd-review` |

### EDD Status Bar

Horizontal progress indicator showing: Pending → In Progress → Completed (with Review Needed as alternate state).

### Tabs

1. **Related Persons**: Two sub-tables — Family Members and Close Associates. Each with inline add/edit/remove.
2. **Source of Wealth & Funds**: Two text areas for `source_of_wealth` and `source_of_funds`.
3. **Additional Info**: `source` (text area) and `notes` (text area).

### Conditional Fields

- `custom_position`: Show only when `position == 'other'`
- `self_declaration_date`: Show only when `self_declared == true`
- `senior_approval_date`: Show only when `senior_approval_id` is set

---

## Page 3: PEP Person Form (Create / Edit)

Same layout as detail view, but all fields are editable. Form validates on submit.

### Validation Feedback

- Required fields marked with asterisk (*)
- Inline validation messages below each field
- Mongolian name format validation shows example format on error
- Duplicate (name + DOB) shows link to existing record on conflict

---

## Page 4: Approval Modal

```
┌─────────────────────────────────────┐
│ Request Senior Management Approval  │
│                                     │
│ Approved By: [Current User ▼]       │
│                                     │
│ Note:                               │
│ [________________________________] │
│ [________________________________] │
│                                     │
│           [Confirm] [Cancel]        │
└─────────────────────────────────────┘
```

---

## Page 5: Screenings List

```
┌─────────────────────────────────────────────────────────────┐
│ PEP Screenings                             [+ New Screening]│
├─────────────────────────────────────────────────────────────┤
│ Search: [________________] [Result ▼] [Method ▼] [Type ▼]  │
├────┬──────────────┬────────────┬────────┬─────┬─────┬──────┤
│ #  │ Name         │ Date       │ Result │Match│Score│By    │
├────┼──────────────┼────────────┼────────┼─────┼─────┼──────┤
│ 1  │ John Doe     │ 2025-01-15 │ Match  │ J.D.│  —  │Admin │
│ 2  │ Jane Smith   │ 2025-01-14 │No Match│  —  │  —  │User1 │
├────┴──────────────┴────────────┴────────┴─────┴─────┴──────┤
│ Page 1 of 10                                                │
└─────────────────────────────────────────────────────────────┘
```

### Filters

- **Search**: Free-text on `name`
- **Result**: match / possible / no_match
- **Screened By**: User dropdown (Manager only — users always filtered to self)
- **Group By**: Result, Screened By, Screening Date

---

## Page 6: Screening Detail / Form

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [← Back]                                                    │
│                                                             │
│ ┌─ Header ────────────────────────────────────────────────┐ │
│ │ [AI Screen] — runs the full screening workflow          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Person Information ───┐  ┌─ Screening Information ────┐ │
│ │ Name*: [____________]  │  │ Date: 2025-01-15 14:30     │ │
│ │ DOB: [__________]      │  │ Screened By: Admin          │ │
│ │ Nationality: [▼]       │  │ Type*: [Initial ▼]         │ │
│ └────────────────────────┘  │ Trigger Reason: [▼]        │ │
│                              │  (shown if type=trigger)   │ │
│                              └────────────────────────────┘ │
│                                                             │
│ ┌─ Results ──────────────┐  ┌─ Methodology ──────────────┐ │
│ │ Result: ● Match        │  │ Method*: [Database ▼]      │ │
│ │ Matched PEP: [Link]    │  │ Database Used: [▼]         │ │
│ │ Confidence: 95%        │  │  (shown if method=database)│ │
│ └────────────────────────┘  └────────────────────────────┘ │
│                                                             │
│ ┌─ Evidence & Documentation ──────────────────────────────┐ │
│ │ Evidence References:                                     │ │
│ │ [_____________________________________________________] │ │
│ │ Notes:                                                    │ │
│ │ [_____________________________________________________] │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Conditional Fields

- `trigger_reason`: Show only when `screening_type == 'trigger'`
- `matched_pep_id`, `confidence_score`: Show only when `result != 'no_match'`
- `database_used`: Show only when `screening_method == 'database'`

### AI Screen Button

Calls `POST /screenings/{id}/run`. Shows loading spinner while processing. On completion, refreshes the form to show results.

---

## Page 7: AI PEP Search Wizard

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ AI PEP Search                                               │
│                                                             │
│ ┌─ Search Parameters ────┐  ┌─ AI Configuration ─────────┐ │
│ │ Country*: [Mongolia ▼] │  │ Provider*: [Gemini ▼]      │ │
│ │ Position*: [_________] │  │ Model: [gemini-2.5-flash]  │ │
│ │ Year*: [current______] │  │                             │ │
│ └────────────────────────┘  └─────────────────────────────┘ │
│                                                             │
│ ┌─ Results ───────────────────────────────────────────────┐ │
│ │ Name        │ Title      │ Start │ End │ Born │ Notes │  │ │
│ ├─────────────┼────────────┼───────┼─────┼──────┼───────┤  │ │
│ │ Хүрэлсүх... │ Prime Min. │ 2017  │2021 │ 1968 │ ...  │[Create PEP]│
│ │ Оюун-Эрдэнэ│ Prime Min. │ 2021  │ —   │ 1980 │ ...  │[Create PEP]│
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│                    [Search with AI] [Close]                  │
└─────────────────────────────────────────────────────────────┘
```

### Behavior

1. AI Model field auto-updates when AI Provider changes (Gemini → `gemini-2.5-flash`, OpenAI → `gpt-4o`)
2. "Search with AI" clears previous results and shows loading indicator
3. Results table is read-only except for "Create PEP" button per row
4. "Create PEP" button disabled/hidden after PEP is created (show checkmark)
5. Clicking "Create PEP" opens the new PEP person form in a new dialog/tab

---

## Page 8: AI Position Search Wizard

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ AI Position Search                                          │
│                                                             │
│ ┌─ Search Parameters ────┐  ┌─ AI Configuration ─────────┐ │
│ │ Country*: [Mongolia ▼] │  │ Provider*: [Gemini ▼]      │ │
│ │ Year*: [2024_________] │  │ Model: [gemini-2.5-flash]  │ │
│ └────────────────────────┘  └─────────────────────────────┘ │
│                                                             │
│ ┌─ Results ───────────────────────────────────────────────┐ │
│ │ Position Title       │ Category      │ Notes     │      │ │
│ ├──────────────────────┼───────────────┼───────────┼──────┤ │
│ │ President of Mongolia│ head_state    │ Head of...│[Register]│
│ │ Prime Minister       │ head_state    │ Head of...│[Register]│
│ │ Chief Justice        │ judicial      │ Highest...│[Register]│
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│                      [Search] [Close]                       │
└─────────────────────────────────────────────────────────────┘
```

### Behavior

- "Register" creates a Position Template from the result row
- Button disabled after registration (show checkmark)
- Category column shows the enum label mapped from value

---

## Page 9: Web Scraper Wizard

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Scrape Official Source                                       │
│                                                             │
│ ┌─ Configuration ────────────────────────────────────────┐  │
│ │ Pages to Scrape: [1____] (0 = all available pages)     │  │
│ │ Status: Ready                                          │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ Results ───────────────────────────────────────────────┐ │
│ │ Year │ Name              │ Position           │         │ │
│ ├──────┼───────────────────┼────────────────────┼─────────┤ │
│ │ 2023 │ Ухнаа Хүрэлсүх    │ Ерөнхийлөгч        │         │ │
│ │ 2022 │ Ухнаа Хүрэлсүх    │ Ерөнхийлөгч        │         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│                  [Start Scraping] [Close]                    │
└─────────────────────────────────────────────────────────────┘
```

### Behavior

1. "Start Scraping" queues background job and shows toast notification
2. Status changes from "Ready" to "Job Queued"
3. Results populate when job completes (poll or WebSocket notification)
4. Show "Scraping in progress..." spinner while job runs

---

## Page 10: Position Templates List

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Position Templates                          [+ New Template] │
├─────────────────────────────────────────────────────────────┤
│ [Country ▼] [Category ▼] [Year: ___]                       │
├────┬─────────────────────┬──────────────┬─────────┬─────────┤
│ #  │ Position Title      │ Category     │ Country │ Year    │
├────┼─────────────────────┼──────────────┼─────────┼─────────┤
│ 1  │ President           │ Head of State│Mongolia │ 2024    │
│ 2  │ Prime Minister      │ Head of State│Mongolia │ 2024    │
└─────────────────────────────────────────────────────────────┘
```

Sorted by country, then name.

---

## Page 11: Settings (Manager Only)

```
┌─────────────────────────────────────────────────────────────┐
│ Settings                                                     │
│                                                             │
│ ┌─ Company ──────────────────────────────────────────────┐  │
│ │ Company Country: [Mongolia ▼]                          │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ AI Configuration ─────────────────────────────────────┐  │
│ │ Gemini Model: [gemini-2.5-flash__]                     │  │
│ │ OpenAI Model: [gpt-4o____________]                     │  │
│ │                                                        │  │
│ │ ⓘ API keys are configured via environment variables.   │  │
│ │   GOOGLE_API_KEY and OPENAI_API_KEY                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ Web Scraping ─────────────────────────────────────────┐  │
│ │ xacxom Search URL: [https://xacxom.iaac.mn/xacxom/... │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ User Management ──────────────────────────────────────┐  │
│ │ [View Users] [Create New User]                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│                          [Save]                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Shared UI Components

### 1. Badge / Chip Component

Used for PEP Type, Status, Risk Level with color coding:

| Value | Color |
|-------|-------|
| High risk / Active / Domestic | Red / Green / Blue |
| Medium risk / Former / Foreign | Orange / Yellow / Purple |
| Low risk / Deceased / International | Green / Gray / Teal |

### 2. Status Bar Component

Horizontal step indicator showing EDD workflow stages. Current step highlighted.

### 3. Toast Notifications

For background job feedback:
- **Info**: "Scraping job started in background"
- **Success**: "Scraping complete. Found 47 records."
- **Error**: "Failed to connect to xacxom.iaac.mn"

### 4. Confirmation Dialogs

For destructive actions (delete, archive) and approval confirmation.

### 5. Loading States

- Full-page spinner for initial data loads
- Inline spinner on buttons during API calls (AI search, EDD scraping)
- Skeleton loading for tables

### 6. Empty States

Each list page shows an illustration + "Create your first..." message when no records exist.

---

## Responsive Behavior

- **Desktop (>1024px)**: Two-column layouts as shown above
- **Tablet (768-1024px)**: Single column, stacked groups
- **Mobile (<768px)**: Single column, collapsible sections, bottom navigation
