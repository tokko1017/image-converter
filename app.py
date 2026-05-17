import streamlit as st
from PIL import Image
import pillow_heif
import io
import zipfile
from pathlib import Path

pillow_heif.register_heif_opener()

st.set_page_config(
    page_title="写真変換ツール",
    page_icon="🖼️",
    layout="centered",
)

# ── パスワード保護 ────────────────────────────────────────────────────────────
PASSWORD = st.secrets["password"]

def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.title("🔒 画像変換ツール")
    st.caption("このツールはパスワード保護されています。")
    pw = st.text_input("パスワード", type="password", placeholder="パスワードを入力してください")
    if st.button("ログイン", type="primary"):
        if pw == PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません。")
    return False

if not check_password():
    st.stop()
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_FORMATS = {
    "JPEG": {"ext": ".jpg",  "pil": "JPEG", "alpha": False, "has_quality": True,  "note": "写真向け・高互換"},
    "PNG":  {"ext": ".png",  "pil": "PNG",  "alpha": True,  "has_quality": False, "note": "透過対応・可逆圧縮"},
    "WebP": {"ext": ".webp", "pil": "WEBP", "alpha": True,  "has_quality": True,  "note": "Web向け・高圧縮"},
    "BMP":  {"ext": ".bmp",  "pil": "BMP",  "alpha": False, "has_quality": False, "note": "無圧縮・高互換性"},
    "TIFF": {"ext": ".tif",  "pil": "TIFF", "alpha": True,  "has_quality": False, "note": "印刷・業務向け"},
}

ACCEPT_TYPES = ["heic", "heif", "jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif"]

st.markdown("""
<style>
    .main { max-width: 720px; }
    div[data-testid="stFileUploader"] { border: 2px dashed #7c6af7; border-radius: 10px; padding: 8px; }
    div.stButton > button[kind="primary"] {
        background: #7c6af7; color: white; border: none;
        padding: 12px 0; font-size: 1.05rem; border-radius: 8px;
        width: 100%; font-weight: bold;
    }
    div.stButton > button[kind="primary"]:hover { background: #9580ff; }
    div[data-testid="stDownloadButton"] button {
        background: #22c55e; color: white; border: none;
        padding: 10px 0; font-size: 1rem; border-radius: 8px;
        width: 100%; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🖼️ 画像変換ツール")
st.caption("HEIC・JPEG・PNG・WebP など複数形式に対応。アップロードするだけで変換できます。")
st.divider()

# ── 設定 ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    fmt = st.selectbox(
        "変換後の形式",
        list(OUTPUT_FORMATS.keys()),
        help="アップロードした画像をこの形式に変換します"
    )

info = OUTPUT_FORMATS[fmt]
st.caption(f"📌 {fmt}：{info['note']}")

with col2:
    if info["has_quality"]:
        quality = st.slider("画質", min_value=40, max_value=100, value=85,
                            help="数値が高いほど高画質・ファイルサイズ大")
    else:
        quality = 85
        st.info("この形式は画質設定なし（可逆圧縮）", icon="ℹ️")

st.divider()

# ── ファイルアップロード ──────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "画像をアップロード（複数まとめてOK）",
    type=ACCEPT_TYPES,
    accept_multiple_files=True,
    label_visibility="visible",
)

if not uploaded_files:
    st.markdown("""
    **対応形式：** HEIC / HEIF / JPEG / PNG / WebP / BMP / TIFF

    **使い方**
    1. 上の枠にファイルをドラッグ＆ドロップ（または「Browse files」をクリック）
    2. 変換後の形式を選ぶ
    3. 「変換開始」ボタンを押す
    4. ダウンロードボタンから保存する
    """)
    st.stop()

st.write(f"**{len(uploaded_files)} ファイル**を選択中")
for f in uploaded_files:
    size_kb = round(f.size / 1024, 1)
    ext = Path(f.name).suffix.upper().lstrip(".")
    st.markdown(f"- `{f.name}` &nbsp; <span style='color:#7c6af7;font-size:0.85rem;'>[{ext}]</span> &nbsp; {size_kb} KB",
                unsafe_allow_html=True)

st.divider()

# ── 変換 ─────────────────────────────────────────────────────────────────────
if st.button("変換開始", type="primary"):
    results = []
    errors = []

    progress_bar = st.progress(0, text="変換中...")
    total = len(uploaded_files)

    for i, file in enumerate(uploaded_files):
        progress_bar.progress((i + 1) / total, text=f"変換中... {file.name} ({i+1}/{total})")
        try:
            img = Image.open(file)

            if not info["alpha"] and img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                src = img.convert("RGBA") if img.mode != "RGBA" else img
                bg.paste(src, mask=src.split()[3])
                img_out = bg
            elif info["alpha"] and img.mode == "P":
                img_out = img.convert("RGBA")
            else:
                img_out = img

            if not info["alpha"] and img_out.mode not in ("RGB", "L"):
                img_out = img_out.convert("RGB")
            elif info["alpha"] and img_out.mode not in ("RGB", "RGBA", "L", "LA"):
                img_out = img_out.convert("RGBA")

            buf = io.BytesIO()
            save_kwargs = {}
            if info["has_quality"]:
                save_kwargs["quality"] = quality
            if fmt == "JPEG":
                save_kwargs["optimize"] = True
            img_out.save(buf, info["pil"], **save_kwargs)
            buf.seek(0)

            out_name = Path(file.name).stem + info["ext"]
            results.append((out_name, buf.getvalue()))

        except Exception as e:
            errors.append(f"{file.name}：{e}")

    progress_bar.empty()

    if errors:
        for msg in errors:
            st.error(f"失敗：{msg}")

    if results:
        st.success(f"✅ {len(results)} ファイルの変換が完了しました！")

        if len(results) == 1:
            name, data = results[0]
            st.download_button(
                label=f"⬇️ ダウンロード：{name}",
                data=data,
                file_name=name,
            )
        else:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, data in results:
                    zf.writestr(name, data)
            zip_buf.seek(0)
            st.download_button(
                label=f"⬇️ すべてダウンロード（{len(results)} ファイル） .zip",
                data=zip_buf.getvalue(),
                file_name="converted_images.zip",
                mime="application/zip",
            )
