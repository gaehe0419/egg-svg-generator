#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egg_svg.py v6
- 그림자 구조: 두판 SVG 분석 기반
  레이어 순서: 아래판g → 그림자rect → 위판g
  그림자: 위판 y기준 +246.2px, height=1000, opacity=0.2
"""

import sys, re, os
import xml.etree.ElementTree as ET

COMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'components')
FILES = {
    '낱개': 'egg-solo.svg',
    '낱개빈칸': 'egg-solo-empty.svg',
    '한줄': 'egg-row.svg',
    '한판': 'egg-tray.svg',
}

SOLO_W, SOLO_H   = 184.96, 250.0
ROW_W,  ROW_H    = 2039.15, 250.0
TRAY_W, TRAY_H   = 2114.0, 1309.07

ROW_EGG_RIGHT = [218.34, 416.14, 613.94, 811.74, 1009.54,
                 1207.33, 1405.13, 1602.93, 1800.73, 1998.52]
EGG_WIDTH = 197.8

TRAY_COL_RIGHT = [255.77, 453.57, 651.36, 849.16, 1046.96,
                  1244.76, 1442.56, 1640.35, 1838.15, 2035.95]

TRAY_ROW_Y = [102.52, 216.02, 329.52, 443.01, 556.51,
              670.01, 783.51, 897.00, 1010.50, 1124.00]
TRAY_ROW_H = 113.5


TRAY_STACK_OFFSET    = 304.87
TRAY_SHADOW_Y_OFFSET = 246.2
TRAY_SHADOW_H        = 1000
TRAY_SHADOW_OPACITY  = 0.1
TRAY_GAP             = 40
GROUP_GAP            = 60
ITEM_GAP             = 20

_file_cache = {}
_counter    = [0]

def load_svg(key):
    if key not in _file_cache:
        with open(os.path.join(COMP_DIR, FILES[key]), 'r', encoding='utf-8') as f:
            _file_cache[key] = f.read()
    return _file_cache[key]

def new_id():
    _counter[0] += 1
    return _counter[0]

def prepare_component(key, clip_id=None):
    iid    = new_id()
    prefix = f'c{iid}'
    text   = load_svg(key)

    text = re.sub(r'<\?xml[^>]+\?>\s*', '', text)
    text = re.sub(r'\s*data-name="[^"]*"', '', text)
    text = re.sub(r'\.(st\d+)', lambda m: f'.{prefix}_{m.group(1)}', text)
    text = re.sub(r'class="(st\d+)"',
                  lambda m: f'class="{prefix}_{m.group(1)}"', text)
    text = re.sub(r'id="([^"]+)"',
                  lambda m: f'id="{prefix}_{m.group(1)}"', text)

    defs_match = re.search(r'<defs>(.*?)</defs>', text, re.DOTALL)
    defs_str   = defs_match.group(1).strip() if defs_match else ''
    text       = re.sub(r'\s*<defs>.*?</defs>\s*', '\n', text, flags=re.DOTALL)

    clip_attr = f' clip-path="url(#{clip_id})"' if clip_id else ''
    text = re.sub(r'<svg[^>]+>', f'<g{clip_attr}>', text)
    text = text.replace('</svg>', '</g>')

    return defs_str, text.strip()

_solid_row_cache = None

def get_solid_row_eggs():
    global _solid_row_cache
    if _solid_row_cache is not None:
        return _solid_row_cache

    path = os.path.join(COMP_DIR, FILES['한줄'])
    tree = ET.parse(path)
    root = tree.getroot()
    for elem in root.iter():
        elem.tag = elem.tag.split('}', 1)[1] if '}' in elem.tag else elem.tag
        elem.attrib = {(k.split('}',1)[1] if '}' in k else k): v
                       for k, v in elem.attrib.items()}

    style_text = ''
    for s in root.iter('style'):
        style_text = s.text or ''
        break

    egg_gs = [c for c in root if c.tag == 'g']
    if len(egg_gs) != 10:
        raise RuntimeError(f'egg-row.svg: 최상위 g가 {len(egg_gs)}개 (10개 예상)')

    _solid_row_cache = (style_text, egg_gs)
    return _solid_row_cache

def serialize_elem(elem, prefix):
    raw = ET.tostring(elem, encoding='unicode')
    raw = re.sub(r'class="(st\d+)"',
                 lambda m: f'class="{prefix}_{m.group(1)}"', raw)
    raw = re.sub(r'id="([^"]+)"',
                 lambda m: f'id="{prefix}_{m.group(1)}"', raw)
    return raw

def make_row_item(n_dotted):
    n_solid = 10 - n_dotted
    all_defs = []
    d_base, body_base = prepare_component('한줄')
    if d_base:
        all_defs.append(d_base)
    if n_dotted == 0:
        return all_defs, [body_base], ROW_W, ROW_H
    modified = body_base
    for idx in range(9, n_solid - 1, -1):
        g_positions = [m.start() for m in re.finditer(r'<g>', modified)]
        actual_idx = idx + 1
        if actual_idx >= len(g_positions):
            continue
        pos = g_positions[actual_idx]
        end_pos = modified.find('</g>', pos) + 4
        dx = ROW_EGG_RIGHT[idx] - 91.86 - SOLO_W / 2
        d_e, body_e = prepare_component('낱개빈칸')
        if d_e:
            d_e = d_e.replace('fill: #9e9f9f;', 'fill: #9e9f9f; stroke: #9e9f9f; stroke-width: 1;')
            all_defs.append(d_e)
        empty_group = f'<g transform="translate({dx:.3f},0)">{body_e}</g>'
        modified = modified[:pos] + empty_group + modified[end_pos:]
    return all_defs, [modified], ROW_W, ROW_H

EMPTY_EGG_CSS = (
    '\n      .empty-body {'
    ' fill: #fff; stroke: #9e9f9f;'
    ' stroke-dasharray: 8 8 0 0 0 0; stroke-width: 4; }\n'
    '      .empty-hl { opacity: 0; }'
)

def make_tray_item(n_dotted):
    n_solid = 100 - n_dotted

    if n_dotted == 0:
        d, body = prepare_component('한판')
        return ([d] if d else []), [body], TRAY_W, TRAY_H

    path_file = os.path.join(COMP_DIR, FILES['한판'])
    tree = ET.parse(path_file)
    root = tree.getroot()

    for elem in root.iter():
        elem.tag = elem.tag.split('}', 1)[1] if '}' in elem.tag else elem.tag
        elem.attrib = {(k.split('}', 1)[1] if '}' in k else k): v
                       for k, v in elem.attrib.items()}

    defs_elem = root.find('defs')
    if defs_elem is not None:
        style_elem = defs_elem.find('style')
        if style_elem is not None and style_elem.text:
            style_elem.text += EMPTY_EGG_CSS

    for egg_idx in range(n_solid, 100):
        row = egg_idx // 10
        col = egg_idx % 10
        row_g  = root[3 + row]
        eggs_g = row_g[1]
        if row % 2 == 0:       # flat structure: path, ellipse, path, ellipse, ...
            body_elem = eggs_g[col * 2]
            hl_elem   = eggs_g[col * 2 + 1]
        else:                   # grouped structure: <g><path/><ellipse/></g>
            egg_g     = eggs_g[col]
            body_elem = egg_g[0]
            hl_elem   = egg_g[1]
        body_elem.set('class', 'empty-body')
        hl_elem.set('class', 'empty-hl')

    raw = ET.tostring(root, encoding='unicode')

    iid    = new_id()
    prefix = f'c{iid}'

    raw = re.sub(r'<\?xml[^>]+\?>\s*', '', raw)
    raw = re.sub(r'\s*data-name="[^"]*"', '', raw)
    raw = re.sub(r'\.(st\d+)', lambda m: f'.{prefix}_{m.group(1)}', raw)
    raw = re.sub(r'class="(st\d+)"',
                 lambda m: f'class="{prefix}_{m.group(1)}"', raw)
    raw = re.sub(r'id="([^"]+)"',
                 lambda m: f'id="{prefix}_{m.group(1)}"', raw)

    defs_match = re.search(r'<defs>(.*?)</defs>', raw, re.DOTALL)
    defs_str   = defs_match.group(1).strip() if defs_match else ''
    raw        = re.sub(r'\s*<defs>.*?</defs>\s*', '\n', raw, flags=re.DOTALL)

    raw = re.sub(r'<svg[^>]+>', '<g>', raw)
    raw = raw.replace('</svg>', '</g>')

    return ([defs_str] if defs_str else []), [raw.strip()], TRAY_W, TRAY_H

def make_solo_item():
    d, body = prepare_component('낱개')
    return ([d] if d else []), [body], SOLO_W, SOLO_H

def parse_cmd(s):
    s = s.replace('−', '-').replace('–', '-')
    results = []
    for m in re.finditer(r'(한판|한줄|낱개)(?:\(-(\d+)\))?\s+(\d+)', s):
        unit  = m.group(1)
        empty = int(m.group(2)) if m.group(2) else 0
        count = int(m.group(3))
        if count > 0:
            results.append((unit, count, empty))
    return results

def build_svg(parsed, tray_stack=True, solo_cols=None,
              row_empty_mode='모든 줄 동일', tray_empty_last_only=False):
    _counter[0] = 0

    ORDER  = ['한판', '한줄', '낱개']
    groups = {u: [] for u in ORDER}
    all_defs = []

    for unit, count, empty in parsed:
        for i in range(count):
            if unit == '한판':
                effective_empty = empty if (not tray_empty_last_only or i == count - 1) else 0
                d, e, w, h = make_tray_item(effective_empty)
            elif unit == '한줄':
                if row_empty_mode == '마지막 줄만':
                    effective_empty = empty if i == count - 1 else 0
                elif row_empty_mode == '뒤에서부터':
                    rows_from_end   = count - 1 - i
                    effective_empty = min(max(empty - rows_from_end * 10, 0), 10)
                else:  # 모든 줄 동일
                    effective_empty = empty
                d, e, w, h = make_row_item(effective_empty)
            else:
                d, e, w, h = make_solo_item()
            all_defs.extend(d)
            groups[unit].append((e, w, h))

    active = [u for u in ORDER if groups[u]]
    if not active:
        raise ValueError("아이템이 없습니다.")

    tray_items = groups['한판']
    row_items  = groups['한줄']
    solo_items = groups['낱개']

    tray_block_w, tray_block_h = 0.0, 0.0
    row_block_w,  row_block_h  = 0.0, 0.0
    solo_block_w, solo_block_h = 0.0, 0.0

    if tray_items:
        n = len(tray_items)
        tray_block_w = TRAY_W
        if tray_stack and n > 1:
            tray_block_h = TRAY_H + (n - 1) * TRAY_STACK_OFFSET
        else:
            tray_block_h = TRAY_H * n + TRAY_GAP * (n - 1)

    if row_items:
        row_block_w = ROW_W
        row_block_h = ROW_H * len(row_items) + ITEM_GAP * (len(row_items) - 1)

    n_solo = len(solo_items)
    if solo_items:
        cols = solo_cols if solo_cols and solo_cols > 0 else n_solo
        rows = (n_solo + cols - 1) // cols
        solo_block_w = cols * SOLO_W + (cols - 1) * (ITEM_GAP * 0.5)
        solo_block_h = rows * SOLO_H + (rows - 1) * (ITEM_GAP * 0.5)

    section_widths, section_heights = [], []
    if tray_items:
        section_widths.append(tray_block_w)
        section_heights.append(tray_block_h)
    if row_items:
        section_widths.append(row_block_w)
        section_heights.append(row_block_h)
    if solo_items:
        section_widths.append(solo_block_w)
        section_heights.append(solo_block_h)

    total_w = sum(section_widths) + GROUP_GAP * (len(section_widths) - 1)
    total_h = max(section_heights) if section_heights else 100

    # 섹션별 x 시작점
    cx = 0.0
    tray_x = row_x = solo_x = 0.0
    if tray_items:
        tray_x = cx; cx += tray_block_w + GROUP_GAP
    if row_items:
        row_x = cx; cx += row_block_w + GROUP_GAP
    if solo_items:
        solo_x = cx

    final_parts = []

    # ── 한판 배치 ──────────────────────────────────────────────────────────
    if tray_items:
        n = len(tray_items)
        cy_tray = (total_h - tray_block_h) / 2

        if tray_stack and n > 1:
            # 레이어 순서: 아래판(i=0) → 그림자 → 위판(i=n-1)
            # i=0: 맨 아래판 (y가 가장 큼)
            # i=n-1: 맨 위판 (y가 가장 작음, 화면 위쪽)
            for i, (elems, w, h) in enumerate(tray_items):
                # 위판(i=n-1)의 y = cy_tray
                # 아래판일수록 y가 커짐
                y_offset = cy_tray + (n - 1 - i) * TRAY_STACK_OFFSET
                inner = '\n    '.join(elems)

                # 아래판 먼저 렌더 (z-order: 맨 아래)
                final_parts.append(
                    f'  <g transform="translate({tray_x:.3f},{y_offset:.3f})">\n'
                    f'    {inner}\n'
                    f'  </g>'
                )

                # 그림자: 위판 바닥 기준 -50px, height=200
                # y = 위판_y_offset + TRAY_H - 50
                if i < n - 1:
                    top_y = cy_tray + (n - 1 - (i + 1)) * TRAY_STACK_OFFSET
                    shadow_y = top_y + TRAY_H - 250
                    final_parts.append(
                        f'  <rect'
                        f' x="{tray_x:.3f}"'
                        f' y="{shadow_y:.3f}"'
                        f' width="{TRAY_W:.3f}"'
                        f' height="200"'
                        f' fill="black"'
                        f' opacity="{TRAY_SHADOW_OPACITY}"/>'
                    )
        else:
            cy = cy_tray
            for elems, w, h in tray_items:
                inner = '\n    '.join(elems)
                final_parts.append(
                    f'  <g transform="translate({tray_x:.3f},{cy:.3f})">\n'
                    f'    {inner}\n'
                    f'  </g>'
                )
                cy += h + TRAY_GAP

    # ── 한줄 배치 ──────────────────────────────────────────────────────────
    if row_items:
        cy_row = (total_h - row_block_h) / 2
        cy = cy_row
        for elems, w, h in row_items:
            inner = '\n    '.join(elems)
            final_parts.append(
                f'  <g transform="translate({row_x:.3f},{cy:.3f})">\n'
                f'    {inner}\n'
                f'  </g>'
            )
            cy += h + ITEM_GAP

    # ── 낱개 배치 ──────────────────────────────────────────────────────────
    if solo_items:
        cols = solo_cols if solo_cols and solo_cols > 0 else n_solo
        cy_solo = (total_h - solo_block_h) / 2
        solo_inner = []
        for idx, (elems, w, h) in enumerate(solo_items):
            col_i = idx % cols
            row_i = idx // cols
            sx = col_i * (SOLO_W + ITEM_GAP * 0.5)
            sy = row_i * (SOLO_H + ITEM_GAP * 0.5)
            inner = '\n      '.join(elems)
            solo_inner.append(
                f'    <g transform="translate({sx:.3f},{sy:.3f})">\n'
                f'      {inner}\n'
                f'    </g>'
            )
        final_parts.append(
            f'  <g transform="translate({solo_x:.3f},{cy_solo:.3f})">\n'
            + '\n'.join(solo_inner) + '\n'
            + f'  </g>'
        )

    defs_str   = '\n    '.join(d for d in all_defs if d.strip())
    defs_block = f'  <defs>\n    {defs_str}\n  </defs>\n' if defs_str else ''

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w:.3f} {total_h:.3f}">\n'
        + defs_block
        + '\n'.join(final_parts)
        + '\n</svg>\n'
    )

def main():
    if len(sys.argv) < 2:
        print('사용법: python egg_svg.py "한판 2 한줄 1 낱개 3" [output.svg]')
        sys.exit(1)
    cmd = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) >= 3 else 'output.svg'
    parsed = parse_cmd(cmd)
    if not parsed:
        print(f'오류: 명령어 인식 불가 → {cmd}')
        sys.exit(1)
    svg = build_svg(parsed)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f'저장 완료: {out}')

if __name__ == '__main__':
    main()
