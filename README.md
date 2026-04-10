# brief-redactor

A command-line tool for producing redacted public versions of appellate briefs in DOCX format.

Identifies direct quotes (enclosed in quotation marks) within paragraphs that cite private source documents — transcripts, findings of fact, and similar trial court records — and replaces the quoted text with `x` characters on a strict 1:1 basis. All formatting, pagination, styles, and document structure are preserved exactly.

Developed for appellate practice. Tested against briefs drafted in Microsoft Word and OnlyOffice, filed in the Utah Court of Appeals.

---

## Background

Under Utah Rule of Appellate Procedure 21(h), a filing that contains non-public information must be accompanied by an identical public version with that information removed. Trial court transcripts and findings of fact are classified as private records under Utah Code of Judicial Administration Rule 4-202.02(4)(B). Briefs routinely quote from these documents.

This tool automates the redaction of those quotes, producing a public brief that is structurally and visually identical to the private version — same page numbers, same formatting, same citation references — with only the quoted content replaced.

---

## Installation

**Requirements:** Python 3.8+, `lxml`

```bash
pip install lxml
```

No other dependencies. Clone or download `redact_brief.py` and run it directly.

---

## Usage

```bash
# Basic usage — produces brief_PRIVATE_PUBLIC.docx
python redact_brief.py brief_PRIVATE.docx

# Specify output path
python redact_brief.py brief_PRIVATE.docx brief_PUBLIC.docx

# Dry run — log what would be redacted without writing output
python redact_brief.py brief_PRIVATE.docx --dry-run

# Use federal citation patterns
python redact_brief.py brief.docx --preset federal

# Custom citation pattern (repeatable)
python redact_brief.py brief.docx --pattern "Tr\. at \d+:\d+" --pattern "Dkt\. No\."
```

### Options

| Option | Description |
|--------|-------------|
| `input` | Input DOCX file. **Never modified.** |
| `output` | Output DOCX file. Default: `{input}_PUBLIC.docx` |
| `--preset` | Citation pattern preset: `utah` (default) or `federal` |
| `--pattern REGEX` | Custom citation pattern. Overrides `--preset`. Repeatable. |
| `--dry-run` | Report what would be redacted; write no output file |
| `--no-log` | Suppress sidecar log file |
| `--log PATH` | Custom path for log file |

---

## How it works

### What gets redacted

The script redacts alphabetic characters inside quotation marks (both straight `"` and smart `"` / `"`) in any paragraph that also contains a citation matching the active pattern set. Numbers, spaces, and punctuation inside quotes are preserved. The citation itself is never touched — only the quoted content.

**Example (Utah appellate mode):**

Before:
```
Jesus testified: "I just decided to do something a lot easy, no physical hard." Sept. 4 Tr. at 85:17.
```

After:
```
Jesus testified: "x xxxx xxxxxxx xx xx xxxxxxxxx x xxx xxxx, xx xxxxxxxx xxxx xxxx." Sept. 4 Tr. at 85:17.
```

Quotes citing the **Decree** (a public document) are not redacted, because the Decree does not contain a private citation pattern.

### What is not redacted

- Paraphrased or summarized content (not in quotation marks)
- Quotes citing only public documents (e.g., the Decree, published case law)
- Case citations, statutes, and rules
- Numerical figures, dollar amounts, dates

Consider a manual pass for paraphrased material drawn from private records if a more conservative redaction is required.

### Cross-run quote handling

DOCX files store text in XML "runs" — small chunks of consistently-formatted text. A single visible sentence may be split across many runs due to formatting changes, spell-check markup, or revision tracking. A naive run-by-run redaction approach breaks when a quoted passage spans multiple runs: the script sees an opening quotation mark without a closing mark in the same run and incorrectly redacts surrounding prose.

This tool solves the problem by assembling the full paragraph text across all runs into a single string, identifying quote boundaries in that string, then mapping the redaction positions back to individual runs by character index. This correctly handles all cross-run quote splits regardless of run structure.

### Namespace preservation

Python's standard `xml.etree.ElementTree` library mangles XML namespace prefixes when writing — replacing `w:rPr` with `ns0:rPr` and similar. Word and LibreOffice rely on the `w:` prefix and render documents with mangled namespaces incorrectly (garbled text, lost styles, or unreadable files). This tool uses `lxml`, which preserves namespace prefixes exactly, producing output that is byte-compatible with the original except for the redacted characters.

### ZIP entry order

DOCX files are ZIP archives. Office applications require `[Content_Types].xml` and `_rels/` entries to appear first in the archive. This tool repacks the ZIP by iterating the original archive's entry list in order, substituting only the modified XML files, preserving all other entries unchanged.

---

## Workflow recommendation

For best results with briefs drafted in OnlyOffice or Google Docs, normalize the DOCX through Word before running the script:

1. Open the brief in Microsoft Word or Word Online
2. Save/download as DOCX (Word normalizes the XML on save)
3. Run `redact_brief.py` on the Word-normalized file

This step is not required for briefs drafted natively in Word.

---

## Log file

Every run produces a sidecar log file (e.g., `brief_PUBLIC_redaction_log.txt`) documenting:

- Timestamp, input file, output file
- Citation patterns used
- Total paragraphs and quotes redacted
- Each redacted quote (first 80 characters), by source file

The `--dry-run` flag produces the log without writing a redacted output file, useful for review before committing to redaction.

---

## Citation presets

### `utah` (default)

Matches transcript citations (`Sept. 4 Tr.`, `June 19 Tr.`, etc.) and findings of fact references (`FFCL ¶`, `Custody FFCL`). Designed for Utah Court of Appeals and Utah Supreme Court practice.

### `federal`

Matches federal transcript citations (`Tr. at 123:4`), findings of fact, and Joint Appendix references (`J.A. 45`).

### Custom patterns

Pass one or more `--pattern REGEX` arguments to use custom citation patterns. Standard Python regex syntax. The pattern is matched against the full paragraph text.

```bash
python redact_brief.py brief.docx \
  --pattern "Tr\. at \d+:\d+" \
  --pattern "ROA\.\d+" \
  --pattern "App\. \d+"
```

---

## Limitations

- **Paraphrased content** is not redacted — only direct quotes in quotation marks
- **Endnotes** are processed; content in text boxes or headers/footers is not
- **PDF output** is not produced — export to PDF from your word processor after redaction
- **No attachment handling** — appendices and addenda must be handled separately (they are typically separate files)

---

## Contributing

Issues and pull requests welcome. See `CONTRIBUTING.md`.

---

## License

MIT License. See `LICENSE`.

---

## Author

[J. Robinson Esq. PLLC](https://jrobinsonesq.com)  
Appellate practice — Maine and Utah  
[john@jrobinsonesq.com](mailto:john@jrobinsonesq.com)
