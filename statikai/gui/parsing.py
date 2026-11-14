"""Text <-> value helpers for the input panel. Pure functions, unit tested.

Lists use ';' as separator and 'n@value' for repetition, the usual notation
on structural drawings:  "3@5"  ->  (5, 5, 5);  "4;2@3.5"  ->  (4, 3.5, 3.5).
Sections are 'AxB' in cm:  "2@50x50;40x40".
A decimal comma is accepted inside numbers ("4,5").
"""
from statikai.frame3d import validate_combinations

MAX_REPEAT=50


def _number(text,what):
    try:
        value=float(text.strip().replace(',','.'))
    except ValueError:
        raise ValueError(f'{what}: "{text.strip()}" sayı değil.') from None
    return value


def _expand(text,what,parse_item):
    items=[]
    for token in text.split(';'):
        token=token.strip()
        if not token:
            continue
        count=1
        if '@' in token:
            head,token=token.split('@',1)
            repeat=_number(head,what)
            if not repeat.is_integer() or not 1<=repeat<=MAX_REPEAT:
                raise ValueError(f'{what}: tekrar sayısı 1 ile {MAX_REPEAT} arasında tam sayı olmalı.')
            count=int(repeat)
        items.extend([parse_item(token)]*count)
    if not items:
        raise ValueError(f'{what}: en az bir değer girilmeli.')
    return tuple(items)


def parse_lengths(text,what='Uzunluklar'):
    """'5;4.5;2@6' -> (5.0, 4.5, 6.0, 6.0)."""
    return _expand(text,what,lambda token:_number(token,what))


def parse_sections(text,what='Kesitler'):
    """'2@50x50;40x60' -> ((50, 50), (50, 50), (40, 60))."""
    def item(token):
        parts=token.lower().replace('×','x').split('x')
        if len(parts)!=2:
            raise ValueError(f'{what}: "{token}" "AxB" biçiminde olmalı (cm), örn. 40x60.')
        return (_number(parts[0],what),_number(parts[1],what))
    return _expand(text,what,item)


def _compress(values,render):
    """Inverse of _expand: run-length encode equal neighbours with n@value."""
    out=[];index=0
    while index<len(values):
        run=1
        while index+run<len(values) and values[index+run]==values[index]:
            run+=1
        text=render(values[index])
        out.append(f'{run}@{text}' if run>1 else text)
        index+=run
    return ';'.join(out)


def format_lengths(values):
    return _compress(list(values),lambda v:f'{v:g}')


def format_sections(values):
    return _compress(list(values),lambda v:f'{v[0]:g}x{v[1]:g}')


def format_combinations(combos):
    return '\n'.join(f'{name} ; '+' ; '.join(f'{v:g}' for v in factors) for name,*factors in combos)


def parse_combinations(text):
    rows=[]
    for number,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):
            continue
        parts=[p.strip() for p in line.split(';')]
        if len(parts)!=5:
            raise ValueError(f'{number}. satır: "ad ; G ; Q ; EX ; EZ" biçiminde 5 alan olmalı.')
        try:
            factors=[float(p.replace(',','.')) for p in parts[1:]]
        except ValueError:
            raise ValueError(f'{number}. satır: katsayılar sayı olmalı.') from None
        rows.append((parts[0],*factors))
    combos=tuple(rows)
    validate_combinations(combos)
    return combos
