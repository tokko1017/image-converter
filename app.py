import streamlit as st
from PIL import Image
import pillow_heif
import io
import zipfile
import subprocess
import tempfile
import os
from pathlib import Path

pillow_heif.register_heif_opener()

st.set_page_config(
    page_title="写真・動画変換ツール",
    page_icon="🖼️",
    layout="centered",
)

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

tab_img, tab_vid = st.tabs(["🖼️ 画像変換", "🎬 動画変換"])

# ── 画像変換 ──────────────────────────────────────────────────────────────────
with tab_img:
    OUTPUT_FORMATS = {
        "JPEG": {"ext": ".jpg",  "pil": "JPEG", "alpha": False, "has_quality": True,  "note": "写真向け・高互換"},
        "PNG":  {"ext": ".png",  "pil": "PNG",  "alpha": True,  "has_quality": False, "note": "透過対応・可逆圧縮"},
        "WebP": {"ext": ".webp", "pil": "WEBP", "alpha": True,  "has_quality": True,  "note": "Web向け・高圧縮"},
        "AVIF": {"ext": ".avif", "pil": "AVIF", "alpha": True,  "has_quality": True,  "note": "次世代・高圧縮・透過対応"},
        "BMP":  {"ext": ".bmp",  "pil": "BMP",  "alpha": False, "has_quality": False, "note": "無圧縮・高互換性"},
        "TIFF": {"ext": ".tif",  "pil": "TIFF", "alpha": True,  "has_quality": False, "note": "印刷・業務向け"},
    }
    ACCEPT_TYPES = ["heic", "heif", "jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "tif"]

    st.title("🖼️ 画像変換ツール")
    st.caption("HEIC・JPEG・PNG・WebP など複数形式に対応。アップロードするだけで変換できます。")
    st.divider()

    col1, col2 = st.columns([3, 2])
    with col1:
        fmt = st.selectbox("変換後の形式", list(OUTPUT_FORMATS.keys()),
                           help="アップロードした画像をこの形式に変換します")
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

    uploaded_files = st.file_uploader(
        "画像をアップロード（複数まとめてOK）",
        type=ACCEPT_TYPES,
        accept_multiple_files=True,
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
    else:
        st.write(f"**{len(uploaded_files)} ファイル**を選択中")
        for f in uploaded_files:
            size_kb = round(f.size / 1024, 1)
            ext = Path(f.name).suffix.upper().lstrip(".")
            st.markdown(f"- `{f.name}` &nbsp; <span style='color:#7c6af7;font-size:0.85rem;'>[{ext}]</span> &nbsp; {size_kb} KB",
                        unsafe_allow_html=True)
        st.divider()

        if st.button("変換開始", type="primary", key="img_convert"):
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
                    results.append((Path(file.name).stem + info["ext"], buf.getvalue()))
                except Exception as e:
                    errors.append(f"{file.name}：{e}")

            progress_bar.empty()
            for msg in errors:
                st.error(f"失敗：{msg}")

            if results:
                st.success(f"✅ {len(results)} ファイルの変換が完了しました！")
                if len(results) == 1:
                    name, data = results[0]
                    st.download_button(f"⬇️ ダウンロード：{name}", data=data, file_name=name)
                else:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for name, data in results:
                            zf.writestr(name, data)
                    zip_buf.seek(0)
                    st.download_button(
                        f"⬇️ すべてダウンロード（{len(results)} ファイル） .zip",
                        data=zip_buf.getvalue(),
                        file_name="converted_images.zip",
                        mime="application/zip",
                    )

# ── 動画変換 ──────────────────────────────────────────────────────────────────
with tab_vid:
    VIDEO_INPUT_TYPES = ["mp4", "mov", "avi", "mkv", "webm", "m4v"]
    VIDEO_OUTPUT_FORMATS = {
        "MP4":  {"ext": ".mp4",  "note": "最も互換性が高い・スマホ・PC問わず再生可能"},
        "WebM": {"ext": ".webm", "note": "Web向け・軽量・ブラウザ再生に最適"},
        "GIF":  {"ext": ".gif",  "note": "アニメーションGIF・SNS向け（音声なし）"},
        "MP3":  {"ext": ".mp3",  "note": "音声のみ抽出して保存"},
    }

    def ffmpeg_available():
        try:
            return subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5).returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    st.title("🎬 動画変換ツール")
    st.caption("MP4・MOV・AVI・MKV・WebM に対応。アップロードするだけで変換できます。")
    st.divider()

    if not ffmpeg_available():
        st.error("FFmpegがインストールされていないため、動画変換は使用できません。")
    else:
        col1v, col2v = st.columns([3, 2])
        with col1v:
            vfmt = st.selectbox("変換後の形式", list(VIDEO_OUTPUT_FORMATS.keys()),
                                help="動画をこの形式に変換します", key="vfmt")
        vinfo = VIDEO_OUTPUT_FORMATS[vfmt]
        st.caption(f"📌 {vfmt}：{vinfo['note']}")

        gif_fps = 10
        gif_width = 480
        if vfmt == "GIF":
            with col2v:
                gif_fps = st.select_slider("フレームレート (fps)", options=[5, 10, 15, 24], value=10)
                gif_width = st.select_slider("横幅 (px)", options=[240, 360, 480, 640], value=480)

        st.divider()

        uploaded_video = st.file_uploader(
            "動画をアップロード（1ファイルずつ）",
            type=VIDEO_INPUT_TYPES,
            accept_multiple_files=False,
            key="video_uploader",
        )

        if not uploaded_video:
            st.markdown("""
            **対応入力形式：** MP4 / MOV / AVI / MKV / WebM / M4V

            > ⚠️ ファイルサイズは **200MB以下** を推奨します。

            **使い方**
            1. 上の枠にファイルをドラッグ＆ドロップ（または「Browse files」をクリック）
            2. 変換後の形式を選ぶ
            3. 「変換開始」ボタンを押す
            4. ダウンロードボタンから保存する
            """)
        else:
            size_mb = round(uploaded_video.size / 1024 / 1024, 1)
            st.write(f"**{uploaded_video.name}** &nbsp; {size_mb} MB")
            st.divider()

            if st.button("変換開始", type="primary", key="vid_convert"):
                with st.spinner("変換中... しばらくお待ちください"):
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            input_path = os.path.join(tmpdir, "input" + Path(uploaded_video.name).suffix)
                            with open(input_path, "wb") as f:
                                f.write(uploaded_video.getbuffer())

                            out_name = Path(uploaded_video.name).stem + vinfo["ext"]
                            output_path = os.path.join(tmpdir, out_name)

                            if vfmt == "MP4":
                                cmd = ["ffmpeg", "-i", input_path,
                                       "-c:v", "libx264", "-c:a", "aac",
                                       "-movflags", "+faststart", "-y", output_path]
                            elif vfmt == "WebM":
                                cmd = ["ffmpeg", "-i", input_path,
                                       "-c:v", "libvpx-vp9", "-c:a", "libopus",
                                       "-y", output_path]
                            elif vfmt == "GIF":
                                palette_path = os.path.join(tmpdir, "palette.png")
                                subprocess.run(
                                    ["ffmpeg", "-i", input_path,
                                     "-vf", f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos,palettegen",
                                     "-y", palette_path],
                                    capture_output=True, timeout=120,
                                )
                                cmd = ["ffmpeg", "-i", input_path, "-i", palette_path,
                                       "-filter_complex",
                                       f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos[x];[x][1:v]paletteuse",
                                       "-y", output_path]
                            elif vfmt == "MP3":
                                cmd = ["ffmpeg", "-i", input_path,
                                       "-q:a", "2", "-map", "a", "-y", output_path]

                            result = subprocess.run(cmd, capture_output=True, timeout=300)

                            if result.returncode != 0:
                                err_msg = result.stderr.decode("utf-8", errors="replace")
                                st.error(f"変換に失敗しました。\n```\n{err_msg[-500:]}\n```")
                            else:
                                with open(output_path, "rb") as f:
                                    output_data = f.read()
                                out_size_mb = round(len(output_data) / 1024 / 1024, 1)
                                st.success("✅ 変換が完了しました！")
                                st.caption(f"出力サイズ：{out_size_mb} MB")
                                st.download_button(
                                    label=f"⬇️ ダウンロード：{out_name}",
                                    data=output_data,
                                    file_name=out_name,
                                )

                    except subprocess.TimeoutExpired:
                        st.error("変換がタイムアウトしました。ファイルサイズを小さくしてお試しください。")
                    except Exception as e:
                        st.error(f"エラーが発生しました：{e}")
