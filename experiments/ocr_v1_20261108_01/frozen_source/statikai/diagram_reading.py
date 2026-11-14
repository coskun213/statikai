"""Conservative horizontal beam interpretation. No physical distance from pixels.

Symbols, OCR and line pixels enter independently. Dimension labels form a graph
of measured lengths. Missing edges stay missing; no interpolation or statics.
"""
from collections import Counter, defaultdict, deque
from decimal import Decimal
from itertools import permutations
import cv2
import numpy as np
from .ocr_quantities import parse_readings

CONFIG = dict(minimum_ocr_confidence=.8, endpoint_tolerance_width=.02,
              dimension_consistency_m=.001, force_label_dx_width=.045,
              supported_domain='horizontal pin/roller beam, two downward point loads')


def cx(box):
    return (box[0]+box[2])/2


def components(mask):
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    return [list(map(int, b[:4])) for b in stats[1:]]


def line_geometry(image):
    gray = np.asarray(image.convert('L'))
    h, w = gray.shape
    if np.median(gray) < 127:
        gray = 255-gray
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    long = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((1, max(20, w//3)), np.uint8))
    beams = [b for b in components(long) if b[2] > .4*w and .15*h < b[1] < .7*h and b[3] < .025*h]
    if not beams:
        return dict(beam=None, horizontal=[], vertical=[])
    x, y, bw, bh = min(beams, key=lambda b: b[1])
    beam = dict(left_px=x, right_px=x+bw-1, y_px=y+(bh-1)/2,
                method='topmost long horizontal ink component')
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((1, max(12, w//40)), np.uint8))
    horizontal = [dict(x0=a, x1=a+c-1, y=b+(d-1)/2, thickness=d)
                  for a, b, c, d in components(horizontal)
                  if b > beam['y_px']+.09*h and c > .035*w and c > 8*d]
    vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((max(8, h//65), 1), np.uint8))
    vertical = [dict(x=a+(c-1)/2, y0=b, y1=b+d-1)
                for a, b, c, d in components(vertical) if d > 3*c]
    return dict(beam=beam, horizontal=horizontal, vertical=vertical)


def dimension_graph(nodes, dimensions, tolerance=.001):
    """Return exact-decimal coordinates and provenance; detect inconsistent cycles."""
    adjacent = defaultdict(list)
    for edge in dimensions:
        a, b = edge['nodes']
        delta = Decimal(str(edge['value_m']))
        adjacent[a].append((b, delta, edge['id']))
        adjacent[b].append((a, -delta, edge['id']))
    positions = {'support_A': Decimal('0')}
    paths = {'support_A': []}
    queue = deque(['support_A'])
    conflicts = []
    while queue:
        a = queue.popleft()
        for b, delta, edge_id in adjacent[a]:
            expected = positions[a]+delta
            if b in positions:
                if abs(positions[b]-expected) > Decimal(str(tolerance)):
                    conflicts.append(edge_id)
            else:
                positions[b] = expected
                paths[b] = paths[a]+[edge_id]
                queue.append(b)
    return {k: float(v) for k, v in positions.items()}, paths, sorted(set(conflicts))


def interpret(image, symbols, raw_readings, config=None):
    cfg = dict(CONFIG, **(config or {}))
    w, h = image.size
    readings = parse_readings(raw_readings, cfg['minimum_ocr_confidence'])
    geometry = line_geometry(image)
    issues = []

    def warn(code, detail, sources=None):
        issues.append(dict(code=code, severity='review_required', detail=detail,
                           source_ids=sources or []))

    result = dict(schema_version='statikai.ocr.v1', coordinate_system='original image pixels, xyxy',
                  config=cfg, ocr_readings=readings, geometry=geometry, symbols=symbols,
                  forces=[], supports=[], length_m=None, extracted_inputs=None,
                  issues=issues, review_required=True,
                  static_solution=dict(status='not_run', RA_kN=None, RB_kN=None))
    # OCR also sees hatching/ticks as digits. Keep them in JSON, but only labels
    # above loads or clearly above dimension baselines can supply quantities.
    # Unsupported numeric text in those regions always blocks acceptance.
    for item in readings:
        text, q = item['raw_text'], item['quantity']
        a=item['bbox']; th=a[3]-a[1]
        force_region=any(s['class_id']==2 and 0 <= s['bbox'][1]-a[3] < .2*h
                         and abs(cx(a)-cx(s['bbox'])) <= .06*w for s in symbols)
        dim_region=any(.15*th <= line['y']-a[3] <= .065*h and line['x0'] <= cx(a) <= line['x1']
                       for line in geometry['horizontal'])
        item['label_region'] = 'force' if force_region else 'dimension' if dim_region else 'other_ink'
        if any(c.isdigit() for c in text) and not item['accepted'] and not item.get('grouped_into') and (force_region or dim_region):
            warn('low_confidence' if q['status']=='ok' else q['status'],
                 'Numeric OCR text cannot be used safely: '+text, [item['id']])
    if Counter(int(s['class_id']) for s in symbols) != Counter({0: 1, 1: 1, 2: 2}):
        warn('symbol_inventory', 'Need exactly one pin, one roller and two load arrows; no best-two fallback.')
        return result
    beam = geometry['beam']
    if beam is None:
        warn('beam_not_found', 'Horizontal beam could not be located.')
        return result
    supports = sorted([s for s in symbols if s['class_id'] != 2], key=lambda s: cx(s['bbox']))
    # This first prototype explicitly rejects reversed/overhanging layouts.
    if supports[0]['class_id'] != 0:
        warn('unsupported_orientation', 'This version requires pin at left and roller at right.')
        return result
    for side, support in zip(('left_px', 'right_px'), supports):
        if abs(cx(support['bbox'])-beam[side]) > .06*w or abs(support['bbox'][1]-beam['y_px']) > .08*h:
            warn('support_beam_mismatch', 'Detected support is inconsistent with a beam endpoint.')
    loads = sorted([s for s in symbols if s['class_id']==2], key=lambda s: cx(s['bbox']))
    nodes = {'support_A': beam['left_px'], 'support_B': beam['right_px']}
    # Locate vertical stems inside predicted boxes, without true symbol boxes.
    for i, load in enumerate(loads, 1):
        candidates = [v for v in geometry['vertical'] if load['bbox'][0] <= v['x'] <= load['bbox'][2]
                      and v['y0'] < beam['y_px'] and v['y1'] >= load['bbox'][1]
                      and v['y1'] < beam['y_px']+.03*h]
        nodes[f'load_{i}'] = (max(candidates, key=lambda v: v['y1']-v['y0'])['x']
                              if candidates else cx(load['bbox']))
    geometry['nodes_px'] = nodes
    if not nodes['support_A'] < nodes['load_1'] < nodes['load_2'] < nodes['support_B']:
        warn('load_geometry', 'Loads must lie within the two support endpoints.')
    force_texts = [t for t in readings if t['accepted'] and t['quantity']['kind']=='force']
    possible = []
    if len(force_texts)==2:
        for assignment in permutations(force_texts):
            if all(abs(cx(t['bbox'])-nodes[f'load_{i}']) <= max(cfg['force_label_dx_width']*w, t['bbox'][3]-t['bbox'][1])
                   and 0 <= load['bbox'][1]-t['bbox'][3] < .2*h
                   for i, (load, t) in enumerate(zip(loads, assignment), 1)):
                possible.append(assignment)
    associations = possible[0] if len(possible)==1 else (None, None)
    if len(possible)!=1:
        warn('ambiguous_force_text' if len(possible)>1 else 'missing_force_text',
             'Exactly one feasible one-to-one force/text assignment is required.')
    for i, (load, text) in enumerate(zip(loads, associations), 1):
        result['forces'].append(dict(id=f'load_{i}', symbol_bbox=load['bbox'],
             anchor_px=[nodes[f'load_{i}'], beam['y_px']],
             magnitude_kN=None if text is None else dict(value=text['quantity']['value_si'],
                 source_text_ids=[text['id']], bbox=text['bbox'], confidence=text['confidence']), position_m=None))
    dimensions = []
    for text in readings:
        if not text['accepted'] or text['quantity']['kind']!='length':
            continue
        tx, ty = cx(text['bbox']), text['bbox'][3]
        lines = [line for line in geometry['horizontal']
                 if -2 <= line['y']-ty <= .065*h and line['x0'] <= tx <= line['x1']]
        if not lines:
            warn('dimension_line_missing', 'No dimension baseline below length label.', [text['id']])
            continue
        line = min(lines, key=lambda line: abs(line['y']-ty))
        # Internal witness lines partition a continuous chain baseline.
        witnesses = sorted(v['x'] for v in geometry['vertical']
                           if v['y0'] <= line['y'] <= v['y1']
                           and line['x0']-4 <= v['x'] <= line['x1']+4)
        clusters = []
        for x in witnesses:
            if not clusters or x-clusters[-1] > max(3, .004*w):
                clusters.append(x)
        intervals = [(a, b) for a, b in zip(clusters, clusters[1:]) if a < tx < b]
        if len(intervals)!=1:
            warn('dimension_endpoints_missing', 'Could not uniquely delimit label by witness lines.', [text['id']])
            continue
        endpoints = intervals[0]
        mapped = [[name for name, x in nodes.items() if abs(x-end) <= cfg['endpoint_tolerance_width']*w]
                  for end in endpoints]
        if any(len(m)!=1 for m in mapped) or mapped[0]==mapped[1]:
            warn('ambiguous_dimension_endpoint', 'Witness lines do not uniquely match detected symbols.', [text['id']])
            continue
        dimensions.append(dict(id=f'dimension_{len(dimensions)}', nodes=[m[0] for m in mapped],
             value_m=text['quantity']['value_si'], text_source_ids=[text['id']],
             source_bbox=text['bbox'], confidence=text['confidence'],
             endpoints_px=[[endpoints[0], line['y']], [endpoints[1], line['y']]]))
    geometry['dimensions'] = dimensions
    # Two independent labels on the same interval are ambiguous even if equal.
    if len({tuple(d['nodes']) for d in dimensions}) != len(dimensions):
        warn('duplicate_dimension', 'Multiple numeric labels were assigned to one dimension interval.')
    positions, paths, conflicts = dimension_graph(nodes, dimensions, cfg['dimension_consistency_m'])
    if conflicts:
        warn('contradictory_dimensions', 'Dimension graph has inconsistent cycles.', conflicts)
    if set(positions) != set(nodes):
        warn('incomplete_dimension_chain', 'Some symbol positions cannot be reached using read dimensions.')
    for force in result['forces']:
        name = force['id']
        if name in positions and not conflicts:
            source = [d for d in dimensions if d['id'] in paths[name]]
            force['position_m'] = dict(value=positions[name], dimension_ids=paths[name],
                source_text_ids=[s for d in source for s in d['text_source_ids']],
                confidence=min(d['confidence'] for d in source),
                method='sum of OCR dimensions; pixel coordinates only associate endpoints')
    if 'support_B' in positions and not conflicts:
        result['length_m'] = dict(value=positions['support_B'], dimension_ids=paths['support_B'],
             source_text_ids=[s for d in dimensions if d['id'] in paths['support_B'] for s in d['text_source_ids']],
             confidence=min(d['confidence'] for d in dimensions if d['id'] in paths['support_B']),
             method='dimension graph from left support origin')
    result['supports'] = [dict(id=name, class_id=s['class_id'], bbox=s['bbox'],
                              anchor_px=[nodes[name], beam['y_px']])
                          for name, s in zip(('support_A', 'support_B'), supports)]
    if set(positions)==set(nodes) and not 0 < positions['load_1'] < positions['load_2'] < positions['support_B']:
        warn('invalid_measured_positions', 'Read dimensions violate 0 < x1 < x2 < L.')
    if not issues:
        result['extracted_inputs'] = dict(L_m=positions['support_B'],
             P1_kN=result['forces'][0]['magnitude_kN']['value'], x1_m=positions['load_1'],
             P2_kN=result['forces'][1]['magnitude_kN']['value'], x2_m=positions['load_2'])
        result['review_required'] = False
    return result
