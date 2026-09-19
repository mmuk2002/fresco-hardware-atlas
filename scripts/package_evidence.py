"""Publish reproducible, source-relative evidence from completed local runs."""
import json
from pathlib import Path
import shutil

from hardware_sets.models import ExtractionResult


def main():
    output = Path('docs/validation')
    output.mkdir(parents=True, exist_ok=True)
    Path('docs/output.schema.json').write_text(json.dumps(ExtractionResult.model_json_schema(), indent=2), encoding='utf-8')
    for name in ('evaluation-development.json', 'evaluation-project-sample.json'):
        shutil.copyfile(Path('output')/name, output/name)
    summary=json.loads(Path('output/corpus/summary.json').read_text(encoding='utf-8'))
    summary.pop('source_root', None)
    for document in summary['documents']:
        document.pop('document_id', None)
    (output/'corpus-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    example_doc=next(d for d in summary['documents'] if d['source_path'].startswith('Forest Park'))
    result=json.loads((Path('output/corpus')/example_doc['output_file']).read_text(encoding='utf-8'))
    example={'source_path':example_doc['source_path'],'coordinate_system':'PDF points, top-left origin; one-based physical pages',
             'set':result['sets'][0]}
    Path('examples').mkdir(exist_ok=True)
    Path('examples/example-set.json').write_text(json.dumps(example, indent=2), encoding='utf-8')
    print('Packaged schema, example, sample metrics and corpus summary.')


if __name__=='__main__':
    main()
