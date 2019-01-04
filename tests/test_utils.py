#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import unittest

from girc import utils


class UtilsTestCase(unittest.TestCase):
    """Tests our utils."""

    def setUp(self):
        errmsg = 'utils.{} does not exist!'
        self.assertTrue(utils.NickMask, msg=errmsg.format('NickMask'))

    def test_nickmask(self):
        nm = utils.NickMask('dan!~lol@localhost')

        self.assertEqual(nm.nick, 'dan')
        self.assertEqual(nm.user, '~lol')
        self.assertEqual(nm.host, 'localhost')
        self.assertEqual(nm.userhost, '~lol@localhost')
        self.assertEqual(nm.nickmask, 'dan!~lol@localhost')

        nm = utils.NickMask('dan!~lol')

        self.assertEqual(nm.nick, 'dan')
        self.assertEqual(nm.user, '~lol')
        self.assertEqual(nm.host, '')

        nm = utils.NickMask('dan@localhost')

        self.assertEqual(nm.nick, 'dan')
        self.assertEqual(nm.user, '')
        self.assertEqual(nm.host, 'localhost')

        nm = utils.NickMask('dan')

        self.assertEqual(nm.nick, 'dan')
        self.assertEqual(nm.user, '')
        self.assertEqual(nm.host, '')

        nm1 = nm = utils.NickMask('dan!~lol@localhost')
        nm2 = utils.NickMask(nm)

        self.assertEqual(nm1.nick, nm2.nick)
        self.assertEqual(nm1.user, nm2.user)
        self.assertEqual(nm1.host, nm2.host)

        # check 'nickmask' attribute
        class AlmostNickMask():
            nickmask = 'dan!~lol@localhost'
        nm = utils.NickMask(AlmostNickMask())

        self.assertEqual(nm.nick, 'dan')
        self.assertEqual(nm.user, '~lol')
        self.assertEqual(nm.host, 'localhost')

    def test_caseinsensitivelist(self):
        ls = utils.CaseInsensitiveList(['LoL', 'yOLo', 'Tres'])

        self.assertTrue('lol' in ls)
        self.assertTrue('YoLo' in ls)
        self.assertTrue('tRES' in ls)

        self.assertEqual(len(ls), 3)

    def test_caseinsensitivedict(self):
        dc = utils.CaseInsensitiveDict()

        dc['LoL'] = 35
        dc['yOlE'] = 'okay'
        dc['tRES'] = [4, 5, 6]

        self.assertEqual(dc['loL'], 35)
        self.assertEqual(dc.get('lOL'), 35)
        self.assertEqual(dc['YoLE'], 'okay')
        self.assertEqual(dc.get('YoLe'), 'okay')
        self.assertEqual(dc['TrEs'], [4, 5, 6])
        self.assertEqual(dc.get('TRES'), [4, 5, 6])

        self.assertEqual(len(dc), 3)

        del dc['lol']
        self.assertEqual(len(dc), 2)

        del dc['yole']
        self.assertEqual(list(dc.items()), [('tRES', [4, 5, 6])])
        self.assertEqual(list(dc.lower_items()), [('tres', [4, 5, 6])])

        # test equality of dicts
        dc2 = utils.CaseInsensitiveDict()
        dc2['TrEs'] = [4, 5, 6]

        self.assertEqual(dc, dc2)

        self.assertEqual(dc, dc2.copy())

    def test_hostnames(self):
        hn = utils.validate_hostname

        self.assertTrue(hn('google.com'))
        self.assertTrue(hn('google.com.'))
        self.assertTrue(hn('eth3rt.wrthwrt.qeht.ethwe.local'))

        self.assertFalse(hn(''))
        self.assertFalse(hn('hdfh.fgeth..ehf.egds'))
        self.assertFalse(hn('-lol-.43wrthwrt.qeht.ethwe.local'))

    def test_parse_modes(self):
        pm = utils.parse_modes

        modes = ['beI', 'k', 'l', 'BCMNORScimnpstz']

        self.assertEqual(pm(['+btk', 'lol', 'ok'], modes), [
            ['+', 'b', 'lol'],
            ['+', 't', None],
            ['+', 'k', 'ok'],
        ])

        self.assertEqual(pm(['+IBlCkSip', 'cool!re@example.com', 'oeoeoeoe!!', 'r'], modes), [
            ['+', 'I', 'cool!re@example.com'],
            ['+', 'B', None],
            ['+', 'l', 'oeoeoeoe!!'],
            ['+', 'C', None],
            ['+', 'k', 'r'],
            ['+', 'S', None],
            ['+', 'i', None],
            ['+', 'p', None],
        ])
