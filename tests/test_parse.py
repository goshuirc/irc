import unittest

import parser_tests.data

from girc.ircreactor.envelope import RFC1459Message
from girc.utils import NickMask, validate_hostname


class ParserTestCase(unittest.TestCase):
    def test_msg_split(self):
        for data in parser_tests.data.msg_split['tests']:
            input_txt = data['input']
            atoms = data['atoms']
            msg = RFC1459Message.from_message(input_txt)

            self.assertEqual(msg.tags, atoms.get('tags', {}))

            self.assertEqual(msg.source, atoms.get('source'))

            self.assertEqual(msg.verb.lower(), atoms.get('verb', '').lower())

            self.assertEqual(msg.params, atoms.get('params', []))

    def test_msg_join(self):
        for data in parser_tests.data.msg_join['tests']:
            atoms = data['atoms']
            matches = data['matches']

            m = RFC1459Message.from_data(atoms['verb'], **{
                'params': atoms.get('params'),
                'source': atoms.get('source'),
                'tags': atoms.get('tags', {}),
            })
            msg = m.to_message()

            self.assertIn(msg, matches)

    def test_userhost_split(self):
        for data in parser_tests.data.userhost_split['tests']:
            source = data['source']
            atoms = data['atoms']

            nickmask = NickMask(source)

            self.assertEqual(nickmask.nick, atoms.get('nick', ''))
            self.assertEqual(nickmask.user, atoms.get('user', ''))
            self.assertEqual(nickmask.host, atoms.get('host', ''))

    def test_hostname_validate(self):
        for data in parser_tests.data.validate_hostname['tests']:
            host = data['host']
            should_be_valid = data['valid']
            self.assertEqual(validate_hostname(host), should_be_valid)
