# egg-svg-generator

달걀 수량에 따라 SVG 이미지를 생성하는 Python 도구.

## 파일 구조

- `egg_svg.py` — 핵심 SVG 생성 로직
- `app.py` — Streamlit UI
- `components/` — SVG 소스 컴포넌트
  - `egg-tray.svg` — 한판 (10×10, 100개)
  - `egg-row.svg` — 한줄 (1×10, 10개)
  - `egg-solo.svg` — 낱개 (1개)
  - `egg-solo-empty.svg` — 낱개 빈칸 (점선 달걀)

## 명령어 형식

```
한판(-N) K  →  한판 K개, 빈자리 N개
한줄(-N) K  →  한줄 K개, 빈자리 N개
낱개 K      →  낱개 K개
```

## 핵심 구현 결정 사항

### 한판(트레이) 빈달걀 표현 방식

**확정 방식:** `egg-tray.svg`를 `ElementTree`로 파싱한 뒤, 빈 달걀 위치의 요소 `class`를 직접 교체.

- 달걀 body `<path>` → `class="empty-body"` (흰색 + 회색 점선 stroke)
- 달걀 highlight `<ellipse>` → `class="empty-hl"` (숨김)

**기각된 방식:** `egg-solo-empty.svg` 컴포넌트를 `translate`로 위에 올려씌우는 오버레이 방식
→ z-order 문제로 기각.

### egg-tray.svg 내부 구조

`root[3]` ~ `root[12]` 가 row 0~9에 해당. 각 row는 `<g>` 두 개:
- `row_g[0]` — 달걀 캡(홈) 9개
- `row_g[1]` — 달걀 몸체 10개

달걀 몸체 그룹 구조는 짝/홀수 행이 다름:
- **짝수 행 (0,2,4,6,8):** flat — `eggs_g[col*2]`=body, `eggs_g[col*2+1]`=highlight
- **홀수 행 (1,3,5,7,9):** grouped — `eggs_g[col][0]`=body, `eggs_g[col][1]`=highlight

### 빈달걀 CSS

```css
.empty-body { fill: #fff; stroke: #9e9f9f; stroke-dasharray: 8 8 0 0 0 0; stroke-width: 4; }
.empty-hl   { opacity: 0; }
```

## 주의사항

`build_svg`에서 `all_defs.extend(d)`를 사용하므로, `make_*_item` 함수의 첫 번째 반환값은 반드시 **리스트**로 반환해야 함. 문자열을 넘기면 문자 단위로 분해됨.
