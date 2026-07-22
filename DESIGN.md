# PSI Shared Dashboard Design Contract

## 1. Intent
A restrained operational workspace for trusted reporting: show what is current, what is ready, and what needs attention without implying remote authentication or release authority in local mode.

## 2. Tokens
- Colors: `--ink #17211b`, `--muted #66756b`, `--canvas #f4f7f2`, `--surface #ffffff`, `--line #d9e3d8`, `--accent #1d5138`, `--accent-soft #e4f0df`, `--signal #b45309`, `--danger #a33b32`, `--focus #2457a6`.
- Spacing: `--space-1 .5rem`, `--space-2 .75rem`, `--space-3 1rem`, `--space-4 1.5rem`, `--space-5 2rem`, `--space-6 3rem`.
- Shape/elevation: `--radius-sm .5rem`, `--radius-md .75rem`, `--radius-lg 1.25rem`; one soft surface shadow only.
- Type: system sans; 12px labels, 14px body, 16px lead, 30px display; line-height 1.5.

## 3. Primitives
Header/status strip, metric card, data table, badge, form field, file drop field, notice, activity item, and action button. Each uses semantic HTML and visible labels.

## 4. States
Controls define default, hover, focus-visible, active, disabled, loading, empty, and error states. Loading uses text and progress, never a misleading success state. Empty states explain the next safe action. Errors preserve user input and identify whether auth, config, metadata, or file data failed.

## 5. Layout
Desktop uses a 12-column grid with overview metrics, matrix, and activity in cards. Upload is a dedicated card below the overview. Tablet collapses secondary columns; mobile is one column with horizontally scrollable data tables and full-width actions. Minimum interactive target is 44px.

## 6. Accessibility and motion
Use landmarks, heading order, native form controls, table captions, `aria-live` status, keyboard order, and `:focus-visible` outlines. Color never carries status alone. Motion is limited to progress/state transitions and disabled under `prefers-reduced-motion`.

## 7. Ant Design migration and overlap contract
- The primary weekly upload surface adopts Ant Design 5.27.1 reset tokens and component language through a pinned CDN stylesheet, with local CSS preserving control behavior if the CDN is unavailable.
- Primitives map to Ant Design Card, Alert, Button, Input, Select-like native select, Tag/Badge, and Upload-like file controls. Native controls remain intentional because this app is static HTML/JS, not React.
- Layout uses normal document flow, `minmax(0, 1fr)` grids, intrinsic card height, `overflow-wrap:anywhere`, and line-heights above 1. No text container may use a fixed height. At 375px, checklist rows stack their action below the label.
- Visual verification must check scroll width and text bounding-box intersections at 375, 768, and 1280px.

## 8. Trust boundaries
The primary PSI flow is upload-only: local mode accepts anonymous multipart uploads and uses `anonymous-uploader` as an audit actor. Team name and reporting period are user-provided metadata, not an access-control boundary; this warning is visible in the page. Immutable snapshot history, checksums, reconciliation, and existing guarded release controls remain available locally. Supabase mode still requires an authenticated bearer and server-side service configuration because its RLS/storage policies are not designed for anonymous writes. Browser config accepts only URL and publishable key; no service secret is read or displayed. Reviewer controls can advance legal lifecycle states but never publish. Admin release actions report guarded service status and never imply success locally.
