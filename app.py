import streamlit as st
from PIL import Image
import pillow_heif
import io
import zipfile
import subprocess
import tempfile
import os
import csv
from pathlib import Path

pillow_heif.register_heif_opener()

st.set_page_config(
    page_title="写真・動画・文書 変換ツール",
    page_icon="🌸",
    layout="centered",
)

st.markdown("""
<style>
.stApp { background: linear-gradient(160deg, #fdf4ff 0%, #eff6ff 100%); }

div[data-baseweb="tab-list"] {
    background: #f3e8ff;
    border-radius: 20px;
    padding: 6px;
    gap: 4px;
}
button[data-baseweb="tab"] {
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    padding: 10px 14px !important;
    border-radius: 14px !important;
    color: #7c3aed !important;
    background: transparent !important;
}
button[data-baseweb="tab"]:hover { background: #ede9fe !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #e879f9, #818cf8) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.35) !important;
}
div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-baseweb="tab-border"] { display: none !important; }

div[data-testid="stFileUploader"] {
    border: 2.5px dashed #c084fc;
    border-radius: 16px;
    padding: 12px;
    background: #fdf4ff;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #e879f9, #818cf8);
    color: white; border: none;
    padding: 14px 0; font-size: 1.1rem;
    border-radius: 14px; width: 100%; font-weight: bold;
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
    letter-spacing: 0.04em;
}
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #f0abfc, #a5b4fc);
    box-shadow: 0 6px 20px rgba(168, 85, 247, 0.45);
}
div[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #34d399, #059669);
    color: white; border: none;
    padding: 12px 0; font-size: 1rem;
    border-radius: 14px; width: 100%; font-weight: bold;
    box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);
}
hr {
    border: none; height: 2px;
    background: linear-gradient(90deg, #f9a8d4, #c084fc, #818cf8, #6ee7b7);
    border-radius: 2px; opacity: 0.55; margin: 16px 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding: 24px 0 16px;">
  <div style="font-size:2.8rem; margin-bottom:8px;">🌸</div>
  <div style="
    background: linear-gradient(135deg, #e879f9, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2rem; font-weight: 900; margin: 0 0 6px; line-height: 1.3;">
    写真・動画・文書 変換ツール
  </div>
  <p style="color: #9333ea; font-size: 0.95rem; margin: 0;">
    ドラッグ＆ドロップで簡単変換 ✨
  </p>
</div>
""", unsafe_allow_html=True)

tab_img, tab_vid, tab_doc, tab_sns, tab_erase = st.tabs([
    "　🖼️  画像変換　",
    "　🎬  動画変換　",
    "　📄  文書変換　",
    "　📱  SNSサイズ　",
    "　✏️  文字消し　",
])

# ── ヘルパー ─────────────────────────────────────────────────────────────────
def step_guide(steps, formats_text):
    steps_html = "".join(f"""
      <div style="display:flex;align-items:center;gap:10px;padding:5px 0;">
        <span style="background:linear-gradient(135deg,#e879f9,#818cf8);color:white;
          border-radius:50%;width:26px;height:26px;display:flex;align-items:center;
          justify-content:center;font-size:0.8rem;font-weight:bold;flex-shrink:0;">{i+1}</span>
        <span style="color:#4c1d95;font-size:0.93rem;">{s}</span>
      </div>""" for i, s in enumerate(steps))
    st.markdown(f"""
    <div style="background:#fdf4ff;border-radius:16px;padding:20px;border:1.5px solid #e9d5ff;">
      <p style="color:#7c3aed;font-weight:700;font-size:0.95rem;margin:0 0 10px;">📋 使い方</p>
      {steps_html}
      <div style="border-top:1.5px solid #e9d5ff;margin-top:12px;padding-top:10px;">
        <p style="color:#7c3aed;font-size:0.85rem;margin:0;">
          <strong>対応形式：</strong>{formats_text}
        </p>
      </div>
    </div>""", unsafe_allow_html=True)

def format_badge(fmt, note):
    return (f"<div style='background:#f3e8ff;border-radius:10px;padding:8px 14px;"
            f"color:#6d28d9;font-size:0.9rem;margin-bottom:8px;'>"
            f"📌 <strong>{fmt}</strong>：{note}</div>")

def file_badge(name, ext, size_label):
    return (f"<div style='padding:7px 12px;margin:4px 0;background:#fdf4ff;"
            f"border-radius:8px;border-left:3px solid #c084fc;font-size:0.9rem;'>"
            f"📄 <strong>{name}</strong> &nbsp;"
            f"<span style='background:#e9d5ff;color:#7c3aed;border-radius:4px;"
            f"padding:1px 7px;font-size:0.78rem;'>{ext}</span>"
            f" &nbsp; {size_label}</div>")

def selected_badge(label):
    return (f"<div style='background:#f0fdf4;border-radius:12px;padding:12px 16px;"
            f"border:1.5px solid #6ee7b7;color:#065f46;font-weight:600;'>"
            f"✅ {label}</div>")

def warning_badge(text):
    return (f"<div style='background:#fff7ed;border-radius:10px;padding:10px 14px;"
            f"border:1.5px solid #fed7aa;color:#92400e;font-size:0.85rem;margin-top:10px;'>"
            f"⚠️ {text}</div>")

def conversion_table(rows):
    trs = "".join(
        f"<tr{'  style=\"background:#faf5ff;\"' if i%2 else ''}>"
        f"<td style='padding:6px 10px;'>{r[0]}</td>"
        f"<td style='padding:6px 10px;'>{r[1]}</td></tr>"
        for i, r in enumerate(rows)
    )
    return f"""
    <div style="background:#f3e8ff;border-radius:14px;padding:16px;margin-top:12px;border:1.5px solid #ddd6fe;">
      <p style="color:#7c3aed;font-weight:700;margin:0 0 10px;">📊 変換できる組み合わせ</p>
      <table style="width:100%;border-collapse:collapse;font-size:0.88rem;color:#4c1d95;">
        <tr style="background:#ede9fe;">
          <th style="padding:6px 10px;text-align:left;border-radius:6px 0 0 6px;">出力形式</th>
          <th style="padding:6px 10px;text-align:left;border-radius:0 6px 6px 0;">説明</th>
        </tr>
        {trs}
      </table>
    </div>"""

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

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    with col1:
        fmt = st.selectbox("✨ 変換後の形式", list(OUTPUT_FORMATS.keys()),
                           help="アップロードした画像をこの形式に変換します")
    info = OUTPUT_FORMATS[fmt]
    st.markdown(format_badge(fmt, info["note"]), unsafe_allow_html=True)
    with col2:
        if info["has_quality"]:
            quality = st.slider("🎚️ 画質", min_value=40, max_value=100, value=85)
        else:
            quality = 85
            st.info("可逆圧縮のため画質設定なし", icon="ℹ️")
    st.divider()

    uploaded_files = st.file_uploader("📂 画像をアップロード（複数まとめてOK）",
                                      type=ACCEPT_TYPES, accept_multiple_files=True)

    if not uploaded_files:
        step_guide(
            ["画像ファイルを上の枠にドラッグ＆ドロップ（または「Upload」をクリック）",
             "変換後の形式・画質を選ぶ",
             "「変換開始」ボタンを押す",
             "ダウンロードボタンから保存する"],
            "HEIC / HEIF / JPEG / PNG / WebP / AVIF / BMP / TIFF"
        )
        st.markdown(conversion_table([
            ("JPEG", "写真向け・高互換・ファイルサイズ小"),
            ("PNG",  "透過対応・可逆圧縮・高品質"),
            ("WebP", "Web向け・高圧縮・透過対応"),
            ("AVIF", "次世代形式・高圧縮・透過対応"),
            ("BMP",  "無圧縮・高互換性"),
            ("TIFF", "印刷・業務向け・高品質"),
        ]), unsafe_allow_html=True)
    else:
        st.markdown(selected_badge(f"{len(uploaded_files)} ファイルを選択中"), unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        for f in uploaded_files:
            size_kb = round(f.size / 1024, 1)
            ext = Path(f.name).suffix.upper().lstrip(".")
            st.markdown(file_badge(f.name, ext, f"{size_kb} KB"), unsafe_allow_html=True)
        st.divider()

        if st.button("✨ 変換開始", type="primary", key="img_convert"):
            results, errors = [], []
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
                st.success(f"🎉 {len(results)} ファイルの変換が完了しました！")
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
                        data=zip_buf.getvalue(), file_name="converted_images.zip",
                        mime="application/zip")

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

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    if not ffmpeg_available():
        st.error("FFmpegがインストールされていないため、動画変換は使用できません。")
    else:
        col1v, col2v = st.columns([3, 2])
        with col1v:
            vfmt = st.selectbox("✨ 変換後の形式", list(VIDEO_OUTPUT_FORMATS.keys()), key="vfmt")
        vinfo = VIDEO_OUTPUT_FORMATS[vfmt]
        st.markdown(format_badge(vfmt, vinfo["note"]), unsafe_allow_html=True)
        gif_fps, gif_width = 10, 480
        if vfmt == "GIF":
            with col2v:
                gif_fps = st.select_slider("🎞️ フレームレート (fps)", options=[5, 10, 15, 24], value=10)
                gif_width = st.select_slider("📐 横幅 (px)", options=[240, 360, 480, 640], value=480)
        st.divider()

        uploaded_video = st.file_uploader("📂 動画をアップロード（1ファイルずつ）",
                                          type=VIDEO_INPUT_TYPES, accept_multiple_files=False,
                                          key="video_uploader")
        if not uploaded_video:
            step_guide(
                ["動画ファイルを上の枠にドラッグ＆ドロップ（または「Upload」をクリック）",
                 "変換後の形式を選ぶ（GIFはフレームレート・横幅も設定可）",
                 "「変換開始」ボタンを押す",
                 "ダウンロードボタンから保存する"],
                "MP4 / MOV / AVI / MKV / WebM / M4V"
            )
            st.markdown(conversion_table([
                ("MP4",  "最も互換性が高い・スマホ・PC問わず再生可能"),
                ("WebM", "Web向け・軽量・ブラウザ再生に最適"),
                ("GIF",  "アニメーションGIF・SNS向け（音声なし）"),
                ("MP3",  "音声のみ抽出して保存"),
            ]), unsafe_allow_html=True)
            st.markdown("<p style='color:#6d28d9;font-size:0.85rem;margin:6px 0 0 4px;'>※ すべての入力形式から、すべての出力形式へ変換できます。</p>",
                        unsafe_allow_html=True)
            st.markdown(warning_badge("ファイルサイズは <strong>200MB以下</strong> を推奨します"),
                        unsafe_allow_html=True)
        else:
            size_mb = round(uploaded_video.size / 1024 / 1024, 1)
            st.markdown(selected_badge(
                f"{uploaded_video.name} &nbsp; <span style='font-weight:400;'>{size_mb} MB</span>"),
                unsafe_allow_html=True)
            st.divider()
            if st.button("✨ 変換開始", type="primary", key="vid_convert"):
                with st.spinner("変換中... しばらくお待ちください 🎬"):
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            input_path = os.path.join(tmpdir, "input" + Path(uploaded_video.name).suffix)
                            with open(input_path, "wb") as f:
                                f.write(uploaded_video.getbuffer())
                            out_name = Path(uploaded_video.name).stem + vinfo["ext"]
                            output_path = os.path.join(tmpdir, out_name)
                            if vfmt == "MP4":
                                cmd = ["ffmpeg", "-i", input_path, "-c:v", "libx264",
                                       "-c:a", "aac", "-movflags", "+faststart", "-y", output_path]
                            elif vfmt == "WebM":
                                cmd = ["ffmpeg", "-i", input_path, "-c:v", "libvpx-vp9",
                                       "-c:a", "libopus", "-y", output_path]
                            elif vfmt == "GIF":
                                palette_path = os.path.join(tmpdir, "palette.png")
                                subprocess.run(
                                    ["ffmpeg", "-i", input_path,
                                     "-vf", f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos,palettegen",
                                     "-y", palette_path], capture_output=True, timeout=120)
                                cmd = ["ffmpeg", "-i", input_path, "-i", palette_path,
                                       "-filter_complex",
                                       f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos[x];[x][1:v]paletteuse",
                                       "-y", output_path]
                            elif vfmt == "MP3":
                                cmd = ["ffmpeg", "-i", input_path, "-q:a", "2",
                                       "-map", "a", "-y", output_path]
                            result = subprocess.run(cmd, capture_output=True, timeout=300)
                            if result.returncode != 0:
                                err_msg = result.stderr.decode("utf-8", errors="replace")
                                st.error(f"変換に失敗しました。\n```\n{err_msg[-500:]}\n```")
                            else:
                                with open(output_path, "rb") as f:
                                    output_data = f.read()
                                st.success("🎉 変換が完了しました！")
                                st.caption(f"出力サイズ：{round(len(output_data)/1024/1024, 1)} MB")
                                st.download_button(f"⬇️ ダウンロード：{out_name}",
                                                   data=output_data, file_name=out_name)
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ 変換がタイムアウトしました。ファイルサイズを小さくしてお試しください。")
                    except Exception as e:
                        st.error(f"エラーが発生しました：{e}")

# ── 文書変換 ──────────────────────────────────────────────────────────────────
with tab_doc:
    DOC_INPUT_TYPES = ["txt", "docx", "pdf", "xlsx", "pptx"]
    OUTPUT_BY_EXT = {
        "txt":  ["PDF", "JPEG", "PNG", "WebP"],
        "docx": ["PDF", "TXT", "JPEG", "PNG", "WebP"],
        "pdf":  ["TXT", "PPTX", "JPEG", "PNG", "WebP"],
        "xlsx": ["PDF", "CSV", "JPEG", "PNG", "WebP"],
        "pptx": ["PDF", "TXT", "JPEG", "PNG", "WebP"],
    }
    FORMAT_NOTES = {
        "PDF":  "どの端末でも同じレイアウトで開ける",
        "TXT":  "テキストを抽出してプレーンテキストで保存",
        "CSV":  "Excel・スプレッドシートで開けるデータ形式",
        "PPTX": "PDFの各ページをスライドとして画像化・PowerPointで開ける",
        "JPEG": "ページ・スライドごとに画像化（写真向け・高互換）",
        "PNG":  "ページ・スライドごとに画像化（高品質・透過対応）",
        "WebP": "ページ・スライドごとに画像化（Web向け・軽量）",
    }

    def libreoffice_available():
        try:
            return subprocess.run(["libreoffice", "--version"],
                                  capture_output=True, timeout=5).returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def to_pdf(input_path, tmpdir):
        env = {**os.environ, "HOME": tmpdir}
        cmd = ["libreoffice", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", tmpdir, input_path]
        result = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
        out = Path(tmpdir) / (Path(input_path).stem + ".pdf")
        if result.returncode == 0 and out.exists():
            return out, None
        return None, result.stderr.decode("utf-8", errors="replace")

    def pdf_to_pptx(input_path, tmpdir, dpi=150):
        import fitz
        from pptx import Presentation
        from pptx.util import Inches
        doc = fitz.open(input_path)
        prs = Presentation()
        if len(doc) > 0:
            r = doc[0].rect
            prs.slide_width  = Inches(r.width  / 72)
            prs.slide_height = Inches(r.height / 72)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        blank = prs.slide_layouts[6]
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = io.BytesIO()
            img.save(buf, "PNG")
            buf.seek(0)
            slide = prs.slides.add_slide(blank)
            slide.shapes.add_picture(buf, 0, 0,
                                     width=prs.slide_width,
                                     height=prs.slide_height)
        doc.close()
        out = Path(tmpdir) / "output.pptx"
        prs.save(str(out))
        return out

    def to_images(input_path, img_format, dpi, tmpdir):
        import fitz
        ext = Path(input_path).suffix.lower()
        if ext != ".pdf":
            pdf_path, err = to_pdf(input_path, tmpdir)
            if not pdf_path:
                return None, err
            input_path = str(pdf_path)
        doc = fitz.open(input_path)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        suffix = {"JPEG": ".jpg", "PNG": ".png", "WebP": ".webp"}[img_format]
        pil_fmt = {"JPEG": "JPEG", "PNG": "PNG", "WebP": "WEBP"}[img_format]
        images = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = io.BytesIO()
            if img_format == "JPEG":
                img.save(buf, pil_fmt, quality=90, optimize=True)
            elif img_format == "PNG":
                img.save(buf, pil_fmt)
            else:
                img.save(buf, pil_fmt, quality=90)
            buf.seek(0)
            images.append((f"page_{i+1:03d}{suffix}", buf.getvalue()))
        doc.close()
        return images, None

    def extract_text(input_path):
        ext = Path(input_path).suffix.lower()
        if ext == ".pdf":
            import pdfplumber
            parts = []
            with pdfplumber.open(input_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            return "\n\n".join(parts)
        elif ext == ".docx":
            from docx import Document
            doc = Document(input_path)
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext == ".pptx":
            from pptx import Presentation
            prs = Presentation(input_path)
            lines = []
            for i, slide in enumerate(prs.slides, 1):
                lines.append(f"=== スライド {i} ===")
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        lines.append(shape.text_frame.text)
                lines.append("")
            return "\n".join(lines)
        return ""

    def to_csv_bytes(input_path):
        import openpyxl
        wb = openpyxl.load_workbook(input_path, data_only=True)
        ws = wb.active
        buf = io.StringIO()
        writer = csv.writer(buf)
        for row in ws.iter_rows(values_only=True):
            writer.writerow(['' if v is None else v for v in row])
        return buf.getvalue().encode("utf-8-sig")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    uploaded_doc = st.file_uploader("📂 文書をアップロード", type=DOC_INPUT_TYPES,
                                    accept_multiple_files=False, key="doc_uploader")

    if not uploaded_doc:
        step_guide(
            ["文書ファイルを上の枠にドラッグ＆ドロップ（または「Upload」をクリック）",
             "変換後の形式を選ぶ（ファイルの種類によって選択肢が変わります）",
             "「変換開始」ボタンを押す",
             "ダウンロードボタンから保存する"],
            "TXT / DOCX / PDF / XLSX / PPTX"
        )
        st.markdown("""
        <div style="background:#f3e8ff;border-radius:14px;padding:16px;margin-top:12px;border:1.5px solid #ddd6fe;">
          <p style="color:#7c3aed;font-weight:700;margin:0 0 10px;">📊 変換できる組み合わせ</p>
          <table style="width:100%;border-collapse:collapse;font-size:0.88rem;color:#4c1d95;">
            <tr style="background:#ede9fe;">
              <th style="padding:6px 10px;text-align:left;border-radius:6px 0 0 6px;">入力</th>
              <th style="padding:6px 10px;text-align:left;border-radius:0 6px 6px 0;">変換できる形式</th>
            </tr>
            <tr><td style="padding:6px 10px;">TXT</td><td style="padding:6px 10px;">→ PDF・JPEG・PNG・WebP</td></tr>
            <tr style="background:#faf5ff;"><td style="padding:6px 10px;">DOCX（Word）</td><td style="padding:6px 10px;">→ PDF・TXT・JPEG・PNG・WebP</td></tr>
            <tr><td style="padding:6px 10px;">PDF</td><td style="padding:6px 10px;">→ TXT・PPTX・JPEG・PNG・WebP</td></tr>
            <tr style="background:#faf5ff;"><td style="padding:6px 10px;">XLSX（Excel）</td><td style="padding:6px 10px;">→ PDF・CSV・JPEG・PNG・WebP</td></tr>
            <tr><td style="padding:6px 10px;">PPTX（PowerPoint）</td><td style="padding:6px 10px;">→ PDF・TXT・JPEG・PNG・WebP</td></tr>
          </table>
        </div>
        """, unsafe_allow_html=True)
    else:
        ext = Path(uploaded_doc.name).suffix.lower().lstrip(".")
        size_kb = round(uploaded_doc.size / 1024, 1)
        st.markdown(selected_badge(
            f"{uploaded_doc.name} &nbsp; <span style='font-weight:400;'>{size_kb} KB</span>"),
            unsafe_allow_html=True)
        available_outputs = OUTPUT_BY_EXT.get(ext, [])
        if not available_outputs:
            st.error("対応していない形式です。")
        else:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            out_fmt = st.selectbox("✨ 変換後の形式", available_outputs, key="doc_out_fmt")
            st.markdown(format_badge(out_fmt, FORMAT_NOTES[out_fmt]), unsafe_allow_html=True)
            dpi = 150
            if out_fmt in ("JPEG", "PNG", "WebP", "PPTX"):
                dpi = st.select_slider("🖨️ 解像度 (DPI)", options=[96, 150, 300], value=150,
                                       help="96=画面向け・150=標準・300=印刷品質", key="doc_dpi")
            st.divider()
            if st.button("✨ 変換開始", type="primary", key="doc_convert"):
                needs_lo = (out_fmt in ("PDF", "JPEG", "PNG", "WebP") and ext != "pdf")
                if needs_lo and not libreoffice_available():
                    st.error("LibreOfficeがインストールされていないため変換できません。")
                else:
                    with st.spinner("変換中... しばらくお待ちください 📄"):
                        try:
                            with tempfile.TemporaryDirectory() as tmpdir:
                                input_path = os.path.join(tmpdir, "input." + ext)
                                with open(input_path, "wb") as f:
                                    f.write(uploaded_doc.getbuffer())
                                out_stem = Path(uploaded_doc.name).stem
                                if out_fmt == "PDF":
                                    out_path, err = to_pdf(input_path, tmpdir)
                                    if out_path:
                                        st.success("🎉 変換が完了しました！")
                                        st.download_button(f"⬇️ ダウンロード：{out_stem}.pdf",
                                                           data=out_path.read_bytes(),
                                                           file_name=out_stem + ".pdf",
                                                           mime="application/pdf")
                                    else:
                                        st.error(f"変換に失敗しました。\n```\n{err[-500:]}\n```")
                                elif out_fmt == "TXT":
                                    text = extract_text(input_path)
                                    if text.strip():
                                        st.success("🎉 テキストの抽出が完了しました！")
                                        st.download_button(f"⬇️ ダウンロード：{out_stem}.txt",
                                                           data=text.encode("utf-8"),
                                                           file_name=out_stem + ".txt",
                                                           mime="text/plain")
                                    else:
                                        st.warning("テキストが抽出できませんでした。スキャンされたPDFなどは対応できません。")
                                elif out_fmt == "PPTX":
                                    out_path = pdf_to_pptx(input_path, tmpdir, dpi)
                                    out_name = Path(uploaded_doc.name).stem + ".pptx"
                                    st.success(f"🎉 {out_name} の変換が完了しました！")
                                    st.download_button(
                                        f"⬇️ ダウンロード：{out_name}",
                                        data=out_path.read_bytes(),
                                        file_name=out_name,
                                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    )
                                elif out_fmt == "CSV":
                                    st.success("🎉 変換が完了しました！")
                                    st.download_button(f"⬇️ ダウンロード：{out_stem}.csv",
                                                       data=to_csv_bytes(input_path),
                                                       file_name=out_stem + ".csv",
                                                       mime="text/csv")
                                elif out_fmt in ("JPEG", "PNG", "WebP"):
                                    images, err = to_images(input_path, out_fmt, dpi, tmpdir)
                                    if images:
                                        st.success(f"🎉 {len(images)} ページの画像化が完了しました！")
                                        if len(images) == 1:
                                            name, data = images[0]
                                            st.download_button(f"⬇️ ダウンロード：{name}",
                                                               data=data, file_name=name)
                                        else:
                                            zip_buf = io.BytesIO()
                                            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                                                for name, data in images:
                                                    zf.writestr(f"{out_stem}/{name}", data)
                                            zip_buf.seek(0)
                                            st.download_button(
                                                f"⬇️ すべてダウンロード（{len(images)} ページ） .zip",
                                                data=zip_buf.getvalue(),
                                                file_name=f"{out_stem}_images.zip",
                                                mime="application/zip")
                                    else:
                                        st.error(f"画像変換に失敗しました。\n```\n{err[-500:]}\n```")
                        except subprocess.TimeoutExpired:
                            st.error("⏱️ 変換がタイムアウトしました。")
                        except Exception as e:
                            st.error(f"エラーが発生しました：{e}")

# ── SNSサイズ変換 ─────────────────────────────────────────────────────────────
with tab_sns:
    SNS_PRESETS = {
        "Instagram / TikTok": [
            {"label": "正方形 1080×1080（フィード 1:1）",       "w": 1080, "h": 1080},
            {"label": "縦型 1080×1350（フィード 4:5）",         "w": 1080, "h": 1350},
            {"label": "リール・TikTok 1080×1920（縦型 9:16）",  "w": 1080, "h": 1920},
            {"label": "横型 1080×566（フィード 16:9）",         "w": 1080, "h": 566},
        ],
        "Twitter / X": [
            {"label": "横型 1200×675（投稿 16:9）",  "w": 1200, "h": 675},
            {"label": "正方形 1200×1200（投稿 1:1）", "w": 1200, "h": 1200},
        ],
        "YouTube": [
            {"label": "サムネイル 1280×720（16:9）",    "w": 1280, "h": 720},
            {"label": "ショート 1080×1920（縦型 9:16）", "w": 1080, "h": 1920},
            {"label": "通常動画 1920×1080（16:9）",     "w": 1920, "h": 1080},
        ],
        "Facebook / LINE": [
            {"label": "投稿 1200×630（16:9）",           "w": 1200, "h": 630},
            {"label": "カバー画像 820×312",               "w": 820,  "h": 312},
            {"label": "正方形 1200×1200（1:1）",         "w": 1200, "h": 1200},
            {"label": "LINEタイムライン 1040×1040（1:1）", "w": 1040, "h": 1040},
        ],
    }

    IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "heic", "heif", "avif", "bmp", "tiff", "tif"}
    VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
    SNS_ACCEPT = sorted(IMAGE_EXTS | VIDEO_EXTS)

    def sns_resize_image(img, target_w, target_h, mode, bg_color):
        img_w, img_h = img.size
        if mode == "crop":
            scale = max(target_w / img_w, target_h / img_h)
            new_w, new_h = round(img_w * scale), round(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - target_w) // 2
            top  = (new_h - target_h) // 2
            return img.crop((left, top, left + target_w, top + target_h))
        else:
            scale = min(target_w / img_w, target_h / img_h)
            new_w, new_h = round(img_w * scale), round(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            bg = Image.new("RGB", (target_w, target_h), bg_color)
            px = (target_w - new_w) // 2
            py = (target_h - new_h) // 2
            if img.mode == "RGBA":
                bg.paste(img, (px, py), mask=img.split()[3])
            else:
                bg.paste(img.convert("RGB"), (px, py))
            return bg

    def sns_resize_video(input_path, output_path, target_w, target_h, mode, bg_color):
        color = "black" if bg_color == (0, 0, 0) else "white"
        if mode == "crop":
            vf = (f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                  f"crop={target_w}:{target_h}")
        else:
            vf = (f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                  f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color={color}")
        cmd = ["ffmpeg", "-i", input_path, "-vf", vf,
               "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", "-y", output_path]
        return subprocess.run(cmd, capture_output=True, timeout=300)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # 設定UI
    col_p, col_s = st.columns([2, 3])
    with col_p:
        platform = st.selectbox("📱 プラットフォーム", list(SNS_PRESETS.keys()), key="sns_platform")
    presets = SNS_PRESETS[platform]
    with col_s:
        preset_label = st.selectbox("📐 サイズ", [p["label"] for p in presets], key="sns_preset")
    selected = next(p for p in presets if p["label"] == preset_label)
    target_w, target_h = selected["w"], selected["h"]

    st.markdown(
        f"<div style='background:#f3e8ff;border-radius:10px;padding:8px 14px;"
        f"color:#6d28d9;font-size:0.9rem;margin-bottom:8px;'>"
        f"📌 出力サイズ：<strong>{target_w} × {target_h} px</strong></div>",
        unsafe_allow_html=True)

    col_m, col_b = st.columns([2, 2])
    with col_m:
        mode = st.radio("✂️ サイズ調整方法",
                        ["クロップ（切り抜き）", "レターボックス（余白追加）"],
                        key="sns_mode",
                        help="クロップ：はみ出た部分を切り抜く／レターボックス：余白を追加してサイズを合わせる")
    trim_mode = "crop" if "クロップ" in mode else "letterbox"
    bg_color = (255, 255, 255)
    if trim_mode == "letterbox":
        with col_b:
            bg_sel = st.radio("🎨 余白の色", ["白", "黒"], key="sns_bg")
            bg_color = (255, 255, 255) if bg_sel == "白" else (0, 0, 0)

    st.divider()

    uploaded_sns = st.file_uploader("📂 画像または動画をアップロード",
                                    type=SNS_ACCEPT, accept_multiple_files=False,
                                    key="sns_uploader")

    if not uploaded_sns:
        step_guide(
            ["画像または動画を上の枠にドラッグ＆ドロップ（または「Upload」をクリック）",
             "プラットフォームとサイズを選ぶ",
             "サイズ調整方法（クロップ or レターボックス）を選ぶ",
             "「変換開始」ボタンを押す",
             "ダウンロードボタンから保存する"],
            "画像：JPEG / PNG / WebP / HEIC など　動画：MP4 / MOV / AVI / MKV など"
        )
        st.markdown("""
        <div style="background:#f3e8ff;border-radius:14px;padding:16px;margin-top:12px;border:1.5px solid #ddd6fe;">
          <p style="color:#7c3aed;font-weight:700;margin:0 0 8px;">✂️ 調整方法の違い</p>
          <div style="display:flex;gap:12px;">
            <div style="flex:1;background:#fdf4ff;border-radius:10px;padding:12px;border:1.5px solid #e9d5ff;">
              <p style="color:#7c3aed;font-weight:700;font-size:0.9rem;margin:0 0 4px;">クロップ（切り抜き）</p>
              <p style="color:#4c1d95;font-size:0.85rem;margin:0;">指定サイズに合わせて中央を切り抜く。余白なし・画像が途切れる場合あり。</p>
            </div>
            <div style="flex:1;background:#fdf4ff;border-radius:10px;padding:12px;border:1.5px solid #e9d5ff;">
              <p style="color:#7c3aed;font-weight:700;font-size:0.9rem;margin:0 0 4px;">レターボックス（余白追加）</p>
              <p style="color:#4c1d95;font-size:0.85rem;margin:0;">全体が収まるよう縮小し、余白（白or黒）を追加。画像が途切れない。</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        file_ext = Path(uploaded_sns.name).suffix.lower().lstrip(".")
        is_video = file_ext in VIDEO_EXTS
        file_type = "動画" if is_video else "画像"
        size_label = (f"{round(uploaded_sns.size/1024/1024, 1)} MB" if uploaded_sns.size > 1024*1024
                      else f"{round(uploaded_sns.size/1024, 1)} KB")
        st.markdown(selected_badge(
            f"{uploaded_sns.name} &nbsp; <span style='font-weight:400;'>{file_type}・{size_label}</span>"),
            unsafe_allow_html=True)

        img_out_fmt = "JPEG"
        if not is_video:
            img_out_fmt = st.selectbox("✨ 出力形式", ["JPEG", "PNG", "WebP"], key="sns_img_fmt")
        st.divider()

        if st.button("✨ 変換開始", type="primary", key="sns_convert"):
            with st.spinner(f"変換中... {target_w}×{target_h}px に調整しています"):
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        input_path = os.path.join(tmpdir, "input." + file_ext)
                        with open(input_path, "wb") as f:
                            f.write(uploaded_sns.getbuffer())
                        out_stem = Path(uploaded_sns.name).stem

                        if not is_video:
                            img = Image.open(input_path)
                            if img.mode not in ("RGB", "RGBA"):
                                img = img.convert("RGB")
                            result_img = sns_resize_image(img, target_w, target_h,
                                                          trim_mode, bg_color)
                            ext_map = {"JPEG": ".jpg", "PNG": ".png", "WebP": ".webp"}
                            pil_map = {"JPEG": "JPEG", "PNG": "PNG", "WebP": "WEBP"}
                            out_name = out_stem + f"_{target_w}x{target_h}" + ext_map[img_out_fmt]
                            buf = io.BytesIO()
                            if img_out_fmt == "JPEG":
                                result_img.convert("RGB").save(buf, pil_map[img_out_fmt],
                                                               quality=90, optimize=True)
                            else:
                                result_img.save(buf, pil_map[img_out_fmt])
                            buf.seek(0)
                            st.success(f"🎉 {target_w}×{target_h}px に変換しました！")
                            st.download_button(f"⬇️ ダウンロード：{out_name}",
                                               data=buf.getvalue(), file_name=out_name)
                        else:
                            if not ffmpeg_available():
                                st.error("FFmpegがインストールされていないため動画変換できません。")
                            else:
                                out_name = out_stem + f"_{target_w}x{target_h}.mp4"
                                output_path = os.path.join(tmpdir, out_name)
                                result = sns_resize_video(input_path, output_path,
                                                          target_w, target_h,
                                                          trim_mode, bg_color)
                                if result.returncode != 0:
                                    err = result.stderr.decode("utf-8", errors="replace")
                                    st.error(f"変換に失敗しました。\n```\n{err[-500:]}\n```")
                                else:
                                    with open(output_path, "rb") as f:
                                        out_data = f.read()
                                    st.success(f"🎉 {target_w}×{target_h}px に変換しました！")
                                    st.caption(f"出力サイズ：{round(len(out_data)/1024/1024, 1)} MB")
                                    st.download_button(f"⬇️ ダウンロード：{out_name}",
                                                       data=out_data, file_name=out_name)
                except subprocess.TimeoutExpired:
                    st.error("⏱️ 変換がタイムアウトしました。ファイルサイズを小さくしてお試しください。")
                except Exception as e:
                    st.error(f"エラーが発生しました：{e}")

# ── 文字消し ──────────────────────────────────────────────────────────────────
with tab_erase:
    # st_canvas の background_image を動かすために st.image.image_to_url が必要。
    # Streamlit 1.28+ でこのメソッドが削除されたため、なければ自前の base64 実装で補う。
    import base64 as _b64mod

    def _img_to_url_b64(image, width=-1, clamp=False, channels="RGB",
                        output_format="auto", image_id="", allow_emoji=False):
        _buf = io.BytesIO()
        if hasattr(image, "save"):
            image.save(_buf, format="PNG")
        _buf.seek(0)
        return "data:image/png;base64," + _b64mod.b64encode(_buf.getvalue()).decode()

    _st_iurl = None
    for _mod_path in (
        "streamlit.elements.image",
        "streamlit.elements.lib.image",
    ):
        try:
            import importlib as _il
            _m = _il.import_module(_mod_path)
            _st_iurl = getattr(_m, "image_to_url", None)
            if _st_iurl is not None:
                break
        except Exception:
            pass
    if _st_iurl is None:
        _st_iurl = _img_to_url_b64

    if not hasattr(st.image, "image_to_url"):
        _orig_st_image = st.image
        class _PatchedImg:
            image_to_url = staticmethod(_st_iurl)
            def __call__(self, *a, **k):
                return _orig_st_image(*a, **k)
            def __getattr__(self, n):
                return getattr(_orig_st_image, n)
        st.image = _PatchedImg()
    _bg_ok = True

    from streamlit_drawable_canvas import st_canvas
    import cv2
    import numpy as np
    from PIL import ImageDraw

    ERASE_INPUT = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif"]

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    uploaded_erase = st.file_uploader(
        "📂 画像をアップロード",
        type=ERASE_INPUT,
        accept_multiple_files=False,
        key="erase_uploader",
    )

    if not uploaded_erase:
        step_guide(
            ["画像ファイルを上の枠にドラッグ＆ドロップ（または「Upload」をクリック）",
             "ブラシサイズを調整する",
             "消したい文字・透かし・ロゴの上を赤くなぞる",
             "「消去する」ボタンを押す",
             "ダウンロードボタンから保存する"],
            "JPEG / PNG / WebP / BMP / TIFF"
        )
        st.markdown("""
        <div style="background:#fff7ed;border-radius:14px;padding:16px;margin-top:12px;border:1.5px solid #fed7aa;">
          <p style="color:#92400e;font-weight:700;margin:0 0 8px;">⚠️ 得意・苦手なケース</p>
          <div style="display:flex;gap:12px;">
            <div style="flex:1;background:#f0fdf4;border-radius:10px;padding:12px;border:1.5px solid #6ee7b7;">
              <p style="color:#065f46;font-weight:700;font-size:0.88rem;margin:0 0 4px;">✅ 得意</p>
              <p style="color:#065f46;font-size:0.83rem;margin:0;">白・単色の背景にある文字、透かし、ロゴ</p>
            </div>
            <div style="flex:1;background:#fef2f2;border-radius:10px;padding:12px;border:1.5px solid #fca5a5;">
              <p style="color:#991b1b;font-weight:700;font-size:0.88rem;margin:0 0 4px;">❌ 苦手</p>
              <p style="color:#991b1b;font-size:0.83rem;margin:0;">写真など複雑な背景の上にある文字（精度が下がります）</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        orig_img = Image.open(uploaded_erase).convert("RGB")
        orig_w, orig_h = orig_img.size

        MAX_W, MAX_H = 680, 560
        scale = min(1.0, MAX_W / orig_w, MAX_H / orig_h)
        disp_w = round(orig_w * scale)
        disp_h = round(orig_h * scale)
        disp_img = orig_img.resize((disp_w, disp_h), Image.LANCZOS)

        col_brush, col_radius = st.columns(2)
        with col_brush:
            brush_size = st.slider("🖌️ ブラシサイズ", min_value=5, max_value=80, value=20,
                                   key="erase_brush")
        with col_radius:
            inpaint_r = st.slider("🔧 補完の強さ", min_value=3, max_value=30, value=10,
                                  help="値が大きいほど広範囲を参照して補完します",
                                  key="erase_radius")

        st.markdown(
            "<p style='color:#7c3aed;font-size:0.88rem;margin:6px 0 2px;'>"
            "📌 消したい部分を<strong>赤くなぞって</strong>から「消去する」を押してください。</p>",
            unsafe_allow_html=True)

        if "erase_reset" not in st.session_state:
            st.session_state["erase_reset"] = 0

        canvas_result = st_canvas(
            stroke_width=brush_size,
            stroke_color="rgba(255, 0, 0, 0.85)",
            background_image=disp_img if _bg_ok else None,
            background_color="#000000",
            drawing_mode="freedraw",
            update_streamlit=True,
            height=disp_h,
            width=disp_w,
            key=f"erase_canvas_{st.session_state['erase_reset']}",
        )

        col_btn, col_reset = st.columns([3, 1])
        with col_reset:
            if st.button("🔄 なぞりをリセット", key="erase_reset_btn"):
                st.session_state["erase_reset"] += 1
                st.rerun()

        st.divider()

        with col_btn:
            do_erase = st.button("✨ 消去する", type="primary", key="erase_btn")

        if do_erase:
            has_objects = (canvas_result.json_data and
                           canvas_result.json_data.get("objects"))
            if not has_objects:
                st.warning("消去する範囲をなぞってから「消去する」を押してください。")
            else:
                with st.spinner("消去中..."):
                    # json_data のパスからマスクを作成（background_image があっても正確に動く）
                    mask_img = Image.new("L", (disp_w, disp_h), 0)
                    draw_mask = ImageDraw.Draw(mask_img)
                    for obj in (canvas_result.json_data or {}).get("objects", []):
                        if obj.get("type") == "path":
                            sw = max(1, int(obj.get("strokeWidth", brush_size)))
                            pts = []
                            for cmd in obj.get("path", []):
                                if cmd[0] in ("M", "L"):
                                    pts.append((cmd[1], cmd[2]))
                                elif cmd[0] == "Q":
                                    pts.append((cmd[3], cmd[4]))
                                elif cmd[0] == "C":
                                    pts.append((cmd[5], cmd[6]))
                            if len(pts) >= 2:
                                draw_mask.line(pts, fill=255, width=sw)
                            elif len(pts) == 1:
                                r = sw // 2
                                x, y = pts[0]
                                draw_mask.ellipse([x-r, y-r, x+r, y+r], fill=255)

                    # 元サイズにスケール
                    mask_orig = mask_img.resize((orig_w, orig_h), Image.NEAREST)
                    mask_arr = np.array(mask_orig)

                    # マスクを少し膨張させて確実に文字をカバー
                    kernel = np.ones((5, 5), np.uint8)
                    mask_arr = cv2.dilate(mask_arr, kernel, iterations=2)

                    # インペインティング
                    img_arr = np.array(orig_img)
                    result_arr = cv2.inpaint(img_arr, mask_arr, inpaintRadius=inpaint_r,
                                             flags=cv2.INPAINT_TELEA)
                    result_img = Image.fromarray(result_arr)

                    st.success("🎉 消去が完了しました！")
                    st.image(result_img, caption="消去後", use_container_width=True)

                    buf = io.BytesIO()
                    result_img.save(buf, "PNG")
                    buf.seek(0)
                    out_name = Path(uploaded_erase.name).stem + "_erased.png"
                    st.download_button(f"⬇️ ダウンロード：{out_name}",
                                       data=buf.getvalue(), file_name=out_name)
