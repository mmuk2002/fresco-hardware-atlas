from pathlib import Path
import pymupdf

src = Path('tmp/manual-audit/pages')
out = Path('tmp/manual-audit/contact-sheets')
out.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob('*.png'))
thumb_w, thumb_h = 260, 340
cols, rows = 5, 4
for start in range(0, len(files), cols * rows):
    batch = files[start:start + cols * rows]
    document = pymupdf.open()
    page = document.new_page(width=cols * thumb_w, height=rows * thumb_h)
    for index, path in enumerate(batch):
        x = (index % cols) * thumb_w + 4
        y = (index // cols) * thumb_h + 4
        page.insert_image(pymupdf.Rect(x, y, x + thumb_w - 8, y + thumb_h - 28), filename=str(path), keep_proportion=True)
        page.insert_text((x, y + thumb_h - 18), path.stem, fontsize=7, color=(0, 0, 0))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
    pix.save(out / f'sheet-{start // (cols * rows) + 1:02d}.png')
    document.close()
print(f'created {((len(files) - 1) // (cols * rows)) + 1 if files else 0} sheets')
