class AppTestClasses:
    spaceconfig = dict(usemodules=['_multibytecodec'])

    def setup_class(cls):
        cls.w_IncrementalHzDecoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalDecoder

            class IncrementalHzDecoder(MultibyteIncrementalDecoder):
                codec = _codecs_cn.getcodec('hz')

            return IncrementalHzDecoder
        """)
        cls.w_IncrementalHzEncoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalEncoder

            class IncrementalHzEncoder(MultibyteIncrementalEncoder):
                codec = _codecs_cn.getcodec('hz')

            return IncrementalHzEncoder
        """)
        cls.w_IncrementalBig5hkscsEncoder = cls.space.appexec([], """():
            import _codecs_cn
            from _multibytecodec import MultibyteIncrementalEncoder

            class IncrementalBig5hkscsEncoder(MultibyteIncrementalEncoder):
                codec = _codecs_cn.getcodec('big5hkscs')

            return IncrementalBig5hkscsEncoder
        """)

    def test_decode_hz(self):
        d = self.IncrementalHzDecoder()
        r = d.decode("~{abcd~}")
        assert r == u'\u5f95\u6c85'
        r = d.decode("~{efgh~}")
        assert r == u'\u5f50\u73b7'
        for c, output in zip("!~{abcd~}xyz~{efgh",
              [u'!',  # !
               u'',   # ~
               u'',   # {
               u'',   # a
               u'\u5f95',   # b
               u'',   # c
               u'\u6c85',   # d
               u'',   # ~
               u'',   # }
               u'x',  # x
               u'y',  # y
               u'z',  # z
               u'',   # ~
               u'',   # {
               u'',   # e
               u'\u5f50',   # f
               u'',   # g
               u'\u73b7',   # h
               ]):
            r = d.decode(c)
            assert r == output

    def test_decode_hz_final(self):
        d = self.IncrementalHzDecoder()
        r = d.decode("~{", True)
        assert r == u''
        raises(UnicodeDecodeError, d.decode, "~", True)
        raises(UnicodeDecodeError, d.decode, "~{a", True)

    def test_decode_hz_reset(self):
        d = self.IncrementalHzDecoder()
        r = d.decode("ab")
        assert r == u'ab'
        r = d.decode("~{")
        assert r == u''
        r = d.decode("ab")
        assert r == u'\u5f95'
        r = d.decode("ab")
        assert r == u'\u5f95'
        d.reset()
        r = d.decode("ab")
        assert r == u'ab'

    def test_decode_hz_error(self):
        d = self.IncrementalHzDecoder()
        raises(UnicodeDecodeError, d.decode, "~{abc", True)
        d = self.IncrementalHzDecoder("ignore")
        r = d.decode("~{abc", True)
        assert r == u'\u5f95'
        d = self.IncrementalHzDecoder()
        d.errors = "replace"
        r = d.decode("~{abc", True)
        assert r == u'\u5f95\ufffd'

    def test_decode_hz_buffer_grow(self):
        d = self.IncrementalHzDecoder()
        for i in range(13):
            r = d.decode("a" * (2**i))
            assert r == u"a" * (2**i)

    def test_encode_hz(self):
        e = self.IncrementalHzEncoder()
        r = e.encode("abcd")
        assert r == 'abcd'
        r = e.encode(u"\u5f95\u6c85")
        assert r == '~{abcd'
        r = e.encode(u"\u5f50")
        assert r == 'ef'
        r = e.encode(u"\u73b7", final=True)
        assert r == 'gh~}'

    def test_encode_hz_final(self):
        e = self.IncrementalHzEncoder()
        r = e.encode(u"xyz\u5f95\u6c85", True)
        assert r == 'xyz~{abcd~}'
        # This is a bit hard to test, because the only way I can see that
        # encoders can return MBERR_TOOFEW is with surrogates, which only
        # occur with 2-byte unicode characters...  We will just have to
        # trust that the logic works, because it is exactly the same one
        # as in the decode case :-/

    def test_encode_hz_reset(self):
        # Same issue as with test_encode_hz_final
        e = self.IncrementalHzEncoder()
        r = e.encode(u"xyz\u5f95\u6c85", True)
        assert r == 'xyz~{abcd~}'
        e.reset()
        r = e.encode(u"xyz\u5f95\u6c85")
        assert r == 'xyz~{abcd'
        r = e.encode(u'', final=True)
        assert r == '~}'

    def test_encode_hz_noreset(self):
        text = (u'\u5df1\u6240\u4e0d\u6b32\uff0c\u52ff\u65bd\u65bc\u4eba\u3002'
                u'Bye.')
        out = ''
        e = self.IncrementalHzEncoder()
        for c in text:
            out += e.encode(c)
        assert out == b'~{<:Ky2;S{#,NpJ)l6HK!#~}Bye.'

    def test_encode_hz_error(self):
        e = self.IncrementalHzEncoder()
        raises(UnicodeEncodeError, e.encode, u"\u4321", True)
        e = self.IncrementalHzEncoder("ignore")
        r = e.encode(u"xy\u4321z", True)
        assert r == 'xyz'
        e = self.IncrementalHzEncoder()
        e.errors = "replace"
        r = e.encode(u"xy\u4321z", True)
        assert r == 'xy?z'

    def test_encode_hz_buffer_grow(self):
        e = self.IncrementalHzEncoder()
        for i in range(13):
            r = e.encode(u"a" * (2**i))
            assert r == "a" * (2**i)

    def test_encode_big5hkscs(self):
        #e = self.IncrementalBig5hkscsEncoder()
        #r = e.encode(u'\xca', True)
        #assert r == '\x88f'
        #r = e.encode(u'\xca', True)
        #assert r == '\x88f'
        #raises(UnicodeEncodeError, e.encode, u'\u0304', True)
        #
        e = self.IncrementalBig5hkscsEncoder()
        r = e.encode(u'\xca')
        assert r == ''
        r = e.encode(u'\xca')
        assert r == '\x88f'
        r = e.encode(u'\u0304')
        assert r == '\x88b'
