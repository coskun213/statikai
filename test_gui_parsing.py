import pytest
from statikai.gui.parsing import (format_lengths, format_sections, parse_combinations, parse_lengths,
                                  parse_sections, format_combinations)
from statikai.frame3d import default_combinations


@pytest.mark.parametrize('text,expected',[('5','5'),('5;4.5;6',(5.,4.5,6.)),('3@5',(5.,5.,5.)),
    ('4;2@3,5',(4.,3.5,3.5)),(' 6@3 ; ',(3.,)*6)])
def test_parse_lengths(text,expected):
    expected=(5.,) if expected=='5' else expected
    assert parse_lengths(text)==expected


@pytest.mark.parametrize('text',['','5;abc','0.5@4','x@4','60@3'])
def test_parse_lengths_rejects(text):
    with pytest.raises(ValueError): parse_lengths(text)


def test_parse_sections_and_round_trip():
    values=parse_sections('2@50x50;40×60;40X60')
    assert values==((50.,50.),(50.,50.),(40.,60.),(40.,60.))
    assert format_sections(values)=='2@50x50;2@40x60'
    assert parse_sections(format_sections(values))==values
    assert format_lengths((3.,3.,4.5))=='2@3;4.5'


@pytest.mark.parametrize('text',['40','40x','40x50x60','ax40'])
def test_parse_sections_rejects(text):
    with pytest.raises(ValueError): parse_sections(text)


def test_combination_text_round_trip():
    combos=default_combinations(10.,5.)
    assert parse_combinations(format_combinations(combos))==combos
    assert parse_combinations('# yorum\nA ; 1,2 ; 1 ; 0 ; 0')==(('A',1.2,1.,0.,0.),)
    with pytest.raises(ValueError): parse_combinations('A ; 1 ; 1')
