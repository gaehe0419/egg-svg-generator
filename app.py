#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
import sys, os, re, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import egg_svg

st.set_page_config(
    page_title="달걀 SVG 생성기",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
  .cmd-box {
    background: #f5f5f5; border-radius: 6px;
    padding: 8px 12px; font-family: monospace;
    font-size: 0.9rem; color: #444; margin-bottom: 8px;
  }
</style>
""", unsafe_allow_html=True)

st.title("🥚 달걀 SVG 생성기")

left, right = st.columns([1, 1.6], gap="large")

with left:
    st.subheader("조합 설정")
    mode = st.radio("입력 방식", ["숫자 입력", "수동 조합"],
                    horizontal=True, label_visibility="collapsed")
    st.divider()

    if mode == "숫자 입력":
        num = st.number_input("나타낼 수 (1–999)", min_value=1, max_value=999,
                              value=243, step=1)
        hanpan_count  = num // 100
        hanjul_count  = (num % 100) // 10
        naalgae_count = num % 10

        cols = st.columns(3)
        cols[0].metric("한판", f"{hanpan_count}개")
        cols[1].metric("한줄", f"{hanjul_count}개")
        cols[2].metric("낱개", f"{naalgae_count}개")

        st.divider()
        st.caption("📝 빈 자리 설정 (문제용 — 0이면 전부 채움)")

        hanpan_empty = 0
        hanjul_empty = 0

        if hanpan_count > 0:
            hanpan_empty = st.slider("한판 빈 자리 (0–100)", 0, 100, 0, key="hp_e")
        if hanjul_count > 0:
            hanjul_empty = st.slider("한줄 빈 자리 (0–10)", 0, 10, 0, key="hj_e")

    else:
        st.markdown("##### 🟫 한판 (×100)")
        c1, c2 = st.columns(2)
        hanpan_count = c1.number_input("개수", 0, 9, 0, key="hp_c")
        hanpan_empty = c2.number_input("빈 자리", 0, 100, 0, key="hp_e2",
                                       disabled=(hanpan_count == 0))

        st.markdown("##### 🟡 한줄 (×10)")
        c3, c4 = st.columns(2)
        hanjul_count = c3.number_input("개수", 0, 9, 0, key="hj_c")
        hanjul_empty = c4.number_input("빈 자리", 0, 10, 0, key="hj_e2",
                                       disabled=(hanjul_count == 0))

        st.markdown("##### 🥚 낱개 (×1)")
        naalgae_count = st.number_input("개수", 0, 9, 0, key="ng_c")

    st.divider()

    # ── 배열 옵션 ─────────────────────────────────────────────────────────
    st.caption("⚙️ 배열 옵션")

    # 한판 배열 방식 (2개 이상일 때만)
    tray_stack = True
    if hanpan_count >= 2:
        tray_mode = st.radio(
            "한판 배열",
            ["겹침 (기본)", "간격"],
            horizontal=True,
            key="tray_mode"
        )
        tray_stack = (tray_mode == "겹침 (기본)")

    # 한줄 빈 자리 적용 범위
    row_empty_last_only = False
    if hanjul_count > 1 and hanjul_empty > 0:
        empty_apply = st.radio(
            "빈 자리 적용",
            ["마지막 줄만", "모든 줄"],
            horizontal=True,
            key="row_empty_apply"
        )
        row_empty_last_only = (empty_apply == "마지막 줄만")

    # 낱개 열 수
    solo_cols = None
    if naalgae_count > 1:
        col_options = []
        for c in range(1, naalgae_count + 1):
            col_options.append(str(c))
        col_label = st.select_slider(
            "낱개 열 수",
            options=col_options,
            value=str(naalgae_count),  # 기본: 가로 한 줄
            key="solo_cols"
        )
        solo_cols = int(col_label)
        rows_preview = (naalgae_count + solo_cols - 1) // solo_cols
        st.caption(f"→ {solo_cols}열 × {rows_preview}행")


# ── 명령어 조합 ──────────────────────────────────────────────────────────────
cmd_parts = []
if hanpan_count > 0:
    suf = f"(-{hanpan_empty})" if hanpan_empty > 0 else ""
    cmd_parts.append(f"한판{suf} {hanpan_count}")
if hanjul_count > 0:
    suf = f"(-{hanjul_empty})" if hanjul_empty > 0 else ""
    cmd_parts.append(f"한줄{suf} {hanjul_count}")
if naalgae_count > 0:
    cmd_parts.append(f"낱개 {naalgae_count}")

with right:
    st.subheader("미리보기")

    if not cmd_parts:
        st.info("왼쪽에서 달걀 구성을 설정해주세요.")
    else:
        cmd = " ".join(cmd_parts)
        st.markdown(f'<div class="cmd-box">명령어: {cmd}</div>',
                    unsafe_allow_html=True)

        bg_opt = st.radio("배경", ["흰색", "체크무늬"],
                          horizontal=True, key="bg",
                          label_visibility="collapsed")
        bg_css = ""
        if bg_opt == "체크무늬":
            bg_css = ("background: repeating-conic-gradient("
                      "#d8d8d8 0% 25%, #fff 0% 50%) 0 0/16px 16px;")

        try:
            parsed  = egg_svg.parse_cmd(cmd)
            svg_out = egg_svg.build_svg(
                parsed,
                tray_stack=tray_stack,
                solo_cols=solo_cols,
                row_empty_last_only=row_empty_last_only,
            )

            svg_inline = svg_out.replace(
                '<?xml version="1.0" encoding="UTF-8"?>', '').strip()

            vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_inline)
            if vb:
                svg_w = float(vb.group(1))
                svg_h = float(vb.group(2))
                display_w = 640
                display_h = max(60, int(display_w * svg_h / svg_w))
            else:
                display_w, display_h = 640, 200

            svg_inline = svg_inline.replace(
                '<svg xmlns="http://www.w3.org/2000/svg"',
                '<svg xmlns="http://www.w3.org/2000/svg"'
                ' width="' + str(display_w) + '" height="' + str(display_h) + '"'
            )

            preview_h = display_h + 80
            pad_h = display_h + 48

            div_style = (bg_css
                         + "padding:24px;display:flex;"
                         + "justify-content:center;align-items:center;"
                         + "min-height:" + str(pad_h) + "px;border-radius:8px;"
                         + "border:1px solid #ddd;box-sizing:border-box;")

            html = "\n".join([
                "<!DOCTYPE html>",
                "<html><body style='margin:0;padding:0;background:transparent;'>",
                "<div style='" + div_style + "'>",
                svg_inline,
                "</div></body></html>",
            ])

            st.components.v1.html(html, height=preview_h, scrolling=False)

            today = datetime.date.today().strftime("%y%m%d")
            safe  = cmd.replace(" ", "_").replace("(-", "-").replace(")", "")
            fname = today + "_" + safe + ".svg"

            st.download_button(
                label="⬇ SVG 저장",
                data=svg_out,
                file_name=fname,
                mime="image/svg+xml",
                use_container_width=True,
                type="primary",
            )

            import base64
            svg_b64 = base64.b64encode(svg_out.encode('utf-8')).decode('ascii')
            png_fname = fname.replace(".svg", ".png")
            st.components.v1.html(f"""<!DOCTYPE html><html><body style="margin:0;padding:0">
<button onclick="dlPNG()" style="width:100%;height:38px;border-radius:6px;
border:1px solid rgba(49,51,63,0.2);background:white;cursor:pointer;
font-size:14px;color:rgb(49,51,63);">⬇ PNG 저장 (2배 고해상도)</button>
<script>
function dlPNG(){{
  var img=new Image();
  img.onload=function(){{
    var c=document.createElement('canvas');
    c.width=img.naturalWidth*2; c.height=img.naturalHeight*2;
    var ctx=c.getContext('2d'); ctx.scale(2,2); ctx.drawImage(img,0,0);
    c.toBlob(function(b){{
      var a=document.createElement('a');
      a.href=URL.createObjectURL(b); a.download='{png_fname}';
      document.body.appendChild(a); a.click(); a.remove();
    }},'image/png');
  }};
  img.src='data:image/svg+xml;base64,{svg_b64}';
}}
</script></body></html>""", height=46)

        except Exception as e:
            import traceback
            st.error(f"생성 오류: {e}")
            st.code(traceback.format_exc())
