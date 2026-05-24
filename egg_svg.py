#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egg_svg.py v5
- 컴포넌트: 달걀 낱개/한줄/한판 (단순화된 벡터)
- 한줄 혼합: 빈 달걀 = outline path 오버레이 방식 (clip 없음)
- 한판 혼합: 양방향 clipPath
- 한판 겹치기: 기본(겹침) / 간격(분리) 모드
- 낱개 배열: 가로 기본, 열 수 지정으로 그리드 가능

사용법: python egg_svg.py "한판 2 한줄 1 낱개 3" output.svg
"""

import sys, re, os
import xml.etree.ElementTree as ET

COMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'components')
FILES = {
    '낱개': 'egg-solo.svg',
    '한줄': 'egg-row.svg',
    '한판': 'egg-tray.svg',
}

# ── 새 컴포넌트 치수 상수 ───────────────────────────────────────────────────
SOLO_W, SOLO_H   = 184.96, 250.0      # 낱개 viewBox
ROW_W,  ROW_H    = 2039.15, 250.0     # 한줄 viewBox
TRAY_W, TRAY_H   = 2114.0, 1309.07   # 한판 viewBox

# 한줄 달걀 10개 오른쪽 경계 x
ROW_EGG_RIGHT = [218.34, 416.14, 613.94, 811.74, 1009.54,
                 1207.33, 1405.13, 1602.93, 1800.73, 1998.52]
EGG_WIDTH = 197.8  # 달걀 1개 폭

# 한판 열(column) 오른쪽 경계 x (행0 기준, 모든 행 동일)
TRAY_COL_RIGHT = [255.77, 453.57, 651.36, 849.16, 1046.96,
                  1244.76, 1442.56, 1640.35, 1838.15, 2035.95]

# 한판 행 y 시작 좌표
TRAY_ROW_Y = [102.52, 216.02, 329.52, 443.01, 556.51,
              670.01, 783.51, 897.00, 1010.50, 1124.00]
TRAY_ROW_H = 113.5  # 행 간격

# 한줄 clip 경계 x (달걀 사이 중간점) — 빈줄 생성용
ROW_CLIP_X = [(ROW_EGG_RIGHT[i] + ROW_EGG_RIGHT[i] - EGG_WIDTH + EGG_WIDTH) / 2
              for i in range(9)] + [ROW_W + 5]
# 실제 중간점: right[i]와 left[i+1] 사이
ROW_CLIP_X = [(ROW_EGG_RIGHT[i] + (ROW_EGG_RIGHT[i+1] - EGG_WIDTH)) / 2
              for i in range(9)] + [ROW_W + 5]

# 한판 열 clip 경계 x
TRAY_COL_CLIP_X = [(TRAY_COL_RIGHT[i] + (TRAY_COL_RIGHT[i+1] - EGG_WIDTH * 2.01)) / 2
                   for i in range(9)] + [TRAY_W + 5]

# 판 겹치기 y오프셋 (두판 SVG 분석값)
TRAY_STACK_OFFSET = 304.87   # 판 간 y 간격 (겹침 모드)
TRAY_GAP          = 40       # 판 간 여백 (간격 모드)

GROUP_GAP = 60   # 단위 그룹 간 가로 간격
ITEM_GAP  = 20   # 같은 단위 내 세로 간격 (간격 모드)
SHADOW_OPACITY = 0.20  # 판 겹침 그림자 투명도

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

# ── SVG 인라인 변환 ─────────────────────────────────────────────────────────

def prepare_component(key, clip_id=None):
    """SVG → 인라인 <g> 변환. (defs_str, body_str) 반환."""
    iid    = new_id()
    prefix = f'c{iid}'
    text   = load_svg(key)

    text = re.sub(r'<\?xml[^>]+\?>\s*', '', text)
    text = re.sub(r'\s*data-name="[^"]*"', '', text)

    # st0~st4 클래스 prefix
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

# ── 달걀 body 추출 (한줄 혼합용) ────────────────────────────────────────────

_solid_row_cache = None

def get_solid_row_eggs():
    """한줄.svg에서 달걀 10개의 path+ellipse 쌍 추출 (캐시)."""
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

    # 최상위 g 10개 = 달걀 10개
    egg_gs = [c for c in root if c.tag == 'g']
    if len(egg_gs) != 10:
        raise RuntimeError(f'달걀 한 줄.svg: 최상위 g가 {len(egg_gs)}개 (10개 예상)')

    _solid_row_cache = (style_text, egg_gs)
    return _solid_row_cache

def serialize_elem(elem, prefix):
    raw = ET.tostring(elem, encoding='unicode')
    raw = re.sub(r'class="(st\d+)"',
                 lambda m: f'class="{prefix}_{m.group(1)}"', raw)
    raw = re.sub(r'id="([^"]+)"',
                 lambda m: f'id="{prefix}_{m.group(1)}"', raw)
    return raw

# ── 한줄 아이템 생성 ─────────────────────────────────────────────────────────

def make_row_item(n_dotted):
    """
    한줄 혼합: 실선 달걀 N개 + 빈 달걀 outline M개 조합.
    clip 없음 — 달걀 g를 직접 조합.
    """
    n_solid = 10 - n_dotted
    all_defs = []
    style_text, egg_gs = get_solid_row_eggs()

    iid = new_id()
    prefix = f'sr{iid}'
    styled = re.sub(r'\.(st\d+)', f'.{prefix}_\\1', style_text)
    all_defs.append(f'<style>{styled}</style>')

    # 트레이/구분선은 한줄 SVG 전체에서 top-level path/polygon
    # → 전체 SVG 인라인으로 베이스 깔기
    d_base, body_base = prepare_component('한줄')
    if d_base:
        all_defs.append(d_base)

    if n_dotted == 0:
        # 전체 실선 — 그냥 한줄 통째로
        return all_defs, [body_base], ROW_W, ROW_H

    # 혼합: 한줄 베이스 위에 빈 달걀 자리를 outline으로 덮기
    # 빈 달걀 = st0 fill을 흰색(#fff)으로, outline(stroke) 점선으로 표현
    # → 실선 달걀 n_solid개만 남기고 나머지는 빈 스타일 적용
    egg_parts = []
    for i, eg in enumerate(egg_gs):
        raw = serialize_elem(eg, prefix)
        if i >= n_solid:
            # 빈 달걀: fill 제거하고 stroke 점선 스타일 적용
            raw = raw.replace(
                f'class="{prefix}_st0"',
                f'style="fill:#fff;stroke:#ccc;stroke-width:6;stroke-dasharray:12,8;" class="{prefix}_st0"'
            )
            raw = raw.replace(
                f'class="{prefix}_st1"',
                f'style="display:none;"'
            )
        egg_parts.append(raw)

    combined = body_base + '\n' + '\n'.join(egg_parts)
    return all_defs, [combined], ROW_W, ROW_H

# ── 한판 clip 생성 ─────────────────────────────────────────────────────────

def make_tray_clips(n_solid):
    n_full = n_solid // 10
    n_part = n_solid % 10
    sid = f'tcs{new_id()}'
    eid = f'tce{new_id()}'

    if n_part == 0:
        yb = TRAY_ROW_Y[n_full] if n_full < 10 else TRAY_H + 5
        solid_def = (f'<clipPath id="{sid}">'
                     f'<rect x="-5" y="-5" width="{TRAY_W+10}" height="{yb+5:.3f}"/>'
                     f'</clipPath>')
        empty_def = (f'<clipPath id="{eid}">'
                     f'<rect x="-5" y="{yb:.3f}" width="{TRAY_W+10}" '
                     f'height="{TRAY_H+10:.3f}"/>'
                     f'</clipPath>')
    else:
        yt = TRAY_ROW_Y[n_full]
        yb = yt + TRAY_ROW_H
        xr = TRAY_COL_CLIP_X[n_part - 1]
        pts_s = (f"-5,-5 {TRAY_W+5},-5 {TRAY_W+5},{yt:.3f} "
                 f"{xr:.3f},{yt:.3f} {xr:.3f},{yb:.3f} -5,{yb:.3f}")
        solid_def = (f'<clipPath id="{sid}">'
                     f'<polygon points="{pts_s}"/>'
                     f'</clipPath>')
        empty_def = (f'<clipPath id="{eid}">'
                     f'<rect x="{xr:.3f}" y="{yt:.3f}" '
                     f'width="{TRAY_W+10:.3f}" height="{TRAY_ROW_H+3:.3f}"/>'
                     f'<rect x="-5" y="{yb:.3f}" width="{TRAY_W+10}" '
                     f'height="{TRAY_H+10:.3f}"/>'
                     f'</clipPath>')

    return sid, solid_def, eid, empty_def

def make_tray_item(n_dotted):
    n_solid = 100 - n_dotted
    all_defs = []

    if n_dotted == 0:
        d, body = prepare_component('한판')
        if d: all_defs.append(d)
        return all_defs, [body], TRAY_W, TRAY_H

    if n_solid == 0:
        # 빈판 없음 → 한판에 전체 빈 스타일 (추후 빈판 컴포넌트 추가 시 교체)
        d, body = prepare_component('한판')
        if d: all_defs.append(d)
        return all_defs, [body], TRAY_W, TRAY_H

    sid, sdef, eid, edef = make_tray_clips(n_solid)
    all_defs += [sdef, edef]

    ds, solid_body = prepare_component('한판', clip_id=sid)
    de, empty_body = prepare_component('한판', clip_id=eid)
    if ds: all_defs.append(ds)
    if de: all_defs.append(de)

    return all_defs, [solid_body, empty_body], TRAY_W, TRAY_H

def make_solo_item():
    d, body = prepare_component('낱개')
    return ([d] if d else []), [body], SOLO_W, SOLO_H

# ── 명령어 파서 ─────────────────────────────────────────────────────────────

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

# ── SVG 조합 ────────────────────────────────────────────────────────────────

def build_svg(parsed, tray_stack=True, solo_cols=None):
    """
    parsed    : parse_cmd() 결과
    tray_stack: True=판 겹침 모드, False=간격 모드
    solo_cols : 낱개 열 수 (None=가로 1줄)
    """
    _counter[0] = 0

    ORDER  = ['한판', '한줄', '낱개']
    groups = {u: [] for u in ORDER}
    all_defs = []

    for unit, count, empty in parsed:
        for _ in range(count):
            if unit == '한판':
                d, e, w, h = make_tray_item(empty)
            elif unit == '한줄':
                d, e, w, h = make_row_item(empty)
            else:
                d, e, w, h = make_solo_item()
            all_defs.extend(d)
            groups[unit].append((e, w, h))

    active = [u for u in ORDER if groups[u]]
    if not active:
        raise ValueError("아이템이 없습니다.")

    body_parts = []
    shadow_rects = []

    # ── 한판 배치 ──────────────────────────────────────────────────────────
    tray_items = groups['한판']
    tray_block_w = TRAY_W
    tray_block_h = 0.0
    tray_cx = 0.0  # 나중에 전체 cx에서 오프셋

    if tray_items:
        n = len(tray_items)
        if tray_stack and n > 1:
            # 겹침 모드: 아래→위 순서로 쌓기
            # 전체 높이 = TRAY_H + (n-1) * STACK_OFFSET
            stack_h = TRAY_H + (n - 1) * TRAY_STACK_OFFSET
            tray_block_h = stack_h

            for i, (elems, w, h) in enumerate(tray_items):
                # 아래판부터(i=0 맨 아래), 위로 갈수록 y 감소
                y_offset = (n - 1 - i) * TRAY_STACK_OFFSET
                inner = '\n    '.join(elems)
                body_parts.append(
                    f'  <g transform="translate(0,{y_offset:.3f})">\n'
                    f'    {inner}\n'
                    f'  </g>'
                )
                # 그림자: y_offset만 저장, cy_tray_center 확정 후 생성
                if i > 0:
                    shadow_rects.append(y_offset)
        else:
            # 간격 모드: 세로 나열
            cy = 0.0
            for elems, w, h in tray_items:
                inner = '\n    '.join(elems)
                body_parts.append(
                    f'  <g transform="translate(0,{cy:.3f})">\n'
                    f'    {inner}\n'
                    f'  </g>'
                )
                cy += h + TRAY_GAP
            tray_block_h = cy - TRAY_GAP

    # ── 한줄 배치 ──────────────────────────────────────────────────────────
    row_items  = groups['한줄']
    row_block_w = ROW_W
    row_block_h = 0.0

    if row_items:
        cy = 0.0
        for elems, w, h in row_items:
            inner = '\n    '.join(elems)
            body_parts.append(
                f'  <g transform="translate(ROWCX,{cy:.3f})">\n'
                f'    {inner}\n'
                f'  </g>'
            )
            cy += h + ITEM_GAP
        row_block_h = cy - ITEM_GAP

    # ── 낱개 배치 ──────────────────────────────────────────────────────────
    solo_items = groups['낱개']
    solo_block_w = 0.0
    solo_block_h = 0.0
    n_solo = len(solo_items)

    if solo_items:
        cols = solo_cols if solo_cols and solo_cols > 0 else n_solo  # 기본: 가로 1줄
        rows = (n_solo + cols - 1) // cols
        solo_block_w = cols * SOLO_W + (cols - 1) * (ITEM_GAP * 0.5)
        solo_block_h = rows * SOLO_H + (rows - 1) * (ITEM_GAP * 0.5)

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
        body_parts.append(
            f'  <g transform="translate(SOLOCX,SOLOCY_CENTER)">\n'
            + '\n'.join(solo_inner) + '\n'
            + f'  </g>'
        )

    # ── 전체 캔버스 계산 ───────────────────────────────────────────────────
    section_widths  = []
    section_heights = []

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

    # ── x 오프셋 적용 ─────────────────────────────────────────────────────
    cx = 0.0
    final_parts = []
    si = 0  # section index

    for part in body_parts:
        if 'translate(ROWCX,' in part:
            if si == 0 and tray_items:
                cx_row = tray_block_w + GROUP_GAP
            elif si == 0:
                cx_row = 0
            else:
                cx_row = sum(section_widths[:si]) + GROUP_GAP * si
            # row의 수직 중앙 정렬
            cy_center = (total_h - row_block_h) / 2
            part = part.replace('translate(ROWCX,', f'translate({cx_row:.3f},')
            # cy를 중앙 정렬로 보정
            part = re.sub(
                r'translate\(' + f'{cx_row:.3f}' + r',([\d.]+)\)',
                lambda m: f'translate({cx_row:.3f},{float(m.group(1))+cy_center:.3f})',
                part
            )
            final_parts.append(part)
        elif 'translate(SOLOCX,' in part:
            si_solo = len([u for u in active if u != '낱개'])
            cx_solo = sum(section_widths[:si_solo]) + GROUP_GAP * si_solo
            cy_center = (total_h - solo_block_h) / 2
            part = (part
                    .replace('SOLOCX', f'{cx_solo:.3f}')
                    .replace('SOLOCY_CENTER', f'{cy_center:.3f}'))
            final_parts.append(part)
        else:
            # 한판 파트 — 수직 중앙 정렬
            cy_center = (total_h - tray_block_h) / 2
            if cy_center != 0:
                part = re.sub(
                    r'transform="translate\(([\d.]+),([\d.]+)\)"',
                    lambda m: f'transform="translate({m.group(1)},{float(m.group(2))+cy_center:.3f})"',
                    part
                )
            final_parts.append(part)

    # 그림자: cy_tray_center 확정 후 final_parts 뒤에 추가할 rect 생성
    cy_tray_center = (total_h - tray_block_h) / 2
    final_shadows = []
    for yo in shadow_rects:
        shadow_y = cy_tray_center + yo + TRAY_H - 70
        final_shadows.append(
            f'  <rect x="0" y="{shadow_y:.3f}" '
            f'width="{TRAY_W}" height="70" '
            f'fill="black" opacity="{SHADOW_OPACITY}" rx="20" ry="20"/>'
        )

    defs_str   = '\n    '.join(d for d in all_defs if d.strip())
    defs_block = f'  <defs>\n    {defs_str}\n  </defs>\n' if defs_str else ''

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w:.3f} {total_h:.3f}">\n'
        + defs_block
        + '\n'.join(final_parts + final_shadows)
        + '\n</svg>\n'
    )

# ── 진입점 ──────────────────────────────────────────────────────────────────

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
