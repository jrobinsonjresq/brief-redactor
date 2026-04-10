# Contributing to brief-redactor

Thanks for your interest in contributing. This is a small focused tool — contributions that keep it simple and well-documented are most welcome.

## What's welcome

- **Additional citation presets** for other jurisdictions (5th Circuit, California, New York, etc.)
- **Bug reports** with a minimal reproducible example (anonymized DOCX or description of the XML structure that caused the issue)
- **Edge case fixes** for unusual DOCX structures (heavily tracked-changes documents, complex footnote nesting, etc.)
- **Documentation improvements**

## What's out of scope for v1

- PDF output (planned for v2)
- Web UI (planned for v2)
- Attachment/appendix handling
- Support for formats other than DOCX

## Adding a citation preset

Edit `redact_brief.py` and add an entry to the `PRESET_PATTERNS` dict:

```python
PRESET_PATTERNS = {
    'utah': UTAH_APPELLATE_PATTERNS,
    'federal': FEDERAL_PATTERNS,
    'fifth_circuit': [        # your new preset
        r'Tr\. at \d+:\d+',
        r'R\. \d+',
    ],
}
```

Include a comment explaining what each pattern matches and a note in the README under "Citation presets."

## Reporting a bug

Please include:
1. The command you ran
2. The error message or incorrect behavior
3. A description of the DOCX structure that triggered it (anonymized is fine — just describe the run/paragraph structure around the quote that wasn't handled correctly)

## Code style

- Standard Python 3.8+ idioms
- No dependencies beyond `lxml`
- Functions should be small and clearly named
- Comments on non-obvious logic (especially XML/namespace handling)
