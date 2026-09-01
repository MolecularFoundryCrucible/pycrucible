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

Every `term.table()` call must include `max_widths` to prevent overflow on narrow terminals.

```python
term.table(rows, headers, max_widths=[...])
```

**Width budget:** aim for a total of ≤ 100 columns (including 2-space padding between columns).

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

Username, project ID, instrument ID, and project-backed access-group columns must allow the full current 25-character identifier limit before truncating.

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

Use `-` for missing or null values in tables, not `None` or an empty string.

## Errors and warnings

Route command failures through `helpers.fail()` so HTTP status, reason, validation details, JSON output, debug tracebacks, and exit status remain consistent. Do not print raw API validation structures directly.

- Print the error heading and HTTP status in red.
- Print warning headings in yellow.
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
