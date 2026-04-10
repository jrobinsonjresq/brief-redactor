#!/usr/bin/env python3
"""
brief-redactor: Redact quoted material from appellate brief DOCX files.

Identifies direct quotes (in quotation marks) within paragraphs that contain
citations to private source documents (transcripts, findings of fact, etc.)
and replaces the quoted text with x's on a 1:1 character basis, preserving
all formatting, pagination, and document structure.

Usage:
    python redact_brief.py input.docx [output.docx] [options]

See README.md for full documentation.
"""

import argparse
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    print("Error: lxml is required. Install with: pip install lxml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Default citation patterns (Utah appellate)
# ---------------------------------------------------------------------------

UTAH_APPELLATE_PATTERNS = [
    # Transcript citations: Sept. 4 Tr., June 19 Tr., etc.
    r'(?:Jan\.|Feb\.|Mar\.|Apr\.|May|June|July|Aug\.|Sept\.|Oct\.|Nov\.|Dec\.)\s+\d+\s+Tr\.',
    # Findings of Fact / Conclusions of Law
    r'FFCL\s*[¶§\d\s]',
    # Custody FFCL
    r'Custody\s+FFCL',
]

FEDERAL_PATTERNS = [
    # Federal transcript citations: Tr. at 123:4
    r'Tr\.\s+(?:at\s+)?\d+:\d+',
    # Federal findings
    r'Finding[s]?\s+(?:of\s+Fact\s+)?(?:No\.)?\s*\d+',
    # Joint Appendix
    r'J\.?A\.?\s+\d+',
]

PRESET_PATTERNS = {
    'utah': UTAH_APPELLATE_PATTERNS,
    'federal': FEDERAL_PATTERNS,
}

# ---------------------------------------------------------------------------
# DOCX namespace
# ---------------------------------------------------------------------------

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W_T = f'{{{W_NS}}}t'
W_P = f'{{{W_NS}}}p'

# Quote characters
OPEN_QUOTES = ('"', '\u201c')   # straight and left smart
CLOSE_MAP = {'"': '"', '\u201c': '\u201d'}


# ---------------------------------------------------------------------------
# Core redaction logic
# ---------------------------------------------------------------------------

def build_cite_pattern(patterns):
    """Compile a single regex from a list of pattern strings."""
    combined = '|'.join(f'(?:{p})' for p in patterns)
    return re.compile(combined)


def should_redact_para(text, cite_pattern):
    """Return True if paragraph has quoted material AND a private citation."""
    has_quote = any(q in text for q in OPEN_QUOTES + ('"', '\u201d'))
    has_cite = bool(cite_pattern.search(text))
    return has_quote and has_cite


def find_quote_spans(text):
    """
    Return a set of character positions inside quoted strings.
    Handles quotes that use either straight or smart quote characters.
    Only marks alphabetic characters for redaction (preserves punctuation,
    spaces, numbers inside quotes).
    """
    redact_positions = set()
    i = 0
    while i < len(text):
        if text[i] in OPEN_QUOTES:
            close_q = CLOSE_MAP[text[i]]
            j = i + 1
            while j < len(text) and text[j] != close_q:
                j += 1
            if j < len(text):
                for k in range(i + 1, j):
                    if text[k].isalpha():
                        redact_positions.add(k)
                i = j + 1
            else:
                i += 1
        else:
            i += 1
    return redact_positions


def redact_paragraph(para, cite_pattern):
    """
    Process a single paragraph element.

    Assembles full paragraph text across all runs, identifies quote spans,
    then maps redactions back to individual text runs by character position.
    This handles quotes that span multiple XML runs (a common occurrence
    when Word applies formatting mid-sentence).

    Returns a list of (original_quote_snippet, position) tuples for logging,
    or an empty list if nothing was redacted.
    """
    t_elements = list(para.iter(W_T))
    if not t_elements:
        return []

    # Build full text and a character → (run_index, offset) map
    full_chars = []
    char_map = []
    for idx, t in enumerate(t_elements):
        text = t.text or ''
        for offset, ch in enumerate(text):
            full_chars.append(ch)
            char_map.append((idx, offset))

    full_str = ''.join(full_chars)

    if not should_redact_para(full_str, cite_pattern):
        return []

    redact_positions = find_quote_spans(full_str)
    if not redact_positions:
        return []

    # Collect snippets for logging before modifying
    log_entries = []
    i = 0
    while i < len(full_str):
        if full_str[i] in OPEN_QUOTES:
            close_q = CLOSE_MAP[full_str[i]]
            j = i + 1
            while j < len(full_str) and full_str[j] != close_q:
                j += 1
            if j < len(full_str):
                snippet = full_str[i:j+1]
                log_entries.append(snippet[:80] + ('...' if len(snippet) > 80 else ''))
                i = j + 1
            else:
                i += 1
        else:
            i += 1

    # Apply redactions to runs
    new_texts = [list(t.text or '') for t in t_elements]
    for pos in redact_positions:
        t_idx, offset = char_map[pos]
        new_texts[t_idx][offset] = 'x'

    for t, new_chars in zip(t_elements, new_texts):
        new_text = ''.join(new_chars)
        if new_text != (t.text or ''):
            t.text = new_text

    return log_entries


def process_xml(xml_bytes, cite_pattern):
    """
    Parse an XML file, redact qualifying quoted passages, and return
    the modified XML bytes plus a list of log entries.
    """
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(xml_bytes, parser)

    all_log_entries = []
    para_count = 0

    for para in root.iter(W_P):
        entries = redact_paragraph(para, cite_pattern)
        if entries:
            para_count += 1
            all_log_entries.extend(entries)

    output_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding='UTF-8',
        standalone=True
    )
    return output_bytes, para_count, all_log_entries


# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------

FILES_TO_PROCESS = [
    'word/document.xml',
    'word/footnotes.xml',
    'word/endnotes.xml',
]


def redact_docx(input_path, output_path, cite_pattern, dry_run=False):
    """
    Main entry point. Reads input_path, redacts qualifying quotes,
    writes to output_path (unless dry_run), returns log data.
    """
    results = {}

    with zipfile.ZipFile(input_path, 'r') as zin:
        available = set(zin.namelist())
        to_process = [f for f in FILES_TO_PROCESS if f in available]

        # Process each XML file
        modified = {}
        for fname in to_process:
            xml_bytes = zin.read(fname)
            new_bytes, para_count, log_entries = process_xml(xml_bytes, cite_pattern)
            modified[fname] = (new_bytes, para_count, log_entries)
            results[fname] = {
                'paragraphs_redacted': para_count,
                'quotes_redacted': len(log_entries),
                'log_entries': log_entries,
            }

        if not dry_run:
            # Repack: copy all entries in original order, substituting modified files
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename in modified:
                        zout.writestr(item, modified[item.filename][0])
                    else:
                        zout.writestr(item, zin.read(item.filename))

    return results


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_log(log_path, input_path, output_path, results, dry_run, patterns):
    """Write a sidecar log file documenting what was (or would be) redacted."""
    total_paras = sum(r['paragraphs_redacted'] for r in results.values())
    total_quotes = sum(r['quotes_redacted'] for r in results.values())

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("BRIEF REDACTOR — REDACTION LOG\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Input:        {input_path}\n")
        f.write(f"Output:       {output_path if not dry_run else '(dry run — no output written)'}\n")
        f.write(f"Mode:         {'DRY RUN' if dry_run else 'REDACTED'}\n\n")
        f.write(f"Citation patterns used:\n")
        for p in patterns:
            f.write(f"  {p}\n")
        f.write(f"\nSUMMARY\n{'-' * 40}\n")
        f.write(f"Total paragraphs redacted: {total_paras}\n")
        f.write(f"Total quotes redacted:     {total_quotes}\n\n")

        for fname, data in results.items():
            if not data['log_entries']:
                continue
            f.write(f"\n{fname.upper()}\n{'-' * 40}\n")
            for i, entry in enumerate(data['log_entries'], 1):
                f.write(f"  {i:3}. {entry}\n")

    return total_quotes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description='Redact quoted material from appellate brief DOCX files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Redact using Utah appellate defaults
  python redact_brief.py brief.docx

  # Specify output path
  python redact_brief.py brief_PRIVATE.docx brief_PUBLIC.docx

  # Dry run — log what would be redacted without writing output
  python redact_brief.py brief.docx --dry-run

  # Use federal citation patterns
  python redact_brief.py brief.docx --preset federal

  # Use custom citation pattern
  python redact_brief.py brief.docx --pattern "Tr\\. at \\d+:\\d+" --pattern "Dkt\\. No\\."

  # Suppress log file
  python redact_brief.py brief.docx --no-log
        """
    )
    parser.add_argument('input', help='Input DOCX file (not modified)')
    parser.add_argument('output', nargs='?', help='Output DOCX file (default: input_PUBLIC.docx)')
    parser.add_argument(
        '--preset', choices=list(PRESET_PATTERNS.keys()),
        default='utah',
        help='Citation pattern preset (default: utah)'
    )
    parser.add_argument(
        '--pattern', action='append', dest='patterns', metavar='REGEX',
        help='Custom citation pattern (regex). Overrides --preset. Repeatable.'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Report what would be redacted without writing output'
    )
    parser.add_argument(
        '--no-log', action='store_true',
        help='Do not write a sidecar log file'
    )
    parser.add_argument(
        '--log', metavar='PATH',
        help='Custom path for log file (default: output_redaction_log.txt)'
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() != '.docx':
        print(f"Warning: Input file does not have .docx extension: {input_path}")

    # Resolve output path
    if args.dry_run:
        output_path = Path('/dev/null')
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_stem(input_path.stem + '_PUBLIC')

    # Resolve patterns
    if args.patterns:
        patterns = args.patterns
        preset_name = 'custom'
    else:
        preset_name = args.preset
        patterns = PRESET_PATTERNS[preset_name]

    cite_pattern = build_cite_pattern(patterns)

    # Resolve log path
    if args.no_log:
        log_path = None
    elif args.log:
        log_path = Path(args.log)
    elif args.dry_run:
        log_path = input_path.with_stem(input_path.stem + '_dryrun_log').with_suffix('.txt')
    else:
        log_path = output_path.with_stem(output_path.stem + '_redaction_log').with_suffix('.txt')

    # Run
    print(f"brief-redactor")
    print(f"  Input:   {input_path}")
    if not args.dry_run:
        print(f"  Output:  {output_path}")
    print(f"  Preset:  {preset_name}")
    print(f"  Mode:    {'DRY RUN' if args.dry_run else 'redact'}")
    print()

    try:
        results = redact_docx(
            str(input_path),
            str(output_path),
            cite_pattern,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"Error during processing: {e}")
        raise

    # Report
    total_paras = sum(r['paragraphs_redacted'] for r in results.values())
    total_quotes = sum(r['quotes_redacted'] for r in results.values())

    for fname, data in results.items():
        if data['paragraphs_redacted']:
            print(f"  {fname}: {data['paragraphs_redacted']} paragraphs, "
                  f"{data['quotes_redacted']} quotes redacted")

    print(f"\n  Total: {total_quotes} quotes across {total_paras} paragraphs")

    if log_path:
        write_log(str(log_path), str(input_path), str(output_path),
                  results, args.dry_run, patterns)
        print(f"  Log:   {log_path}")

    if not args.dry_run and not args.no_log:
        print(f"\n  Written: {output_path}")

    if total_quotes == 0:
        print("\n  Note: No quotes matching citation patterns were found.")
        print("  Check that the correct --preset or --pattern is specified.")


if __name__ == '__main__':
    main()
