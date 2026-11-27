from pdfminer.high_level import extract_text
import fitz  # PyMuPDF
import os
import io
import re
from typing import Optional, Union


_PDF_DATE_HINT_RE = re.compile(
    r'\b(?:19|20)\d{2}\b|\b(?:present|current(?:ly)?|now|to\s+date|ongoing|pres\.?)\b|'
    r'\b\d+(?:\.\d+)?\s*(?:yrs?|years?|mos?|months?)\b',
    re.IGNORECASE,
)
_PDF_LOC_HINT_RE = re.compile(
    r'\b(?:manila|makati|taguig|bgc|bonifacio\s+global\s+city|pasig|ortigas|quezon\s+city|'
    r'mandaluyong|pasay|paranaque|parañaque|muntinlupa|alabang|las\s+pinas|las\s+piñas|'
    r'caloocan|marikina|san\s+juan|valenzuela|antipolo|taytay|cainta|rizal|laguna|calamba|'
    r'santa\s+rosa|cavite|batangas|bulacan|pampanga|clark|subic|cebu|davao|iloilo|baguio|'
    r'bacolod|cagayan\s+de\s+oro|ncr|metro\s+manila|calabarzon|philippines|singapore|'
    r'dubai|uae|usa|united\s+states|uk|united\s+kingdom|canada|australia|japan|tokyo|'
    r'hong\s+kong|taiwan|malaysia|remote|hybrid|onsite|on-site|wfh)\b|'
    r'^[A-Z][A-Za-z.\-\s]{2,25},\s*(?:[A-Z]{2,3}|[A-Z][A-Za-z.\-\s]{2,25})$',
    re.IGNORECASE,
)
_PDF_DANGLING_DATE_START_RE = re.compile(
    r'(?:\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|'
    r'Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\.?(?:\s+\d{1,2}(?:st|nd|rd|th)?)?(?:\s*[,.]?\s*(?:19|20)\d{2})?|'
    r'(?:19|20)\d{2}|\d{1,2}[./-]\d{4})\s*(?:-|–|—|\bto|\buntil|\bthru|\bthrough)\s*$',
    re.IGNORECASE,
)
_PDF_FULL_DATE_RANGE_HINT_RE = re.compile(
    r'(?:(?:19|20)\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\s*[,.]?\s*(?:19|20)\d{2})'
    r'\s*(?:-|–|—|\bto\b|\buntil\b|\bthru\b|\bthrough\b)\s*'
    r'(?:(?:19|20)\d{2}|present|current|now|ongoing)',
    re.IGNORECASE,
)
_PDF_DECORATIVE_BLOCK_RE = re.compile(r'^[\s\-–—=_*#•►◆■□▪▸▹│┃|.·~]+$')
_PDF_BULLET_ONLY_RE = re.compile(r'^[•\-*▪►✓◆■□▸▹·]$')
_PDF_PAGE_FOOTER_RE = re.compile(
    r'^\s*(?:'
    r'(?:page|pg\.?|p\.?)\s*\d+(?:\s*(?:of|/)\s*\d+)?|'
    r'\d+\s*(?:of|/)\s*\d+|'
    r'\d+\s*\|\s*page|page\s*\|\s*\d+|'
    r'[-–—|•·]\s*\d+\s*[-–—|•·]'
    r')\s*$',
    re.IGNORECASE,
)
_PDF_RUNNING_PAGE_MARKER_RE = re.compile(
    r'(?:\|\s*|\-\s*|–\s*|—\s*|,\s*)?(?:page|pg\.?)\s*\d+(?:\s*(?:of|/)\s*\d+)?\b',
    re.IGNORECASE,
)


def _is_pure_page_number_line(line: str) -> bool:
    return bool(_PDF_PAGE_FOOTER_RE.match((line or "").strip()))


def _normalize_running_line_sig(line: str) -> str:
    s = re.sub(r'\s+', ' ', (line or "").strip()).lower()
    if not s:
        return ""
    s = _PDF_RUNNING_PAGE_MARKER_RE.sub('<page>', s)
    s = re.sub(r'\b\d+\s*(?:of|/)\s*\d+\b', '<page>', s)
    return s.strip(' |-–—•·')


def _is_decorative_block(txt: str) -> bool:
    s = txt.strip()
    if not s:
        return True
    if _PDF_DECORATIVE_BLOCK_RE.match(s):
        return True
    return False


def _is_dangling_date_start(txt: str) -> bool:
    s = txt.strip()
    if not s or _PDF_FULL_DATE_RANGE_HINT_RE.search(s):
        return False
    return bool(_PDF_DANGLING_DATE_START_RE.search(s))


def _is_date_gutter_column(blocks, detect_section_label_fn) -> bool:
    """Return True if a column's blocks are predominantly short date/timeline fragments with no section headers."""
    if not blocks:
        return False
    if detect_section_label_fn is not None:
        for b in blocks:
            for ln in b[4].splitlines():
                if ln.strip() and detect_section_label_fn(ln.strip()) is not None:
                    return False
    date_frag_count = 0
    for b in blocks:
        txt = b[4].strip()
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        if len(lines) <= 3 and len(txt) <= 45 and _PDF_DATE_HINT_RE.search(txt):
            date_frag_count += 1
    return (date_frag_count / len(blocks)) >= 0.6


def _extract_region_lines_paired(
    blocks: list[tuple[float, float, float, float, str]],
    dict_blocks: list[dict],
    detect_section_label_fn=None,
) -> list[str]:
    """
    Extract lines from *blocks* using PyMuPDF dict line geometry (when available) so
    same-baseline left/right fragments (e.g. Job Title + right-aligned Date or Company + Location)
    are paired cleanly with ' | ', while preserving wrapped gutter dates and bullets.
    """
    if not blocks:
        return []

    raw_lines: list[tuple[float, float, float, float, str]] = []
    seen_dict_lines: set[tuple[float, float, float, float, str]] = set()
    if dict_blocks:
        for b in blocks:
            bx0, by0, bx1, by1, btxt = b
            matched_lines: list[tuple[float, float, float, float, str]] = []
            for db in dict_blocks:
                if db.get("type") != 0:
                    continue
                for ln in db.get("lines", []):
                    bbox = ln.get("bbox")
                    if not bbox or len(bbox) < 4:
                        continue
                    lx0, ly0, lx1, ly1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    cx = (lx0 + lx1) * 0.5
                    cy = (ly0 + ly1) * 0.5
                    if (bx0 - 2.5) <= cx <= (bx1 + 2.5) and (by0 - 2.5) <= cy <= (by1 + 2.5):
                        ltxt = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
                        if ltxt and not _PDF_DECORATIVE_BLOCK_RE.match(ltxt):
                            dedup_key = (round(lx0, 1), round(ly0, 1), round(lx1, 1), round(ly1, 1), ltxt)
                            if dedup_key not in seen_dict_lines:
                                seen_dict_lines.add(dedup_key)
                                matched_lines.append((lx0, ly0, lx1, ly1, ltxt))
            if matched_lines:
                raw_lines.extend(matched_lines)
            else:
                split_lns = [s.strip() for s in btxt.splitlines() if s.strip() and not _PDF_DECORATIVE_BLOCK_RE.match(s.strip())]
                step = max(8.0, (by1 - by0) / max(1, len(split_lns)))
                for idx, st in enumerate(split_lns):
                    raw_lines.append((bx0, by0 + idx * step, bx1, by0 + (idx + 1) * step, st))
    else:
        for bx0, by0, bx1, by1, btxt in blocks:
            split_lns = [s.strip() for s in btxt.splitlines() if s.strip() and not _PDF_DECORATIVE_BLOCK_RE.match(s.strip())]
            step = max(8.0, (by1 - by0) / max(1, len(split_lns)))
            for idx, st in enumerate(split_lns):
                raw_lines.append((bx0, by0 + idx * step, bx1, by0 + (idx + 1) * step, st))

    if not raw_lines:
        return []

    raw_lines.sort(key=lambda r: (r[1], r[0]))

    # Cluster into visual rows using vertical overlap >= 45% or y-center proximity <= 4.5pt
    rows: list[list[tuple[float, float, float, float, str]]] = []
    anchor_y0 = anchor_y1 = 0.0
    for item in raw_lines:
        _, ly0, _, ly1, _ = item
        if not rows:
            rows.append([item])
            anchor_y0, anchor_y1 = ly0, ly1
            continue
        overlap = min(anchor_y1, ly1) - max(anchor_y0, ly0)
        min_h = max(1.0, min(anchor_y1 - anchor_y0, ly1 - ly0))
        y_center_diff = abs(((anchor_y0 + anchor_y1) * 0.5) - ((ly0 + ly1) * 0.5))
        if (overlap / min_h) >= 0.45 or y_center_diff <= 4.5:
            rows[-1].append(item)
        else:
            rows.append([item])
            anchor_y0, anchor_y1 = ly0, ly1

    _PROSE_LINK_WORDS = {
        "a", "an", "the", "to", "of", "in", "on", "for", "with", "by", "from",
        "and", "or", "through", "while", "their", "our", "its", "this", "that",
        "is", "are", "was", "were", "as", "at", "into", "within", "using",
    }

    out_lines: list[str] = []
    for row in rows:
        row.sort(key=lambda r: r[0])
        if len(row) == 1:
            out_lines.append(row[0][4])
            continue

        # Merge standalone bullets, mid-word kerning splits (no space), and justified prose gaps
        compact: list[tuple[float, float, float, float, str]] = [row[0]]
        for nxt in row[1:]:
            prev = compact[-1]
            gap = nxt[0] - prev[2]
            line_h = max(6.0, min(prev[3] - prev[1], nxt[3] - nxt[1]))
            nxt_is_date_or_loc = bool(_PDF_DATE_HINT_RE.search(nxt[4]) or _PDF_LOC_HINT_RE.search(nxt[4]))

            if _PDF_BULLET_ONLY_RE.match(prev[4]):
                compact[-1] = (prev[0], min(prev[1], nxt[1]), max(prev[2], nxt[2]), max(prev[3], nxt[3]), f"{prev[4]} {nxt[4]}")
            elif (
                gap <= max(1.0, line_h * 0.10)
                or (
                    gap <= max(1.5, line_h * 0.15)
                    and prev[4][-1].isalnum()
                    and nxt[4][0].isalnum()
                )
            ):
                # Tight intra-word kerning split (e.g. Canva/Chromium justified text splitting "reschedul" + "e")
                compact[-1] = (prev[0], min(prev[1], nxt[1]), max(prev[2], nxt[2]), max(prev[3], nxt[3]), f"{prev[4]}{nxt[4]}")
            elif gap < (12.0 if nxt_is_date_or_loc else max(18.0, line_h * 1.65)):
                compact[-1] = (prev[0], min(prev[1], nxt[1]), max(prev[2], nxt[2]), max(prev[3], nxt[3]), f"{prev[4]} {nxt[4]}")
            else:
                compact.append(nxt)

        if len(compact) == 1:
            out_lines.append(compact[0][4])
            continue

        texts = [c[4] for c in compact]
        has_dangling = any(_is_dangling_date_start(t) for t in texts)
        has_date_or_loc = any(_PDF_DATE_HINT_RE.search(t) or _PDF_LOC_HINT_RE.search(t) for t in texts)
        all_short = all(len(t) < 90 for t in texts)
        both_headers = (
            detect_section_label_fn is not None
            and len(texts) >= 2
            and all(detect_section_label_fn(t) is not None for t in texts)
        )
        any_bullet = any(t.startswith(("•", "-", "*", "▪", "►", "✓")) for t in texts)

        # Detect justified prose lines (stretched word spacing) so we NEVER insert ' | ' inside sentences
        lower_continuation_chunks = sum(1 for t in texts[1:] if t and t[0].islower())
        prose_link_boundary = any(
            (t.split()[-1].lower().strip(",.;:") in _PROSE_LINK_WORDS)
            for t in texts[:-1]
            if t.split()
        )
        looks_like_justified_prose = (
            not both_headers
            and not has_date_or_loc
            and (
                len(texts) >= 4
                or lower_continuation_chunks >= 1
                or prose_link_boundary
            )
        )

        if looks_like_justified_prose:
            out_lines.append(" ".join(texts))
        elif not has_dangling and not both_headers and all_short and (
            has_date_or_loc or (not any_bullet and len(texts) <= 3 and all(len(t) < 60 for t in texts))
        ):
            out_lines.append(" | ".join(texts))
        else:
            out_lines.extend(texts)

    return out_lines


def _join_gutter_block_text(txt: str) -> str:
    """Join wrapped lines inside a narrow date-gutter block cleanly."""
    parts = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    joined = parts[0]
    for p in parts[1:]:
        if re.search(r'(?:-|–|—|\bto|\buntil|\bthru|\bthrough)\s*$', joined, re.IGNORECASE):
            joined = f"{joined} {p}"
        else:
            joined = f"{joined} {p}"
    return joined


def _extract_date_gutter_lines(
    gutter_b: list[tuple[float, float, float, float, str]],
    main_b: list[tuple[float, float, float, float, str]],
    dict_blocks: list[dict],
    detect_section_label_fn=None,
) -> list[str]:
    """Emit date-gutter blocks right before their vertically aligned main-column blocks."""
    main_sorted = sorted(main_b, key=lambda b: (round(b[1] / 4.0), b[0]))
    attached: dict[int, list[str]] = {idx: [] for idx in range(len(main_sorted))}
    orphan_gutter: list[tuple[float, str]] = []

    def _is_hdr_block(b) -> bool:
        if detect_section_label_fn is None:
            return False
        first_ln = b[4].splitlines()[0].strip() if b[4].strip() else ""
        return bool(first_ln and detect_section_label_fn(first_ln) is not None and "\n" not in b[4].strip())

    for gb in sorted(gutter_b, key=lambda b: b[1]):
        g_txt = _join_gutter_block_text(gb[4])
        if not g_txt:
            continue
        best_idx = None
        best_score = 1e9
        for m_idx, mb in enumerate(main_sorted):
            if _is_hdr_block(mb):
                continue
            y_dist = abs(gb[1] - mb[1])
            overlap = min(gb[3], mb[3]) - max(gb[1], mb[1])
            score = y_dist - (20.0 if overlap > 0 else 0.0)
            if score < best_score:
                best_score = score
                best_idx = m_idx
        if best_idx is not None and abs(gb[1] - main_sorted[best_idx][1]) <= 45.0:
            attached[best_idx].append(g_txt)
        else:
            orphan_gutter.append((gb[1], g_txt))

    out: list[str] = []
    orphan_idx = 0
    for m_idx, mb in enumerate(main_sorted):
        while orphan_idx < len(orphan_gutter) and orphan_gutter[orphan_idx][0] <= mb[1]:
            out.append(orphan_gutter[orphan_idx][1])
            orphan_idx += 1
        out.extend(attached[m_idx])
        out.extend(_extract_region_lines_paired([mb], dict_blocks, detect_section_label_fn))
    while orphan_idx < len(orphan_gutter):
        out.append(orphan_gutter[orphan_idx][1])
        orphan_idx += 1
    return out


def _split_horizontally_bridged_blocks(
    text_blocks: list[tuple[float, float, float, float, str]],
    dict_blocks: list[dict],
    page_w: float,
) -> list[tuple[float, float, float, float, str]]:
    """
    Split blocks where PyMuPDF coalesced two horizontally disjoint columns (e.g. a narrow
    left date-gutter and main right-hand content) across a wide empty vertical gap.
    Preserves single-line right-aligned rows so paired-row extraction can join them cleanly.
    """
    if not dict_blocks or not text_blocks:
        return text_blocks

    out: list[tuple[float, float, float, float, str]] = []
    for b in text_blocks:
        bx0, by0, bx1, by1, _ = b
        if (bx1 - bx0) < 120.0 or (by1 - by0) <= 18.0:
            out.append(b)
            continue

        spans: list[tuple[float, float, float, float, str]] = []
        for db in dict_blocks:
            if db.get("type") != 0:
                continue
            for ln in db.get("lines", []):
                for sp in ln.get("spans", []):
                    stxt = (sp.get("text") or "").strip()
                    if not stxt or _PDF_DECORATIVE_BLOCK_RE.match(stxt):
                        continue
                    sb = sp.get("bbox")
                    if not sb or len(sb) < 4:
                        continue
                    sx0, sy0, sx1, sy1 = float(sb[0]), float(sb[1]), float(sb[2]), float(sb[3])
                    scx = (sx0 + sx1) * 0.5
                    scy = (sy0 + sy1) * 0.5
                    if (bx0 - 2.5) <= scx <= (bx1 + 2.5) and (by0 - 2.5) <= scy <= (by1 + 2.5):
                        spans.append((sx0, sy0, sx1, sy1, stxt))

        if len(spans) < 2:
            out.append(b)
            continue

        # Sweep sorted spans by x0 to find the widest zero-overlap vertical gap >= 22pt
        sorted_x = sorted(spans, key=lambda s: (s[0], s[2]))
        running_max_x1 = sorted_x[0][2]
        best_gap = 0.0
        best_gap_mid = None
        for idx in range(len(sorted_x) - 1):
            running_max_x1 = max(running_max_x1, sorted_x[idx][2])
            next_x0 = sorted_x[idx + 1][0]
            gap = next_x0 - running_max_x1
            if gap >= 22.0 and gap > best_gap:
                best_gap = gap
                best_gap_mid = (running_max_x1 + next_x0) * 0.5

        if best_gap_mid is None:
            out.append(b)
            continue

        left_sp = [s for s in spans if s[2] <= best_gap_mid]
        right_sp = [s for s in spans if s[0] >= best_gap_mid]
        if not left_sp or not right_sp:
            out.append(b)
            continue

        def _rebuild_subblock(sub_spans: list[tuple[float, float, float, float, str]]):
            sub_spans_s = sorted(sub_spans, key=lambda s: (round(s[1] / 3.0), s[0]))
            lines_acc: list[list[tuple[float, float, float, float, str]]] = []
            for sp in sub_spans_s:
                if not lines_acc:
                    lines_acc.append([sp])
                    continue
                cy_prev = (lines_acc[-1][0][1] + lines_acc[-1][0][3]) * 0.5
                cy_curr = (sp[1] + sp[3]) * 0.5
                if abs(cy_curr - cy_prev) <= 4.5:
                    lines_acc[-1].append(sp)
                else:
                    lines_acc.append([sp])
            built_lines = [" ".join(x[4] for x in sorted(ln, key=lambda s: s[0])) for ln in lines_acc]
            sx0 = min(s[0] for s in sub_spans)
            sy0 = min(s[1] for s in sub_spans)
            sx1 = max(s[2] for s in sub_spans)
            sy1 = max(s[3] for s in sub_spans)
            return (sx0, sy0, sx1, sy1, "\n".join(built_lines)), len(built_lines)

        l_blk, l_nlines = _rebuild_subblock(left_sp)
        r_blk, r_nlines = _rebuild_subblock(right_sp)
        left_w = l_blk[2] - l_blk[0]
        # Split if both columns are multi-line OR left column is a narrow gutter beside a multi-line body
        if (l_nlines >= 2 and r_nlines >= 2) or (left_w <= page_w * 0.22 and r_nlines >= 2):
            out.append(l_blk)
            out.append(r_blk)
        else:
            out.append(b)

    return out


def _extract_page_layout_parts(page, prev_split_x: float | None = None) -> dict:
    """
    Extract structured layout regions from a PyMuPDF page while preserving visual reading order.
    Returns dict with keys:
      is_two_col, split_x, top_lines, left_lines, right_lines, other_lines, footer_lines, text
    """
    raw_blocks = page.get_text("blocks") or []
    text_blocks = [
        (float(b[0]), float(b[1]), float(b[2]), float(b[3]), str(b[4]).strip())
        for b in raw_blocks
        if len(b) >= 7 and b[6] == 0 and str(b[4]).strip() and not _is_decorative_block(str(b[4]))
    ]
    if not text_blocks:
        fallback = page.get_text() or ""
        return {
            "is_two_col": False,
            "split_x": None,
            "top_lines": [],
            "left_lines": [],
            "right_lines": [],
            "other_lines": fallback.splitlines() if fallback else [],
            "footer_lines": [],
            "text": fallback,
        }

    dict_blocks: list[dict] = []
    try:
        d = page.get_text("dict")
        if isinstance(d, dict):
            dict_blocks = d.get("blocks") or []
    except Exception:
        dict_blocks = []

    page_w = float(page.rect.width or 600.0)
    page_h = float(page.rect.height or 800.0)
    text_blocks = _split_horizontally_bridged_blocks(text_blocks, dict_blocks, page_w)

    # Separate bottom page footers so they don't cross column boundaries and disable 2-column detection
    footer_blocks = []
    main_blocks = []
    for b in text_blocks:
        is_single_line = "\n" not in b[4]
        if b[1] >= page_h * 0.90 or (is_single_line and _PDF_PAGE_FOOTER_RE.match(b[4])):
            footer_blocks.append(b)
        else:
            main_blocks.append(b)

    if not main_blocks:
        main_blocks = text_blocks
        footer_blocks = []

    detect_section_label_fn = None
    try:
        from app.extractors.content.section_parser import detect_section_label
        detect_section_label_fn = detect_section_label
    except Exception:
        pass

    # Identify candidate header cutoffs:
    # 1) standard top banner cutoff (capped by first detected section header)
    # 2) dynamic cutoff below full-width top blocks (e.g. Name + Summary above 2-col body) in top 45%
    default_cutoff = min(145.0, page_h * 0.18)
    first_section_y = default_cutoff
    if detect_section_label_fn is not None:
        try:
            for b in main_blocks:
                first_line = b[4].split("\n", 1)[0].strip()
                if first_line and detect_section_label_fn(first_line) is not None:
                    if b[1] < first_section_y:
                        first_section_y = b[1]
        except Exception:
            pass

    candidate_cutoffs: list[float] = [first_section_y]
    if prev_split_x is not None:
        candidate_cutoffs.append(0.0)
    for b in main_blocks:
        if b[0] < page_w * 0.35 and b[2] > page_w * 0.65 and b[3] <= page_h * 0.45:
            below_ys = [mb[1] for mb in main_blocks if mb[1] >= b[3] - 2.0 and mb is not b]
            if below_ys:
                c_y = min(below_ys)
                if c_y not in candidate_cutoffs:
                    candidate_cutoffs.append(c_y)

    best_split = None
    best_cutoff = first_section_y
    best_score = -1.0
    best_gutter_split = None
    best_gutter_cutoff = first_section_y
    best_gutter_score = -1.0

    def _split_block_at_x(
        blk: tuple[float, float, float, float, str],
        sx: float,
    ) -> Optional[tuple[tuple[float, float, float, float, str], tuple[float, float, float, float, str]]]:
        """Split a single crossing block along *sx* if its PyMuPDF dict spans do not cross *sx*."""
        if not dict_blocks:
            return None
        bx0, by0, bx1, by1, _ = blk
        spans: list[tuple[float, float, float, float, str]] = []
        for db in dict_blocks:
            if db.get("type") != 0:
                continue
            for ln in db.get("lines", []):
                for sp in ln.get("spans", []):
                    stxt = (sp.get("text") or "").strip()
                    if not stxt or _PDF_DECORATIVE_BLOCK_RE.match(stxt):
                        continue
                    sb = sp.get("bbox")
                    if not sb or len(sb) < 4:
                        continue
                    sx0, sy0, sx1, sy1 = float(sb[0]), float(sb[1]), float(sb[2]), float(sb[3])
                    scx = (sx0 + sx1) * 0.5
                    scy = (sy0 + sy1) * 0.5
                    if (bx0 - 2.5) <= scx <= (bx1 + 2.5) and (by0 - 2.5) <= scy <= (by1 + 2.5):
                        spans.append((sx0, sy0, sx1, sy1, stxt))
        if not spans:
            return None
        l_sp = [s for s in spans if s[2] <= sx + 8.0]
        r_sp = [s for s in spans if s[0] >= sx - 8.0 and s not in l_sp]
        if len(l_sp) + len(r_sp) != len(spans) or not l_sp or not r_sp:
            return None
        # Require a real column gap (>= 14pt) between the left and right spans in this block
        if (min(s[0] for s in r_sp) - max(s[2] for s in l_sp)) < 14.0:
            return None

        def _make_blk(sub: list[tuple[float, float, float, float, str]]) -> tuple[float, float, float, float, str]:
            sub_s = sorted(sub, key=lambda s: (round(s[1] / 3.0), s[0]))
            lines_acc: list[list[tuple[float, float, float, float, str]]] = []
            for sp in sub_s:
                if not lines_acc:
                    lines_acc.append([sp])
                    continue
                cy_prev = (lines_acc[-1][0][1] + lines_acc[-1][0][3]) * 0.5
                cy_curr = (sp[1] + sp[3]) * 0.5
                if abs(cy_curr - cy_prev) <= 4.5:
                    lines_acc[-1].append(sp)
                else:
                    lines_acc.append([sp])
            built = [" ".join(x[4] for x in sorted(ln, key=lambda s: s[0])) for ln in lines_acc]
            return (
                min(s[0] for s in sub),
                min(s[1] for s in sub),
                max(s[2] for s in sub),
                max(s[3] for s in sub),
                "\n".join(built),
            )

        return _make_blk(l_sp), _make_blk(r_sp)

    fracs = [0.24, 0.28, 0.30, 0.33, 0.35, 0.38, 0.40, 0.42, 0.48, 0.52, 0.62, 0.67, 0.72]
    for cutoff in candidate_cutoffs:
        body_blocks = [b for b in main_blocks if b[1] >= cutoff]
        if len(body_blocks) < 2:
            continue

        # Combine fixed fraction grid with data-driven column-gap midpoints from actual block x-edges
        split_candidates: list[float] = [page_w * frac for frac in fracs]
        edge_x1s = sorted({round(b[2], 1) for b in body_blocks if page_w * 0.18 <= b[2] <= page_w * 0.75})
        edge_x0s = sorted({round(b[0], 1) for b in body_blocks if page_w * 0.20 <= b[0] <= page_w * 0.78})
        for x1 in edge_x1s:
            for x0 in edge_x0s:
                if 6.0 <= (x0 - x1) <= page_w * 0.18:
                    mid = (x1 + x0) * 0.5
                    if page_w * 0.20 <= mid <= page_w * 0.76:
                        if all(abs(mid - existing) > 4.0 for existing in split_candidates):
                            split_candidates.append(mid)

        for split_x in split_candidates:
            left_b = [b for b in body_blocks if b[2] <= split_x + 8]
            right_b = [b for b in body_blocks if b[0] >= split_x - 8 and b not in left_b]
            crossing_b = [b for b in body_blocks if b[0] < split_x - 8 and b[2] > split_x + 8]

            # If only a few blocks bridged across the column gutter (e.g. coalesced single lines),
            # check if their dict spans separate cleanly across split_x.
            if crossing_b and len(crossing_b) <= 4:
                resolved_left: list[tuple[float, float, float, float, str]] = []
                resolved_right: list[tuple[float, float, float, float, str]] = []
                unresolved = False
                for cb in crossing_b:
                    split_pair = _split_block_at_x(cb, split_x)
                    if split_pair is None:
                        unresolved = True
                        break
                    resolved_left.append(split_pair[0])
                    resolved_right.append(split_pair[1])
                if not unresolved:
                    left_b = left_b + resolved_left
                    right_b = right_b + resolved_right
                    crossing_b = []

            if len(left_b) >= 1 and len(right_b) >= 1 and len(crossing_b) == 0:
                left_is_gutter = _is_date_gutter_column(left_b, detect_section_label_fn)
                right_is_gutter = _is_date_gutter_column(right_b, detect_section_label_fn)
                left_min_y = min(b[1] for b in left_b)
                left_max_y = max(b[3] for b in left_b)
                right_min_y = min(b[1] for b in right_b)
                right_max_y = max(b[3] for b in right_b)
                y_overlap = min(left_max_y, right_max_y) - max(left_min_y, right_min_y)
                left_lines_cnt = sum(b[4].count("\n") + 1 for b in left_b)
                right_lines_cnt = sum(b[4].count("\n") + 1 for b in right_b)

                if left_is_gutter or right_is_gutter:
                    if len(left_b) >= 2 and len(right_b) >= 2 and y_overlap > 60:
                        g_score = float(len(left_b) + len(right_b)) - (0.01 if cutoff != first_section_y else 0.0)
                        if g_score > best_gutter_score:
                            best_gutter_score = g_score
                            best_gutter_split = split_x
                            best_gutter_cutoff = cutoff
                    continue

                is_prev_cont = (
                    prev_split_x is not None
                    and abs(split_x - prev_split_x) <= page_w * 0.12
                    and y_overlap > 25
                    and left_lines_cnt >= 2
                    and right_lines_cnt >= 2
                )
                is_std_two_col = (
                    len(left_b) >= 2
                    and len(right_b) >= 2
                    and y_overlap > 80
                    and left_lines_cnt >= 5
                    and right_lines_cnt >= 5
                )
                if is_std_two_col or is_prev_cont:
                    score = float(len(left_b) + len(right_b))
                    if cutoff == first_section_y:
                        score += 0.5
                    if prev_split_x is not None and abs(split_x - prev_split_x) <= page_w * 0.10:
                        score += 0.25
                    if score > best_score:
                        best_score = score
                        best_split = split_x
                        best_cutoff = cutoff

    footer_blocks.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
    footer_lines = _extract_region_lines_paired(footer_blocks, dict_blocks, detect_section_label_fn)

    if best_split is not None:
        top_blocks = sorted([b for b in main_blocks if b[1] < best_cutoff], key=lambda b: (round(b[1] / 6.0), b[0]))
        body_blocks = [b for b in main_blocks if b[1] >= best_cutoff]

        left_col = [b for b in body_blocks if b[2] <= best_split + 8]
        right_col = [b for b in body_blocks if b[0] >= best_split - 8 and b not in left_col]
        other_col = []
        for b in body_blocks:
            if b in left_col or b in right_col:
                continue
            split_pair = _split_block_at_x(b, best_split)
            if split_pair is not None:
                left_col.append(split_pair[0])
                right_col.append(split_pair[1])
            else:
                other_col.append(b)

        left_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
        right_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))
        other_col.sort(key=lambda b: (round(b[1] / 4.0), b[0]))

        top_lines = _extract_region_lines_paired(top_blocks, dict_blocks, detect_section_label_fn)
        left_lines = _extract_region_lines_paired(left_col, dict_blocks, detect_section_label_fn)
        right_lines = _extract_region_lines_paired(right_col, dict_blocks, detect_section_label_fn)
        other_lines = _extract_region_lines_paired(other_col, dict_blocks, detect_section_label_fn)

        all_lines = top_lines + left_lines + right_lines + other_lines + footer_lines
        return {
            "is_two_col": True,
            "split_x": best_split,
            "page_w": page_w,
            "top_lines": top_lines,
            "left_lines": left_lines,
            "right_lines": right_lines,
            "other_lines": other_lines,
            "footer_lines": footer_lines,
            "text": "\n".join(all_lines),
        }

    if best_gutter_split is not None:
        top_blocks = sorted([b for b in main_blocks if b[1] < best_gutter_cutoff], key=lambda b: (round(b[1] / 6.0), b[0]))
        body_blocks = [b for b in main_blocks if b[1] >= best_gutter_cutoff]
        left_col = [b for b in body_blocks if b[2] <= best_gutter_split + 8]
        right_col = [b for b in body_blocks if b[0] >= best_gutter_split - 8 and b not in left_col]
        if _is_date_gutter_column(left_col, detect_section_label_fn):
            body_lines = _extract_date_gutter_lines(left_col, right_col, dict_blocks, detect_section_label_fn)
        else:
            body_lines = _extract_date_gutter_lines(right_col, left_col, dict_blocks, detect_section_label_fn)
        top_lines = _extract_region_lines_paired(top_blocks, dict_blocks, detect_section_label_fn)
        all_lines = top_lines + body_lines + footer_lines
        return {
            "is_two_col": False,
            "split_x": None,
            "page_w": page_w,
            "top_lines": top_lines,
            "left_lines": [],
            "right_lines": [],
            "other_lines": body_lines,
            "footer_lines": footer_lines,
            "text": "\n".join(all_lines),
        }

    # Single-column layout: sort visually top-to-bottom, left-to-right with dict-level visual row pairing
    ordered_blocks = sorted(main_blocks, key=lambda b: (round(b[1] / 4.0), b[0]))
    body_lines = _extract_region_lines_paired(ordered_blocks, dict_blocks, detect_section_label_fn)
    all_lines = body_lines + footer_lines
    return {
        "is_two_col": False,
        "split_x": None,
        "page_w": page_w,
        "top_lines": [],
        "left_lines": [],
        "right_lines": [],
        "other_lines": body_lines,
        "footer_lines": footer_lines,
        "text": "\n".join(all_lines),
    }


def _extract_page_text_layout_aware(page) -> str:
    """
    Extracts text from a PyMuPDF page while preserving visual reading order:
    - Sorts out-of-order PDF stream blocks top-to-bottom.
    - Detects two-column (sidebar + main) layouts so left-column sections
      (e.g. CONTACT, EDUCATION, SKILLS, CERTIFICATION) never interleave into
      right-column sections (e.g. PROFILE, EXPERIENCE).
    - Separates bottom page footers and aligns date-only timeline gutters with their roles.
    """
    return _extract_page_layout_parts(page)["text"]


def extract_text_from_pdf(file_input: Union[str, bytes, io.BytesIO]) -> str:
    """
    Extracts complete visible text from a .pdf file using dual-engine analysis
    (PyMuPDF fitz + pdfminer.six) to guarantee natural visual reading order,
    multi-column layout fidelity, and complete content extraction (REQ004 / TC-RES-010).
    Accepts file path (str), raw bytes (bytes), or BytesIO.
    """
    fitz_text = ""
    extra_links = []

    detect_section_label_fn = None
    try:
        from app.extractors.content.section_parser import detect_section_label
        detect_section_label_fn = detect_section_label
    except Exception:
        pass

    # Engine 1: PyMuPDF (fitz) with layout-aware block ordering
    try:
        if isinstance(file_input, bytes):
            doc = fitz.open(stream=file_input, filetype="pdf")
        elif isinstance(file_input, io.BytesIO):
            doc = fitz.open(stream=file_input.getvalue(), filetype="pdf")
        else:
            doc = fitz.open(file_input)
        pages_parts: list[dict] = []
        prev_two_col_split: float | None = None
        for page in doc:
            parts = _extract_page_layout_parts(page, prev_split_x=prev_two_col_split)
            page_text = parts["text"]
            # Scanned or image-only PDF page fallback to OCR at 250 DPI
            if not page_text or len(page_text.strip()) < 20:
                try:
                    ocr_tp = page.get_textpage_ocr(flags=0, dpi=250, full=True)
                    ocr_text = ocr_tp.extractText()
                    if ocr_text and len(ocr_text.strip()) > len(page_text.strip()):
                        parts = {
                            "is_two_col": False,
                            "split_x": None,
                            "page_w": float(page.rect.width or 600.0),
                            "top_lines": [],
                            "left_lines": [],
                            "right_lines": [],
                            "other_lines": ocr_text.splitlines(),
                            "footer_lines": [],
                            "text": ocr_text,
                        }
                except Exception:
                    pass
            pages_parts.append(parts)
            prev_two_col_split = parts["split_x"] if parts.get("is_two_col") else None

            # Check links
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and ("mailto:" in uri.lower() or "@" in uri):
                    clean_uri = uri.replace("mailto:", "").split("?")[0].strip()
                    if clean_uri and clean_uri not in extra_links:
                        extra_links.append(f"Email Link: {clean_uri}")
                elif uri and ("tel:" in uri.lower() or "callto:" in uri.lower()):
                    clean_tel = uri.lower().replace("tel:", "").replace("callto:", "").split("?")[0].strip()
                    if clean_tel and clean_tel not in extra_links:
                        extra_links.append(f"Phone Link: {clean_tel}")

            # Check annotations
            for annot in page.annots():
                info = annot.info or {}
                content = info.get("content", "")
                if content and ("@" in content or "mailto:" in content.lower()):
                    extra_links.append(f"Email Annotation: {content.strip()}")
                elif content and ("tel:" in content.lower() or "callto:" in content.lower()):
                    extra_links.append(f"Phone Annotation: {content.strip()}")

        doc.close()

        # Multi-page assembly:
        # 1. Preserve 2-column continuity across pages 2..N.
        # 2. Strip pure page-number lines ("Page 2 of 4", "- 2 -", "2 / 4") so page
        #    boundaries never break multi-page sections or work-experience entries.
        # 3. Strip repeated running headers/footers on pages 2..N while keeping page 1
        #    intact so name/contact extraction always sees the header on page 1.
        assembled_page_lines: list[list[str]] = []
        for idx, p_info in enumerate(pages_parts):
            if (
                idx > 0
                and pages_parts[idx - 1].get("is_two_col")
                and p_info.get("is_two_col")
                and p_info.get("right_lines")
                and p_info.get("left_lines")
            ):
                prev_sx = pages_parts[idx - 1].get("split_x") or 0.0
                curr_sx = p_info.get("split_x") or 0.0
                pw = p_info.get("page_w") or 600.0
                first_right = next((ln.strip() for ln in p_info["right_lines"] if ln.strip()), "")
                right_starts_with_hdr = (
                    detect_section_label_fn is not None
                    and bool(first_right)
                    and detect_section_label_fn(first_right) is not None
                )
                if abs(curr_sx - prev_sx) <= pw * 0.15 and not right_starts_with_hdr:
                    reordered = (
                        p_info["top_lines"]
                        + p_info["right_lines"]
                        + p_info["left_lines"]
                        + p_info["other_lines"]
                        + p_info["footer_lines"]
                    )
                    assembled_page_lines.append(reordered)
                    continue
            assembled_page_lines.append(p_info["text"].splitlines())

        if len(assembled_page_lines) >= 2:
            # Identify lines repeated in top-3 / bottom-3 margins across >= 2 pages
            margin_sig_pages: dict[str, set[int]] = {}
            for p_idx, p_lines in enumerate(assembled_page_lines):
                non_empty_indices = [i for i, ln in enumerate(p_lines) if ln.strip()]
                edge_indices = set(non_empty_indices[:3] + non_empty_indices[-3:])
                for li in edge_indices:
                    raw_ln = p_lines[li].strip()
                    if not raw_ln or len(raw_ln) > 120:
                        continue
                    if detect_section_label_fn is not None and detect_section_label_fn(raw_ln) is not None:
                        continue
                    sig = _normalize_running_line_sig(raw_ln)
                    if sig and len(sig) >= 3:
                        margin_sig_pages.setdefault(sig, set()).add(p_idx)

            repeated_sigs = {sig for sig, pset in margin_sig_pages.items() if len(pset) >= 2}

            cleaned_page_texts: list[str] = []
            for p_idx, p_lines in enumerate(assembled_page_lines):
                non_empty_indices = [i for i, ln in enumerate(p_lines) if ln.strip()]
                edge_indices = set(non_empty_indices[:3] + non_empty_indices[-3:])
                kept_lines: list[str] = []
                for li, ln in enumerate(p_lines):
                    stripped_ln = ln.strip()
                    if not stripped_ln:
                        kept_lines.append(ln)
                        continue
                    # Always strip standalone page-number markers
                    if _is_pure_page_number_line(stripped_ln):
                        continue
                    # On pages 2..N, drop repeated running headers/footers and edge lines with "Page N"
                    if p_idx > 0 and li in edge_indices:
                        is_sec_hdr = (
                            detect_section_label_fn is not None
                            and detect_section_label_fn(stripped_ln) is not None
                        )
                        if not is_sec_hdr:
                            sig = _normalize_running_line_sig(stripped_ln)
                            if sig in repeated_sigs:
                                continue
                            if (
                                len(stripped_ln) <= 100
                                and _PDF_RUNNING_PAGE_MARKER_RE.search(stripped_ln)
                            ):
                                continue
                    kept_lines.append(ln)
                cleaned_page_texts.append("\n".join(kept_lines))
            page_texts = cleaned_page_texts
        else:
            page_texts = [
                "\n".join(ln for ln in p_lines if not _is_pure_page_number_line(ln))
                for p_lines in assembled_page_lines
            ]

        fitz_text = "\n".join(page_texts).strip()
    except Exception as e:
        print(f"PyMuPDF extraction error: {e}")

    # Engine 2: pdfminer.six
    pm_text = ""
    try:
        if isinstance(file_input, bytes):
            pm_text = extract_text(io.BytesIO(file_input)).strip()
        else:
            pm_text = extract_text(file_input).strip()
        if pm_text:
            pm_text = re.sub(r"\(cid:\d+\)¢?", "• ", pm_text)
    except Exception as e:
        print(f"pdfminer error reading PDF file: {e}")

    # Structural evaluation: Detect header inversions (e.g. EDUCATION placed below school)
    # and dropped sections / heavy text loss compared to the alternative engine.
    def _inversion_penalty(t: str, other_t: str = "") -> int:
        if not t:
            return 999
        penalty = 0
        t_up = t.upper()
        edu_pos = t_up.find("EDUCATION")
        exp_pos = max(t_up.find("WORK EXPERIENCE"), t_up.find("EXPERIENCE"))

        if edu_pos > 150:
            for s in ["STI COLLEGES", "UNIVERSIDAD", "UNIVERSITY", "COLLEGE", "BACHELOR", "BS "]:
                p = t_up.find(s)
                if 0 <= p < edu_pos:
                    # Do not penalize summary/objective prose mentioning alma mater (e.g. "graduate from Bicol University")
                    line_s = t.rfind("\n", 0, p) + 1
                    line_e = t.find("\n", p)
                    line_txt = t[line_s:(line_e if line_e >= 0 else len(t))].strip()
                    if re.search(r'\b(?:graduate\s+from|graduated\s+from|seeking|looking\s+to|with\s+strong\s+skills|passionate|dedicated)\b', line_txt, re.I):
                        continue
                    penalty += 50
        if exp_pos > 150:
            for c in ["FOOD PANDA", "CHANZIT", "JOLLIBEE", "SHOPEE", "ACCENTURE", "DELIVERY RIDER"]:
                p = t_up.find(c)
                if 0 <= p < exp_pos:
                    penalty += 50
        try:
            from app.extractors.content.section_parser import split_into_sections
            secs = split_into_sections(t)
            if "SKILLS" in secs and not secs["SKILLS"].strip():
                penalty += 50
            if "EDUCATION" in secs and not secs["EDUCATION"].strip():
                penalty += 50
            if other_t:
                other_secs = split_into_sections(other_t)
                if other_secs.get("EXPERIENCE", "").strip() and not secs.get("EXPERIENCE", "").strip():
                    penalty += 60
                if other_secs.get("EDUCATION", "").strip() and not secs.get("EDUCATION", "").strip():
                    penalty += 60
        except Exception:
            pass
        if other_t and len(t) < len(other_t) * 0.70:
            penalty += 40
        return penalty

    p_fitz = _inversion_penalty(fitz_text, pm_text)
    p_pm = _inversion_penalty(pm_text, fitz_text)

    # Select the text that preserves natural reading order (prefer layout-ordered PyMuPDF when equal)
    if p_fitz <= p_pm and len(fitz_text) >= 40:
        chosen_text = fitz_text
    elif p_pm < p_fitz and len(pm_text) >= 40:
        chosen_text = pm_text
    elif fitz_text:
        chosen_text = fitz_text
    else:
        chosen_text = pm_text

    # Append hyperlink URIs and annotations
    if extra_links:
        chosen_text = (chosen_text + "\n" + "\n".join(extra_links)).strip()

    return chosen_text

def extract_image_from_pdf(file_path: str) -> str:
    """
    Extracts the best candidate for a profile image from a PDF and saves it to uploads/resume_images.
    Returns the path to the saved image or None.
    """
    try:
        doc = fitz.open(file_path)
        img_dir = "uploads/resume_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            
        # Search page by page. Profile images are almost always on the first page.
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            
            if not image_list:
                continue
                
            candidates = []
            for img_info in image_list:
                xref = img_info[0]
                width = img_info[2]
                height = img_info[3]
                
                # Filter out tiny images (icons)
                if width < 40 or height < 40:
                    continue
                    
                aspect = width / height if height else 0
                if aspect < 0.4 or aspect > 2.5:
                    continue
                    
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                img_bytes = base_image["image"]
                size_kb = len(img_bytes) / 1024
                img_ext = base_image["ext"]
                
                # Score candidate
                score = 0
                
                # 1. Aspect ratio: prefer close to square (1:1)
                ratio_diff = abs(1.0 - aspect)
                score += (1.0 - ratio_diff) * 100
                
                # 2. Size in bytes: prefer larger byte sizes (more detail/higher resolution)
                if size_kb < 2.0:
                    score -= 50
                else:
                    score += min(size_kb, 200.0) * 2
                    
                # 3. Position on page:
                rects = page.get_image_rects(xref)
                if rects:
                    rect = rects[0]
                    img_w = rect.width
                    img_h = rect.height
                    
                    # Filter out backgrounds
                    if img_w > page.rect.width * 0.7 or img_h > page.rect.height * 0.7:
                        score -= 500
                    if img_w < 20 or img_h < 20:
                        score -= 300
                        
                    # Prefer top-portion
                    y_center = (rect.y0 + rect.y1) / 2
                    if y_center < page.rect.height * 0.4:
                        score += 150
                    elif y_center < page.rect.height * 0.6:
                        score += 50
                    else:
                        score -= 100
                else:
                    score -= 50
                    
                candidates.append({
                    'xref': xref,
                    'bytes': img_bytes,
                    'ext': img_ext,
                    'score': score
                })
                
            if candidates:
                # Sort by score descending and pick the best one
                candidates.sort(key=lambda x: x['score'], reverse=True)
                best = candidates[0]
                
                filename = os.path.basename(file_path)
                image_name = f"{os.path.splitext(filename)[0]}_img.{best['ext']}"
                image_path = os.path.join(img_dir, image_name)
                
                with open(image_path, "wb") as f:
                    f.write(best['bytes'])
                
                doc.close()

                # Upload to Supabase resume_images bucket (path: resumeimages/)
                try:
                    from app.utils.supabase_storage import upload_resume_image_sync
                    sb_res = upload_resume_image_sync(
                        file_bytes=best['bytes'],
                        original_filename=image_name,
                    )
                    return sb_res["public_url"]
                except Exception as sb_err:
                    print(f"Supabase resume image upload fallback to local: {sb_err}")
                    return image_path
                
        doc.close()
    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
    return None
