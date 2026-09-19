"""Prepare and record an actual browser walkthrough into a local MP4.

Windows narration: run --prepare, then scripts/demo_voice.ps1; launch the demo
store on port 8002; run --record. Requires Playwright, Edge/Chromium and FFmpeg.
The review store is isolated from real corrections. Narration is synthetic.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEGMENTS = [
    ('Source-linked hardware extraction', 'This is Hardware Atlas, a local application for the Fresco hardware sets challenge. It extracts door hardware into structured records while keeping every set linked to its original PDF page. The system runs without an API key or external document upload. This walkthrough uses actual extraction results from three supplied specifications, with different layouts and a page continuation.'),
    ('Audit first: 43 PDFs, 21 projects, 17,637 pages', 'I started by inventorying the complete download: forty three PDFs, twenty one project folders, and seventeen thousand six hundred thirty seven pages. Those files are not all independent hardware schedules. Some are door and frame requirements, some are indexes, and others repeat a schedule inside a larger manual. The repository includes a file by file audit, so processing coverage is separate from measured extraction accuracy.'),
    ('Example 1 / Centered and wrapped cells', 'The first example is J C Ryan, physical PDF page twenty eight. Set one point zero contains centered, multiline catalog cells. The parser keeps the finish instructions inside the catalog text and assigns Pemko to the manufacturer field. There is no separate finish column here, so the finish remains empty. The green source region shows exactly where this set came from, using PDF coordinates rather than a guessed screenshot position.'),
    ('Missing quantity stays null', 'Set two point zero shows another important case. The hinge quantity is absent in the source. The output leaves it null instead of assuming one. A surface closer has a description split above and below its quantity baseline; those lines remain one component. Column roles are established before interpreting short codes. In other documents, this prevents P E from being treated as a finish when its column is actually manufacturers.'),
    ('Correct, save, and retain the original extraction', 'The review interface lets a person correct a field, add or remove rows, and save the result. Here I add a review note and save it. The original machine extraction is kept separately from the correction layer, with an audit history. Switching away and returning preserves the saved correction. JSON and C S V exports include the reviewed values. Confidence badges are heuristic review aids, not calibrated probabilities.'),
    ('Example 2 / A different table schema', 'The second example is Roselle Library, page seventeen. This is a landscape table with merged set cells. Its quantity column comes after a combined manufacturer and product column. A dedicated geometric table path identifies the cell boundaries and separates the manufacturer from the product at the printed separator. The same output contract works for this table and the previous list layout. Blank or dashed quantities stay null.'),
    ('Example 3 / One set across two pages', 'The third example is Forest Park School. Set one starts on physical page two hundred sixty two and continues on page two hundred sixty three. The result is one set with five components and two source regions. Moving between pages makes both regions visible. The next specification section is a hard stop, preventing the final hardware set from absorbing unrelated glazing requirements. Explicit not used sets are retained as empty records.'),
    ('Measured holdout across eight layouts', 'After freezing the extractor, I randomly selected eight schedule pages from template families absent from development labels and transcribed the rendered source before looking at predictions. The first full corpus score found fourteen of fourteen labeled sets and all one hundred twenty six expected components. One hundred twenty three of one hundred twenty six annotated rows were exact across the labeled fields, above ninety seven percent. There were three extra component rows and zero manufacturer and finish swaps. Independent PDF location checks found all seventeen printed headings and placed a source description word inside all one hundred twenty six component boxes. These are sample results, not a guarantee for all forty three files.'),
    ('Run locally / Review / Export', 'The submission includes setup instructions, a command line extractor, full corpus processing, the local review application, source annotations, and reproducible evaluation scripts. Start the app with python dash m hardware sets serve, then open localhost port eight thousand. Human corrections and heuristic confidence help with uncommon revisions, OCR, and noisy watermarks. Same page catalog code expansion is available when an explicit lookup appears, with the original code and its source box preserved. Use the supplied holdout report to assess both the strong measured accuracy and its limits.'),
]


def prepare(source: Path):
    from hardware_sets.extract import extract_pdf
    from hardware_sets.storage import DocumentStore
    folder = Path('output/demo')
    folder.mkdir(parents=True, exist_ok=True)
    store = DocumentStore('tmp/demo-store')
    selections = {
        'ryan': ('JC Ryan 2/087100 - Door Hardware-6.pdf', [28]),
        'roselle': ('Roselle Public Library/087100_FL_-_Door_Hardware_IFB_REVISED.pdf', [17]),
        'forest': ('Forest Park School/Project Manual (1).pdf', [262,263]),
    }
    records = {}
    for name, (relative, pages) in selections.items():
        pdf = source / relative
        document = store.import_pdf(pdf, project=pdf.parent.name)
        result = store.save_result(document['id'], extract_pdf(pdf, pages=pages))
        records[name] = result.model_dump(mode='json')
    (folder/'documents.json').write_text(json.dumps(records), encoding='utf-8')
    (folder/'narration.json').write_text(json.dumps([{'title':t,'text':s} for t,s in SEGMENTS], indent=2), encoding='utf-8')
    print('Prepared demo store and narration.', flush=True)


def record(url: str):
    from playwright.sync_api import sync_playwright, expect
    folder = Path('output/demo')
    records = json.loads((folder/'documents.json').read_text(encoding='utf-8'))
    audio_parts = []
    for index in range(len(SEGMENTS)):
        with wave.open(str(folder/f'voice-{index}.wav'), 'rb') as audio:
            audio_parts.append((audio.getparams(), audio.readframes(audio.getnframes())))
    rate = audio_parts[0][0].framerate
    sample_width = audio_parts[0][0].sampwidth
    channels = audio_parts[0][0].nchannels
    durations = [len(data)/(rate*sample_width*channels) for _,data in audio_parts]
    with wave.open(str(folder/'narration.wav'),'wb') as audio:
        audio.setparams(audio_parts[0][0])
        for _, data in audio_parts:
            audio.writeframes(data)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,channel='msedge')
        context=browser.new_context(viewport={'width':1600,'height':1000},record_video_dir=str(folder/'raw'),record_video_size={'width':1600,'height':1000})
        page=context.new_page()
        page.goto(url,wait_until='networkidle')
        def select(document, number):
            page.get_by_title(document['name'],exact=True).click()
            target=next(s for s in document['sets'] if s['set_number']==number)
            page.locator(f'[data-set-id="{target["id"]}"]').click()
            page.wait_for_function("document.querySelector('#source-image').naturalWidth > 0")
            page.evaluate('window.scrollTo(0,0)')
        select(records['ryan'],'1.0')
        page.evaluate("""() => { const el=document.createElement('div');el.id='demo-caption';el.style.cssText='position:fixed;bottom:0;left:0;right:0;background:#153f36;color:#fff;padding:18px 32px;font:600 20px Segoe UI;z-index:99999;box-shadow:0 -3px 18px #0002;';document.body.append(el); }""")
        narration_start=time.monotonic()
        for index, ((title,_), duration) in enumerate(zip(SEGMENTS,durations)):
            start=time.monotonic()
            page.locator('#demo-caption').inner_text()
            page.evaluate('(text)=>document.getElementById("demo-caption").textContent=text',f'{index+1:02d}  /  {title}    ·    Synthetic narration / actual local app')
            print(f'Segment {index+1}/{len(SEGMENTS)}: {duration:.1f}s - {title}',flush=True)
            if index==2:
                select(records['ryan'],'1.0')
            elif index==3:
                select(records['ryan'],'2.0')
                page.locator('[data-field="qty"]').first.focus()
            elif index==4:
                page.locator('[data-field="notes"]').first.fill('Reviewed against source: quantity not specified; validated in eight-family holdout.')
                with page.expect_response(lambda response: response.request.method == 'PUT'):
                    page.locator('#save-button').click()
                expect(page.locator('#save-button')).to_be_disabled()
                select(records['ryan'],'1.0')
                select(records['ryan'],'2.0')
                page.locator('#export-button').click()
            elif index==5:
                page.locator('#export-button').click()
                select(records['roselle'],'7.1')
            elif index==6:
                select(records['forest'],'1')
                page.wait_for_timeout(4000)
                page.locator('#page-select').select_option('263')
            elif index==7:
                page.evaluate('window.scrollTo(0,0)')
            elif index==8:
                page.locator('#export-button').click()
            page.screenshot(path=str(folder/f'chapter-{index+1}.png'))
            remaining=duration-(time.monotonic()-start)
            if remaining>0:
                page.wait_for_timeout(remaining*1000)
        video=page.video
        context.close()
        raw=video.path()
        browser.close()
    # Browser startup precedes narration; trim that interval to align the voice.
    # Playwright starts recording when the page is created, before navigation.
    probe=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-of','json',str(raw)]))
    offset=max(0,float(probe['format']['duration'])-sum(durations))
    subprocess.run(['ffmpeg','-y','-ss',str(offset),'-i',str(raw),'-i',str(folder/'narration.wav'),
        '-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
        '-shortest','-movflags','+faststart',str(folder/'hardware-atlas-demo.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    print(f'Created {folder / "hardware-atlas-demo.mp4"} ({sum(durations):.1f} seconds).',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--record',action='store_true')
    parser.add_argument('--source',type=Path,default=Path('Fresco Coding Challenge (Hardware Sets)'))
    parser.add_argument('--url',default='http://127.0.0.1:8002')
    args=parser.parse_args()
    if args.prepare: prepare(args.source)
    if args.record: record(args.url)
