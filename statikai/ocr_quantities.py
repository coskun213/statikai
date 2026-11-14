"""Strict quantity parsing. Never repair digits, supply units or guess values."""
from decimal import Decimal, InvalidOperation
import re

UNITS = {'kN': ('force', Decimal('1'), 'kN'),
         'N': ('force', Decimal('.001'), 'kN'),
         'm': ('length', Decimal('1'), 'm'),
         'cm': ('length', Decimal('.01'), 'm'),
         'mm': ('length', Decimal('.001'), 'm')}


def parse_quantity(text):
    clean = re.sub(r'\s+', '', text.strip())
    match = re.fullmatch(r'([+-]?\d+(?:[.,]\d+)?)([^\d.,+\-]+)', clean)
    if not match:
        return dict(status='missing_unit' if re.fullmatch(r'[+-]?\d+(?:[.,]\d+)?', clean)
                    else 'unparsed', value_si=None)
    raw, unit = match.groups()
    if unit not in UNITS:
        return dict(status='unsupported_unit', raw_value=raw, unit=unit, value_si=None)
    kind, factor, si = UNITS[unit]
    try:
        value = Decimal(raw.replace(',', '.')) * factor
    except InvalidOperation:
        return dict(status='invalid_number', value_si=None)
    if not value.is_finite() or value <= 0:
        return dict(status='nonpositive_value', value_si=None)
    return dict(status='ok', kind=kind, raw_value=raw, unit=unit,
                value_si=float(value), value_si_decimal=str(value), si_unit=si,
                decimal_policy='one dot or comma is decimal; no thousands grouping')


def parse_readings(readings, minimum_confidence=.8):
    """Join split number/unit boxes only when the geometric pair is unique."""
    result = []
    for index, reading in enumerate(readings):
        item = dict(reading, id=f'text_{index}')
        item['quantity'] = parse_quantity(item['raw_text'])
        item['accepted'] = (item['quantity']['status'] == 'ok'
                            and item.get('confidence') is not None
                            and item['confidence'] >= minimum_confidence)
        result.append(item)
    pairings = []
    for number in result:
        if number['quantity']['status'] != 'missing_unit':
            continue
        a = number['bbox']; ah = a[3]-a[1]
        for unit in result:
            if unit['raw_text'].strip() not in UNITS:
                continue
            b = unit['bbox']; bh = b[3]-b[1]
            overlap = max(0, min(a[3], b[3])-max(a[1], b[1]))
            if (0 <= b[0]-a[2] <= max(ah, bh) and overlap >= .5*min(ah, bh)
                    and abs((a[1]+a[3]-b[1]-b[3])/2) <= .4*max(ah, bh)):
                pairings.append((number, unit))
    unique = [(a, b) for a, b in pairings
              if sum(x['id']==a['id'] for x, y in pairings)==1
              and sum(y['id']==b['id'] for x, y in pairings)==1]
    for a, b in unique:
        text = a['raw_text']+' '+b['raw_text']
        bbox = [min(a['bbox'][0], b['bbox'][0]), min(a['bbox'][1], b['bbox'][1]),
                max(a['bbox'][2], b['bbox'][2]), max(a['bbox'][3], b['bbox'][3])]
        confidence = min(a['confidence'], b['confidence'])
        item = dict(id=f'text_{len(result)}', raw_text=text, confidence=confidence,
                    bbox=bbox, quad=None, quantity=parse_quantity(text),
                    accepted=confidence>=minimum_confidence,
                    component_text_ids=[a['id'], b['id']], grouping='unique adjacent number/unit pair')
        a['grouped_into'] = b['grouped_into'] = item['id']
        result.append(item)
    return result
