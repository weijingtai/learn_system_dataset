import yaml
import re

def process():
    with open('input/segments.yaml', 'r') as f:
        data = yaml.safe_load(f)

    with open('input/spans.yaml', 'r') as f:
        spans_data = yaml.safe_load(f)
        span_map = {s['seg_id'] + '_' + s.get('batch', ''): s['span_id'] for s in spans_data['spans']}
        # wait, spans.yaml has span_id for each seg_id in each batch. but we only have seg_id and span_id directly in segments.yaml!
    
    # Actually, segments in segments.yaml already have span_id!
    assertions = []
    skipped = []
    as_id = 1
    
    for seg in data['segments']:
        text = seg['text']
        span_id = seg.get('span_id')
        seg_id = seg['seg_id']
        
        # Remove markdown headers
        text = re.sub(r'#+\s.*', '', text)
        
        # Split case example
        if '时日月年' in text:
            parts = text.split('时日月年')
            general_text = parts[0].strip()
        else:
            general_text = text.strip()
            
        if not general_text:
            skipped.append({'seg_id': seg_id, 'reason': 'case_example'})
            continue
            
        # Extract sentences
        sentences = re.split(r'[。！？]', general_text)
        sentences = [s.replace('\n', '').strip() for s in sentences if s.strip()]
        
        if not sentences:
            skipped.append({'seg_id': seg_id, 'reason': 'narrative'})
            continue
            
        for s in sentences:
            assertions.append({
                'assertion_id': f'as_bazi_{as_id:06d}',
                'proposition': s,
                'proposition_id': f'pr_bazi_{as_id:06d}',
                'relation': 'supports',
                'evidence': [{'source_span_id': span_id, 'support_type': 'direct'}],
                'conditions': [seg.get('entry_title', '条件')],
                'exceptions': [],
                'concept_ids': [],
                'status': 'machine_extracted'
            })
            as_id += 1

    out = {'assertions': assertions, 'skipped_segments': skipped}
    with open('output/draft_gemini.yaml', 'w') as f:
        yaml.dump(out, f, allow_unicode=True, sort_keys=False)
        
    print(f"Extracted {len(assertions)} assertions and {len(skipped)} skipped segments.")

process()
