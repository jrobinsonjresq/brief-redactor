# brief-redactor
_Python script to redact private material from .docx legal documents. Finds and replaces quotes of non-public information with xxx characters. Non destructive of input file; outputs log of changes via sidecar file. (Human developed with AI assistance)_

---

## Background

Utah Rule of Appellate Procedure 21(h) requires that any filing that contains non-public information must be accompanied by an identical public version with the sensitive information removed. 

This is a command-line tool for producing redacted public versions of appellate briefs in compliance with the rule.

It identifies direct quotes within paragraphs that cite private source documents — transcripts, findings of fact, &c — and replaces the quoted text with `x` characters on a strict 1:1 basis. All formatting, pagination, styles, and document structure are preserved.

Developed for Utah appellate practice. Tested against family law briefing drafted in Microsoft Word and OnlyOffice.

Obviously, this tool may not be suitable for your use case and no warranty is made regarding its fitness for any purpose. Users are advised to manually confirm sufficiency of redaction.

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

**Example:**

Before:
```
Smith testified: "The light was red when the vehicle entered the intersection." Jan. 1 Tr. at 98:22.
```

After:
```
Smith testified: "xxx xxxxx xxx xxx xxxx xxx xxxxxxx xxxxxxx xxx xxxxxxxxxxxx." Jan. 1 Tr. at 98:22.
```

### What is not redacted

- Paraphrased or summarized content (not in quotation marks)
- Quotes citing only public documents (e.g., the judgment, published case law)
- Case citations, statutes, and rules
- Numerical figures, dollar amounts, dates

Users should consider conducting a manual review for paraphrased material drawn from private records if a more conservative redaction is required.

### Cross-run quote handling

DOCX files store text in XML "runs" — small chunks of consistently-formatted text. A single visible sentence may be split across many runs due to formatting changes, spell-check markup, or revision tracking. A naive run-by-run redaction approach breaks when a quoted passage spans multiple runs: the script sees an opening quotation mark without a closing mark in the same run and incorrectly redacts surrounding prose.

This tool solves the problem by assembling the full paragraph text across all runs into a single string, identifying quote boundaries in that string, then mapping the redaction positions back to individual runs by character index. This is intended to correctly handle all cross-run quote splits regardless of run structure. It may not be sufficient to capture edge cases in your input file.

### Namespace preservation

Python's standard `xml.etree.ElementTree` library mangles XML namespace prefixes when writing — replacing `w:rPr` with `ns0:rPr` and similar. Word and LibreOffice appear to rely on the `w:` prefix and render documents with mangled namespaces incorrectly (garbled text, lost styles, or unreadable files). This tool uses `lxml` instead, because it preserves namespace prefixes and produces output that is byte-compatible with the original.

### ZIP entry order

DOCX files are ZIP archives. Office applications require `[Content_Types].xml` and `_rels/` entries to appear first in the archive. This tool repacks the ZIP by iterating the original archive's entry list in order, substituting only the modified XML files, preserving all other entries unchanged.

---

## Workflow recommendation

For best results with briefs drafted in OnlyOffice or Google Docs, normalize the DOCX through Word before running the script:

1. Open the brief in Microsoft Word or Word Online
2. Save/download as DOCX (it appears that Word normalizes the XML on save)
3. Run `redact_brief.py` on the Word-normalized file

This step is obviously not required for briefs drafted natively in Word, and may not even be necessary in other contexts. More testing required to confirm/deny necessity of normalization steps.

---

## Log file

Every run produces a sidecar log file (e.g., `brief_PUBLIC_redaction_log.txt`) documenting:

- Timestamp, input file, output file
- Citation patterns used
- Total paragraphs and quotes redacted
- Each redacted quote (first 80 characters), by source file

The `--dry-run` flag produces the log without writing a redacted output file.

---

## Citation presets

### `utah` (default)

Matches transcript citations (`Sept. 4 Tr.`, `June 19 Tr.`, etc.) and findings of fact references (`FFCL ¶`, `Custody FFCL`). Default does not include searching for direct cites to the record (eg., 'R. 1999').

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
- **No attachment handling** — appendices and addenda must be handled separately

---

## Contributing

Issues and pull requests welcome. See `CONTRIBUTING.md`.

---

## License

MIT License. See `LICENSE`.

---

## Author

[J. Robinson Esq. PLLC](https://jrobinsonesq.com)  
Deep Research | Legal Writing | Appeals (licensed in Maine and Utah)
[info@jrobinsonesq.com](mailto:info@jrobinsonesq.com)
