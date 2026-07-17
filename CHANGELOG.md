# 作業ログ

## 2026-07-17

### PDF変換のOCR対応
- **PDF→DOCX**：文字情報を持たないスキャン画像PDFを自動検出し、OCR（Tesseract）で文字認識してWordに書き込むように変更。以前は画像がそのまま貼り付けられていた。
- **PDF→TXT**：同様にスキャン画像PDFをOCRでテキスト抽出できるように対応。
- **PDF→PPTX**：各ページを丸ごと画像化してスライドに貼り付ける方式から、テキストを抽出してスライドのテキストボックスに書き込む方式に変更（通常PDFは`pdfplumber`、スキャン画像PDFはOCR）。
- OCRは**横書き・縦書きの両方を試し、認識信頼度が高い方を自動採用**（縦書き文書が横書きとして誤読され文字化けする問題を解消）。
- 日本語OCR特有の文字間の余分なスペースを後処理で除去。

### 対応環境
- **EXE版**（`converter.py`）：縦書き用言語データ（`jpn_vert.traineddata`）を`tessdata/`フォルダに同梱し、管理者権限やパス内の日本語・スペースに影響されない形で組み込み。pytesseractは使わず`tesseract.exe`を直接subprocess呼び出しする方式に変更（Windows特有のパス関連の不具合を回避するため）。
- **Web版**（`app.py` / `webapp/app.py`）：Streamlit CloudのDebian環境向けに`packages.txt`へ`tesseract-ocr`・`tesseract-ocr-jpn`・`tesseract-ocr-jpn-vert`を追加。

### 整理
- 旧名称時代の古いビルド（`dist/画像変換ツール.exe`、`画像変換ツール.zip`）を削除。
- 使われていない`eraser_canvas/`（削除済みのテキスト消しゴム機能の残骸）を削除。
- `docs/使い方ガイド.html`を現行の3タブ構成（画像変換・動画変換・文書変換）とOCR対応の内容に全面更新。

### 関連コミット
- `f783dd6` Add OCR support for scanned PDF to DOCX conversion
- `25d4138` Clean up stale files and update usage guide
- `aa34644` Add OCR support for scanned PDF to TXT conversion
- `594d544` Change PDF to PPTX conversion from page images to real text
