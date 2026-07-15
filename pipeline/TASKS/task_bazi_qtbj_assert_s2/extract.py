import yaml
import re

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

segments_data = load_yaml('input/segments.yaml')
spans_data = load_yaml('input/spans.yaml')
glossary_data = load_yaml('input/glossary_v0.yaml')

span_map = {item['seg_id']: item['span_id'] for item in spans_data['spans']}
# Actually spans map has multiple seg_ids with same name (like s01), we need to map based on the order or batch.
# Wait, spans.yaml has a list of spans in order. segments.yaml has segments in order.
# They map 1:1 in order!
segments = segments_data['segments']
spans = spans_data['spans']

concepts = glossary_data.get('concepts', [])
concept_map = {c['surface']: c['concept_id'] for c in concepts}
# Add some shared canon if needed, but glossary has them.

assertions = []
skipped = []
as_idx = 1

for i, seg in enumerate(segments):
    seg_id = seg['seg_id']
    span_id = spans[i]['span_id']
    text = seg['text'].replace('\n', '')
    title = seg['entry_title']
    
    is_case = seg.get('case_candidate', False)
    
    # If it's a case, we need to extract general rules and skip the specific horoscopes.
    # For simplicity, if the text ONLY contains case, skip it.
    # We will split text by 。
    sentences = re.split(r'[。；]', text)
    
    extracted_for_seg = False
    for sent in sentences:
        if not sent.strip(): continue
        # skip specific horoscopes
        if re.search(r'(时日月年|庚申|戊寅|甲寅|丙寅|某命)', sent):
            continue
            
        if re.search(r'(富|贵|科甲|贫|常人|用|忌|喜|先|次|透|藏|主|必|定)', sent):
            # Extract
            proposition = sent.strip()
            # Clean up markdown
            proposition = proposition.replace('#', '').strip()
            if not proposition: continue
            
            # Find concepts
            found_concepts = []
            for surface, cid in concept_map.items():
                if surface in proposition:
                    found_concepts.append(cid)
                    
            conditions = [title]
            if '若' in proposition or '或' in proposition:
                parts = re.split(r'[，,]', proposition)
                conditions.extend([p for p in parts if '若' in p or '或' in p])
            
            assertions.append({
                'assertion_id': f'as_bazi_{as_idx:06d}',
                'proposition': proposition,
                'proposition_id': f'pr_bazi_{as_idx:06d}',
                'relation': 'supports',
                'evidence': [{
                    'source_span_id': span_id,
                    'support_type': 'direct'
                }],
                'conditions': conditions,
                'exceptions': [],
                'concept_ids': found_concepts,
                'status': 'machine_extracted'
            })
            as_idx += 1
            extracted_for_seg = True
            
    if not extracted_for_seg:
        reason = 'case_example' if is_case else 'narrative'
        skipped.append({
            'seg_id': seg_id,
            'reason': reason
        })

# Output
out = {'assertions': assertions, 'skipped_segments': skipped}
with open('output/draft_gemini.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(out, f, allow_unicode=True, sort_keys=False)

print(f"Extracted {len(assertions)} assertions, skipped {len(skipped)} segments.")
