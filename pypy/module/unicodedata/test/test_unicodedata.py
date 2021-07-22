import py
import sys

class AppTestUnicodeData:
    spaceconfig = dict(usemodules=('unicodedata',))

    def test_hangul_syllables(self):
        import unicodedata
        # Test all leading, vowel and trailing jamo
        # but not every combination of them.
        for code, name in ((0xAC00, 'HANGUL SYLLABLE GA'),
                           (0xAE69, 'HANGUL SYLLABLE GGAEG'),
                           (0xB0D2, 'HANGUL SYLLABLE NYAGG'),
                           (0xB33B, 'HANGUL SYLLABLE DYAEGS'),
                           (0xB5A4, 'HANGUL SYLLABLE DDEON'),
                           (0xB80D, 'HANGUL SYLLABLE RENJ'),
                           (0xBA76, 'HANGUL SYLLABLE MYEONH'),
                           (0xBCDF, 'HANGUL SYLLABLE BYED'),
                           (0xBF48, 'HANGUL SYLLABLE BBOL'),
                           (0xC1B1, 'HANGUL SYLLABLE SWALG'),
                           (0xC41A, 'HANGUL SYLLABLE SSWAELM'),
                           (0xC683, 'HANGUL SYLLABLE OELB'),
                           (0xC8EC, 'HANGUL SYLLABLE JYOLS'),
                           (0xCB55, 'HANGUL SYLLABLE JJULT'),
                           (0xCDBE, 'HANGUL SYLLABLE CWEOLP'),
                           (0xD027, 'HANGUL SYLLABLE KWELH'),
                           (0xD290, 'HANGUL SYLLABLE TWIM'),
                           (0xD4F9, 'HANGUL SYLLABLE PYUB'),
                           (0xD762, 'HANGUL SYLLABLE HEUBS'),
                           (0xAE27, 'HANGUL SYLLABLE GYIS'),
                           (0xB090, 'HANGUL SYLLABLE GGISS'),
                           (0xB0AD, 'HANGUL SYLLABLE NANG'),
                           (0xB316, 'HANGUL SYLLABLE DAEJ'),
                           (0xB57F, 'HANGUL SYLLABLE DDYAC'),
                           (0xB7E8, 'HANGUL SYLLABLE RYAEK'),
                           (0xBA51, 'HANGUL SYLLABLE MEOT'),
                           (0xBCBA, 'HANGUL SYLLABLE BEP'),
                           (0xBF23, 'HANGUL SYLLABLE BBYEOH'),
                           (0xD7A3, 'HANGUL SYLLABLE HIH')):
            assert unicodedata.name(unichr(code)) == name
            assert unicodedata.lookup(name) == unichr(code)
        # Test outside the range
        raises(ValueError, unicodedata.name, unichr(0xAC00 - 1))
        raises(ValueError, unicodedata.name, unichr(0xD7A3 + 1))

    def test_cjk(self):
        import sys
        import unicodedata
        cases = ((0x3400, 0x4DB5),
                 (0x4E00, 0x9FA5))
        if unicodedata.unidata_version >= "5":    # don't know the exact limit
            cases = ((0x3400, 0x4DB5),
                     (0x4E00, 0x9FCB),
                     (0x20000, 0x2A6D6),
                     (0x2A700, 0x2B734))
        elif unicodedata.unidata_version >= "4.1":
            cases = ((0x3400, 0x4DB5),
                     (0x4E00, 0x9FBB),
                     (0x20000, 0x2A6D6))
        for first, last in cases:
            # Test at and inside the boundary
            for i in (first, first + 1, last - 1, last):
                charname = 'CJK UNIFIED IDEOGRAPH-%X'%i
                char = ('\\U%08X' % i).decode('unicode-escape')
                assert unicodedata.name(char) == charname
                assert unicodedata.lookup(charname) == char
            # Test outside the boundary
            for i in first - 1, last + 1:
                charname = 'CJK UNIFIED IDEOGRAPH-%X'%i
                char = ('\\U%08X' % i).decode('unicode-escape')
                try:
                    unicodedata.name(char)
                except ValueError as e:
                    assert e.message == 'no such name'
                raises(KeyError, unicodedata.lookup, charname)

    def test_bug_1704793(self): # from CPython
        import unicodedata
        assert unicodedata.lookup("GOTHIC LETTER FAIHU") == u'\U00010346'

    def test_normalize_bad_argcount(self):
        import unicodedata
        raises(TypeError, unicodedata.normalize, 'x')

    def test_normalize_nonunicode(self):
        import unicodedata
        exc_info = raises(TypeError, unicodedata.normalize, 'NFC', 'x')
        assert str(exc_info.value).endswith('must be unicode, not str')

    @py.test.mark.skipif("sys.maxunicode < 0x10ffff")
    def test_normalize_wide(self):
        import unicodedata
        assert unicodedata.normalize('NFC', u'\U000110a5\U000110ba') == u'\U000110ab'

    def test_linebreaks(self):
        linebreaks = (0x0a, 0x0b, 0x0c, 0x0d, 0x85,
                      0x1c, 0x1d, 0x1e, 0x2028, 0x2029)
        for i in linebreaks:
            for j in range(-2, 3):
                lines = (unichr(i + j) + u'A').splitlines()
                if i + j in linebreaks:
                    assert len(lines) == 2
                else:
                    assert len(lines) == 1

    def test_mirrored(self):
        import unicodedata
        # For no reason, unicodedata.mirrored() returns an int, not a bool
        assert repr(unicodedata.mirrored(u' ')) == '0'

    def test_bidirectional_not_one_character(self):
        import unicodedata
        exc_info = raises(TypeError, unicodedata.bidirectional, u'xx')
        assert str(exc_info.value) == 'need a single Unicode character as parameter'

    def test_bidirectional_not_one_character(self):
        import unicodedata
        exc_info = raises(TypeError, unicodedata.bidirectional, 'x')
        assert str(exc_info.value).endswith('must be unicode, not str')
