# Crucible CLI Display Guide

Conventions for consistent display across the CLI. Follow these rules when adding new subcommands or modifying existing ones.

---

## Autocomplete Dropdowns (interactive shell)

All completions that pair a **key** with descriptive **metadata** must use HTML formatting:

```python
from prompt_toolkit.formatted_text import HTML as _HTML

yield Completion(
    key + ' ',
    start_position=-len(prefix),
    display=_HTML(f'<b>{key}</b>'),              # bold key in the dropdown list
    display_meta=_HTML(f'<ansibrightblack>{meta}</ansibrightblack>'),  # dim right-side hint
)
```

For richer metadata (multiple fields), join with ` · `:

```python
display_meta=_HTML(' | '.join([
    f'{resource_type}',                            # plain — cyan is illegible in dropdowns
    f'<b>{name}</b>',
    f'<ansibrightblack>{reason}</ansibrightblack>',
]))
```

**Applied to:** `use PROJECT_ID`, `config set current_project`, `deletion approve/reject ID`

For completions with no meaningful metadata (e.g. subcommand names, flag choices), plain `Completion(name + ' ', ...)` without `display`/`display_meta` is fine.

---

## Field Printers (`term.field_printer`)

`field_printer(n)` returns a callable `_p(label, value)` that left-pads labels to `n` characters.

| Width | Use case |
|-------|----------|
| 14    | Standard detail views: dataset, sample, project, instrument |
| 16    | Wide-label views: user, deletion request, whoami |

```python
_p = term.field_printer(14)   # dataset / sample / project / instrument
_p = term.field_printer(16)   # user / deletion / whoami
```

Don't use widths < 14; labels will collide with values and look misaligned.

---

## Tables (`term.table`)

Every `term.table()` call must include `max_widths`. The renderer treats these as upper bounds and shrinks columns to the current terminal width. Redirected output uses a deterministic 100-column width.

```python
term.table(
    rows,
    headers,
    max_widths=[...],
    min_widths=[...],
)
```

Use `min_widths` for crowded tables when selected columns should be protected during shrinking. Keep full 26-character MFIDs, 25-character project or instrument IDs, and 24-character usernames whenever the remaining columns can shrink enough. The renderer may reduce protected columns when the terminal is too narrow for their combined preferred widths.

Width declarations should still aim for a total of no more than 100 columns, including two-space padding between columns.

Common patterns:

| Content | max_widths |
|---------|------------|
| Name + MFID + Measurement + Session | `[35, 26, 15, 20]` |
| Name + MFID + Measurement | `[35, 26, 15]` |
| Name + MFID + Type | `[35, 26, 20]` |
| File + Size | `[60, 10]` |
| File + Size + Status | `[60, 10, 4]` |
| ID + Resource ID + Type + Name + Status + Date | `[6, 26, 10, 24, 10, 10]` |
| Username + Name + user ID | `[25, 25, 26]` |
| Name + ORCID + Email | `[25, 19, 35]` |
| Project ID + Title + Organization | `[25, 30, 20]` |

Username columns must allow the full 24-character limit before truncating. Project ID, instrument ID, and project-backed access-group columns must allow the full 25-character limit.

## JSON output

Add `--json` only when a command has a defined machine-readable result. Collection and search commands emit a JSON array, singleton commands emit a JSON object, and empty collections emit `[]`.

Serialize the raw client result before any terminal headers, links, relative timestamps, placeholders, user-resolution helpers, or display-only restructuring. Write successful JSON to stdout and pass `args` to `helpers.fail()` so errors are emitted as structured JSON on stderr. Do not mix informational logs or human-readable success messages into JSON output.

Future expansion may cover relationship and membership listings, ingestion records, ACL models, deletion workflows, signed file links, local status, and mutation responses. Add these only after defining whether the output is a raw API response or an explicit client-owned schema; do not infer a JSON contract from the human display.

---

## ANSI Color Conventions

Use `term.*` helpers. They are TTY-safe no-ops when output is redirected and respect both `NO_COLOR` and the global `--no-color` option.

| Color | Use case | Helper |
|-------|----------|--------|
| Cyan | IDs (MFID, ORCID, project IDs) | `term.cyan(s)` / `term.mfid_link()` / `term.orcid_link()` |
| Dim / grey | Supplementary info, empty placeholders, timestamps | `term.dim(s)` |
| Bold | Section headers | `term.bold(s)` / `term.header()` |
| Yellow | Status: pending or warning | `term.yellow(s)` |
| Green | Status: approved or success | `term.green(s)` |
| Red | Status: rejected or error | `term.red(s)` |

Pass lifecycle and workflow statuses through `term.status_label()`. Active states are green, maintenance and pending states are yellow, decommissioned states are dim, and rejected or failed states are red.

Use `term.success()` for completed mutations. It prints a green `Success:` label for interactive terminals, remains plain when color is disabled or output is redirected, and emits nothing for JSON output.

Symbols may supplement text only in compact health summaries, repeated checklist results, tree structures, interactive selection markers, and progress indicators. Use `term.status_marker()` for compact health and checklist rows so interactive output uses a symbol while redirected output uses an explicit word. Do not use symbols for mutation confirmations, warning paragraphs, errors, logs, JSON, or table statuses that already have a clear word.

Use `-` for missing or null values in tables, not `None` or an empty string.

Use `term.fmt_bool()` for nullable boolean fields in human-readable output so true, false, and missing values render as `yes`, `no`, and `-`. Preserve native booleans and nulls in JSON output.

Pass project membership roles through `term.role_label()`. Member tables are ordered from highest to lowest standing and use this palette:

| API role | Display | Color |
|---|---|---|
| `owner` | `lead` | Gold |
| `admin` | `admin` | Red |
| `editor` | `editor` | Blue |
| `contributor` | `contributor` | Cyan |
| `viewer` | `viewer` | Gray |

Label resource slugs explicitly as `Project ID` or `Instrument ID`, and label canonical identifiers as `MFID`. Detail views for slug-addressable resources should show both when available.

## Interactive prompts

Use the shared helpers in `cli.helpers` instead of calling `input()` directly for creation and configuration fields.

- Use `prompt_required()` for required text or validated identifiers.
- Use `prompt_optional()` for values that may be omitted and for configured defaults.
- Use `prompt_secret()` for API keys and other credentials.
- Use `prompt_choice()` for a fixed set of accepted values.
- Reuse the same validator used by the Python resource method whenever one exists.
- Invalid input must explain the problem and prompt again. Never silently discard it.
- Required prompts must fail with status 2 when stdin is not interactive. Optional prompts should be skipped, and configured defaults may be used.
- Keep labels bold, hints and defaults dim, and validation errors red. Do not color user-entered values.

Use `prompt_confirm()` for actions that require a yes-or-no decision. Confirmation must default to no for destructive operations, accept `yes` and `no` in addition to their single-letter forms, explain invalid responses, and fail with status 2 outside an interactive terminal. Commands intended for automation should provide an explicit bypass such as `--yes`.

API operations that support a server-side preview should remain preview-only by default and execute only when the user supplies `--confirm`. Do not add an interactive prompt after a preview response.

## Errors and warnings

Route command failures through `helpers.fail()` so HTTP status, reason, validation details, JSON output, debug tracebacks, and exit status remain consistent. Do not print raw API validation structures directly.

- Print the error heading and HTTP status in red.
- Print warning headings in yellow.
- Prefix non-fatal warnings with `Warning:` and an actionable explanation.
- Print field names in bold.
- Keep explanatory text uncolored.
- Write errors and warnings to stderr.
- Preserve the HTTP status in output while using process exit status `1` for command failure.
- Never include ANSI codes in JSON or redirected output.

---

## Headers and Subheaders

```python
term.header("Dataset")              # top-level section: bold "── Dataset ──────"
term.subheader("Ownership")         # secondary section: dim "  Ownership"
```

Include a count in the title when listing multiple items:

```python
term.header(f"Datasets · {project_id} ({len(datasets)})")
term.header(f"Deletion Requests — pending ({len(records)})")
```

---

## Timestamps

Always pass through `term.fmt_ts()` for display. Never print raw ISO strings.

```python
_p("Requested", term.fmt_ts(record.get('request_time')))
```

In table columns where space is tight, use `_short_ts(ts)` → `YYYY-MM-DD` (26 chars max with column padding).
