import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

SUPPORTED_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

OUTPUT_FORMATS = {
    "JPEG": {"ext": ".jpg",  "pil": "JPEG", "alpha": False, "has_quality": True},
    "PNG":  {"ext": ".png",  "pil": "PNG",  "alpha": True,  "has_quality": False},
    "WebP": {"ext": ".webp", "pil": "WEBP", "alpha": True,  "has_quality": True},
    "BMP":  {"ext": ".bmp",  "pil": "BMP",  "alpha": False, "has_quality": False},
    "TIFF": {"ext": ".tif",  "pil": "TIFF", "alpha": True,  "has_quality": False},
}

BG = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT = "#7c6af7"
ACCENT_HOVER = "#9580ff"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
SUCCESS = "#a6e3a1"
ERROR = "#f38ba8"
WARN = "#f9e2af"

FILETYPES = [
    ("対応画像ファイル", "*.heic *.HEIC *.heif *.HEIF *.jpg *.jpeg *.JPG *.JPEG *.png *.PNG *.webp *.WEBP *.bmp *.BMP *.tiff *.tif"),
    ("HEIC/HEIF", "*.heic *.HEIC *.heif *.HEIF"),
    ("JPEG", "*.jpg *.jpeg *.JPG *.JPEG"),
    ("PNG", "*.png *.PNG"),
    ("WebP", "*.webp *.WEBP"),
    ("すべて", "*.*"),
]


class FileItem:
    def __init__(self, path: Path):
        self.path = path
        self.status = "待機中"
        self.status_color = TEXT_DIM


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("画像変換ツール")
        self.geometry("700x600")
        self.minsize(580, 500)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.files: list[FileItem] = []
        self.output_dir = tk.StringVar(value="")
        self.quality = tk.IntVar(value=85)
        self.out_format = tk.StringVar(value="JPEG")
        self.converting = False

        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 0))
        tk.Label(header, text="画像変換ツール", font=("Yu Gothic UI", 16, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(12, 0))
        self._btn(btn_row, "ファイル追加", self._add_files).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "フォルダ追加", self._add_folder).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "リストをクリア", self._clear_list, fg=TEXT_DIM).pack(side="right")

        # file list
        list_frame = tk.Frame(self, bg=SURFACE, bd=0)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(list_frame, bg=SURFACE, highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.list_inner = tk.Frame(self.canvas, bg=SURFACE)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        self.list_inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._show_empty()

        # output format
        fmt_frame = tk.Frame(self, bg=BG)
        fmt_frame.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(fmt_frame, text="変換形式:", font=("Yu Gothic UI", 10),
                 bg=BG, fg=TEXT_DIM, width=8, anchor="w").pack(side="left")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TCombobox",
                        fieldbackground=SURFACE, background=SURFACE,
                        foreground=TEXT, selectbackground=ACCENT,
                        arrowcolor=TEXT)
        fmt_combo = ttk.Combobox(fmt_frame, textvariable=self.out_format,
                                 values=list(OUTPUT_FORMATS.keys()),
                                 state="readonly", width=10,
                                 style="Dark.TCombobox",
                                 font=("Yu Gothic UI", 10))
        fmt_combo.pack(side="left", padx=(4, 0))
        fmt_combo.bind("<<ComboboxSelected>>", self._on_format_change)

        self.fmt_note = tk.Label(fmt_frame, text="", font=("Yu Gothic UI", 9),
                                 bg=BG, fg=TEXT_DIM)
        self.fmt_note.pack(side="left", padx=(12, 0))

        # output dir
        out_frame = tk.Frame(self, bg=BG)
        out_frame.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(out_frame, text="出力先:", font=("Yu Gothic UI", 10),
                 bg=BG, fg=TEXT_DIM, width=8, anchor="w").pack(side="left")
        tk.Entry(out_frame, textvariable=self.output_dir,
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Yu Gothic UI", 10), bd=4).pack(
            side="left", fill="x", expand=True, padx=(4, 8))
        self._btn(out_frame, "選択", self._choose_output, small=True).pack(side="left")

        # quality
        self.q_frame = tk.Frame(self, bg=BG)
        self.q_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.q_label_key = tk.Label(self.q_frame, text="品質:", font=("Yu Gothic UI", 10),
                                    bg=BG, fg=TEXT_DIM, width=8, anchor="w")
        self.q_label_key.pack(side="left")
        self.q_label_val = tk.Label(self.q_frame, text=f"{self.quality.get()}%",
                                    font=("Yu Gothic UI", 10, "bold"), bg=BG, fg=ACCENT, width=5)
        self.q_label_val.pack(side="right")
        style.configure("Accent.Horizontal.TScale", background=BG)
        self.q_slider = ttk.Scale(self.q_frame, from_=40, to=100, variable=self.quality,
                                  orient="horizontal", command=self._on_quality_change)
        self.q_slider.pack(side="left", fill="x", expand=True, padx=(4, 8))

        # progress
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label = tk.Label(self, text="", font=("Yu Gothic UI", 9),
                                       bg=BG, fg=TEXT_DIM)
        self.progress_label.pack(padx=20, anchor="w")
        style.configure("Accent.Horizontal.TProgressbar",
                        troughcolor=SURFACE, background=ACCENT, thickness=8)
        ttk.Progressbar(self, style="Accent.Horizontal.TProgressbar",
                        variable=self.progress_var, maximum=100).pack(
            fill="x", padx=20, pady=(2, 10))

        self.convert_btn = tk.Button(
            self, text="変換開始", font=("Yu Gothic UI", 13, "bold"),
            bg=ACCENT, fg="#ffffff", activebackground=ACCENT_HOVER,
            activeforeground="#ffffff", relief="flat", bd=0,
            cursor="hand2", pady=10, command=self._start_convert
        )
        self.convert_btn.pack(fill="x", padx=20, pady=(0, 18))

        self._on_format_change()

    def _btn(self, parent, text, cmd, fg=TEXT, small=False):
        return tk.Button(parent, text=text, font=("Yu Gothic UI", 9 if small else 10),
                         bg=SURFACE, fg=fg, activebackground="#3a3a5e",
                         activeforeground=TEXT, relief="flat", bd=0,
                         cursor="hand2", padx=10, pady=5, command=cmd)

    # ── canvas ──────────────────────────────────────────────────────────────

    def _on_frame_configure(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # ── format change ────────────────────────────────────────────────────────

    def _on_format_change(self, _=None):
        fmt = self.out_format.get()
        info = OUTPUT_FORMATS.get(fmt, {})
        has_quality = info.get("has_quality", True)

        for w in self.q_frame.winfo_children():
            w.configure(state="normal" if has_quality else "disabled")

        notes = {
            "JPEG": "透過なし・圧縮あり",
            "PNG":  "透過対応・可逆圧縮",
            "WebP": "透過対応・高圧縮",
            "BMP":  "透過なし・無圧縮",
            "TIFF": "透過対応・無圧縮",
        }
        self.fmt_note.config(text=notes.get(fmt, ""))

    # ── actions ─────────────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="画像ファイルを選択", filetypes=FILETYPES)
        self._add_paths([Path(p) for p in paths])

    def _add_folder(self):
        folder = filedialog.askdirectory(title="フォルダを選択")
        if not folder:
            return
        paths = [p for p in Path(folder).rglob("*") if p.suffix.lower() in SUPPORTED_EXTS]
        if not paths:
            messagebox.showinfo("情報", "対応する画像ファイルが見つかりませんでした。")
            return
        self._add_paths(paths)

    def _add_paths(self, paths: list[Path]):
        existing = {f.path for f in self.files}
        for p in paths:
            if p not in existing:
                self.files.append(FileItem(p))
        self._refresh_list()

    def _clear_list(self):
        if self.converting:
            return
        self.files.clear()
        self._refresh_list()

    def _choose_output(self):
        folder = filedialog.askdirectory(title="出力先フォルダを選択")
        if folder:
            self.output_dir.set(folder)

    def _on_quality_change(self, _=None):
        self.q_label_val.config(text=f"{self.quality.get()}%")

    # ── list ────────────────────────────────────────────────────────────────

    def _show_empty(self):
        tk.Label(self.list_inner,
                 text="画像ファイルをここに追加してください\n（対応形式: HEIC / JPEG / PNG / WebP / BMP / TIFF）",
                 font=("Yu Gothic UI", 11), bg=SURFACE, fg=TEXT_DIM,
                 justify="center").pack(expand=True, pady=60)

    def _refresh_list(self):
        for w in self.list_inner.winfo_children():
            w.destroy()
        if not self.files:
            self._show_empty()
            return
        for i, item in enumerate(self.files):
            row_bg = SURFACE if i % 2 == 0 else "#252538"
            row = tk.Frame(self.list_inner, bg=row_bg)
            row.pack(fill="x")
            ext_tag = item.path.suffix.upper().lstrip(".")
            tk.Label(row, text=f"[{ext_tag}]", font=("Yu Gothic UI", 8),
                     bg=row_bg, fg=ACCENT, width=5).pack(side="left", padx=(8, 0), pady=5)
            tk.Label(row, text=item.path.name, font=("Yu Gothic UI", 10),
                     bg=row_bg, fg=TEXT, anchor="w").pack(side="left", padx=(4, 0), pady=5)
            tk.Label(row, text=item.status, font=("Yu Gothic UI", 9),
                     bg=row_bg, fg=item.status_color, anchor="e").pack(side="right", padx=10)

    def _update_item_status(self, index: int, status: str, color: str):
        self.files[index].status = status
        self.files[index].status_color = color
        self.after(0, self._refresh_list)

    # ── conversion ───────────────────────────────────────────────────────────

    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            messagebox.showwarning("警告", "変換するファイルを追加してください。")
            return
        out = self.output_dir.get().strip()
        if out and not os.path.isdir(out):
            messagebox.showerror("エラー", "出力先フォルダが存在しません。")
            return

        self.converting = True
        self.convert_btn.config(state="disabled", text="変換中...")
        self.progress_var.set(0)
        for item in self.files:
            item.status = "待機中"
            item.status_color = TEXT_DIM
        self._refresh_list()

        fmt = self.out_format.get()
        threading.Thread(target=self._convert_all, args=(out, fmt), daemon=True).start()

    def _convert_all(self, out_dir: str, fmt: str):
        total = len(self.files)
        success = 0
        failed = 0
        info = OUTPUT_FORMATS[fmt]
        quality = self.quality.get()

        for i, item in enumerate(self.files):
            self.after(0, lambda i=i: self._update_item_status(i, "変換中...", WARN))
            try:
                dest_dir = Path(out_dir) if out_dir else item.path.parent
                dest = dest_dir / (item.path.stem + info["ext"])

                with Image.open(item.path) as img:
                    if not info["alpha"] and img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        src = img.convert("RGBA") if img.mode != "RGBA" else img
                        bg.paste(src, mask=src.split()[3])
                        img_out = bg
                    else:
                        img_out = img.convert("RGBA") if info["alpha"] and img.mode == "P" else img

                    if not info["alpha"] and img_out.mode not in ("RGB", "L"):
                        img_out = img_out.convert("RGB")
                    elif info["alpha"] and img_out.mode not in ("RGB", "RGBA", "L", "LA"):
                        img_out = img_out.convert("RGBA")

                    save_kwargs = {}
                    if info["has_quality"]:
                        save_kwargs["quality"] = quality
                    if fmt == "JPEG":
                        save_kwargs["optimize"] = True

                    img_out.save(dest, info["pil"], **save_kwargs)

                self.after(0, lambda i=i: self._update_item_status(i, "完了", SUCCESS))
                success += 1
            except Exception as e:
                self.after(0, lambda i=i, e=e: self._update_item_status(
                    i, f"失敗: {type(e).__name__}", ERROR))
                failed += 1

            progress = (i + 1) / total * 100
            self.after(0, lambda p=progress, c=i + 1, t=total:
                       self._set_progress(p, f"{c} / {t} 処理中"))

        self.after(0, lambda: self._on_complete(success, failed))

    def _set_progress(self, value: float, label: str):
        self.progress_var.set(value)
        self.progress_label.config(text=label)

    def _on_complete(self, success: int, failed: int):
        self.converting = False
        self.convert_btn.config(state="normal", text="変換開始")
        self.progress_label.config(text=f"完了: {success} 件成功 / {failed} 件失敗")
        self.progress_var.set(100)
        if failed == 0:
            messagebox.showinfo("完了", f"{success} 件のファイルを変換しました。")
        else:
            messagebox.showwarning("完了",
                                   f"成功: {success} 件\n失敗: {failed} 件\n失敗したファイルを確認してください。")


if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()
