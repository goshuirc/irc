#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import unittest

import base
from girc import formatting


class FormattingTestCase(unittest.TestCase):
    """Tests our formatting."""

    def setUp(self):
        errmsg = 'formatting.{} does not exist!'
        self.assertTrue(formatting.escape, msg=errmsg.format('escape'))
        self.assertTrue(formatting.unescape, msg=errmsg.format('unescape'))

    def test_colour_codes(self):
        self.assertEqual(formatting._ctos(5), 'brown')
        self.assertEqual(formatting._ctos(452), 'unknown: 452')

    def test_escaping(self):
        self.assertEqual(formatting.escape('Strawberries are \x02cool\x0f'),
                         'Strawberries are $bcool$r')

        self.assertEqual(formatting.escape('Such \x1dcool\x1d things\x02!\x0f'),
                         'Such $icool$i things$b!$r')

        self.assertEqual(formatting.escape('Lol \x03cool \x032tests\x0f!'),
                         'Lol $c[]cool $c[blue]tests$r!')

        self.assertEqual(formatting.escape('Lol cool\x03'),
                         'Lol cool$c[]')

        self.assertEqual(formatting.escape('Lol \x034cool \x032,tests\x0f!'),
                         'Lol $c[red]cool $c[blue],tests$r!')

        self.assertEqual(formatting.escape('\x02Lol \x034,2cool \x033,8tests\x0f!'),
                         '$bLol $c[red,blue]cool $c[green,yellow]tests$r!')

    def test_unescaping(self):
        self.assertEqual(formatting.unescape('Strawberries are $$cool$r'),
                         'Strawberries are $cool\x0f')

        self.assertEqual(formatting.unescape('Strawberries are $bcool$r'),
                         'Strawberries are \x02cool\x0f')

        self.assertEqual(formatting.unescape('Such $icool$i things$b!$r'),
                         'Such \x1dcool\x1d things\x02!\x0f')

        self.assertEqual(formatting.unescape('How cool$c'),
                         'How cool\x03')

        self.assertEqual(formatting.unescape('Lol $c[red]cool $c[blue]tests$r!'),
                         'Lol \x034cool \x032tests\x0f!')

        self.assertEqual(formatting.unescape('$bLol $c[red,blue]cool $c[green,yellow]tests$r!'),
                         '\x02Lol \x034,2cool \x033,8tests\x0f!')

        # testing custom unescaping function
        def custom_unescape(*args, **kwargs):
            return '{}-{}'.format(','.join(args),
                                  ','.join('{}:{}'.format(k, v) for k, v in kwargs.items()))

        extra_dict = {
            'custom': [custom_unescape, ['r', 't'], {'34': 'dfg'}],
        }
        self.assertEqual(formatting.unescape('lolo[${custom}]', extra_format_dict=extra_dict),
                         'lolo[r,t-34:dfg]')

        extra_dict = {
            'custom': [custom_unescape, ['wer', 'hgd']],
        }
        self.assertEqual(formatting.unescape('fff--${custom}]', extra_format_dict=extra_dict),
                         'fff--wer,hgd-]')

        extra_dict = {
            'custom': [custom_unescape],
        }
        self.assertEqual(formatting.unescape('abcd=${custom}=', extra_format_dict=extra_dict),
                         'abcd=-=')
