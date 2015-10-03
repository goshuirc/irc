#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .formatting import escape
from .utils import NickMask, parse_modes

NAME_ATTR = 0
INFO_ATTR = 1

# maps verbs' params to attribute names in event dicts
# if the param name starts with 'escaped_', the param is escaped
#   before being set
# the params 'source' and 'target' will be converted to Client,
#   Channel, or Server objects in the event dict
_verb_param_map = {
    'target': {
        0: (
            'privmsg', 'pubmsg', 'privnotice', 'pubnotice', 'ctcp',
            'umode', 'cmode', 'nosuchservice', 'ctcp_reply',
            'targettoofast',
        ),
        1: (
            'cmodeis',
        ),
    },
    'new_nick': {
        0: (
            'nick',
        ),
    },
    'nick': {
        0: (
            'welcome',
        ),
    },
    'user': {
        0: (
            'kick',
        ),
    },
    'escaped_message': {
        0: (
            'info', 'endofinfo',
            'motdstart', 'motd', 'endofmotd',
            'youreoper',
            'adminloc1', 'adminloc2', 'adminemail',
            'quit',
        ),
        1: (
            'privmsg', 'pubmsg', 'privnotice', 'pubnotice',
            'nosuchnick', 'nosuchserver', 'nosuchchannel', 'nosuchservice',
            'targettoofast', 'kick', 'welcome',
        ),
    },
    'channel': {
        0: (
            'cannotsendtochan',
            'topic', 'cmode',
        ),
        1: (
            'endofnames', 'cmodeis', 'chancreatetime',
        ),
        2: (
            'namreply',
        ),
    },
    'topic': {
        1: (
            'topic',
        ),
    },
    'names': {
        3: (
            'namreply',
        ),
    },
    'timestamp': {
        2: (
            'chancreatetime',
        ),
    },
    'escaped_reason': {
        1: (
            'cannotsendtochan',
        ),
    },
    'channels': {
        0: (
            'join', 'part',
        ),
    }
}


def ctcp_unpack_message(info):
    """Given a an input message (privmsg/pubmsg/notice), return events."""
    verb = info['verb']
    message = info['params'][1]

    # NOTE: full CTCP dequoting and unpacking is not done here, only a subset
    #   this is because doing the full thing breaks legitimate messages

    # basics
    infos = []

    X_QUOTE = '\\'
    X_DELIM = '\x01'

    # tagged data
    messages = str(message).split(X_DELIM)

    for i in range(len(messages)):
        msg = messages[i]
        new_info = dict(info)

        if i % 2 == 0:  # is normal message)
            if not msg:
                continue
            new_info['params'] = new_info['params'][:1]
            new_info['params'].append(msg)
        else:
            if verb in ['privnotice', 'pubnotice']:
                new_info['verb'] = 'ctcp_reply'
            else:
                new_info['verb'] = 'ctcp'
            if ' ' in msg.lstrip():
                new_info['ctcp_verb'], new_info['ctcp_text'] = msg.lstrip().split(' ', 1)
            else:
                new_info['ctcp_verb'] = msg.lstrip()
                new_info['ctcp_text'] = ''

            new_info['ctcp_verb'] = new_info['ctcp_verb'].lower()

        infos.append([new_info['verb'], new_info])

    # ctcp-level dequoting
    for i in range(len(infos)):
        if infos[i][NAME_ATTR] == 'ctcp':
            attrs = ['ctcp_verb', 'ctcp_text']
        else:
            attrs = ['params']

        for attr in attrs:
            if isinstance(infos[i][INFO_ATTR][attr], (list, tuple)):
                raw_messages = infos[i][INFO_ATTR][attr]
            else:
                raw_messages = [infos[i][INFO_ATTR][attr]]

            messages = []
            for raw in raw_messages:
                unquoted = ''
                while len(raw):
                    char = raw[0]
                    raw = raw[1:]

                    if char == X_QUOTE:
                        if not len(raw):
                            continue
                        key = raw[0]
                        raw = raw[1:]

                        if key == 'a':
                            unquoted += X_DELIM
                        elif key == X_QUOTE:
                            unquoted += X_QUOTE
                        else:
                            unquoted += key
                    else:
                        unquoted += char
                messages.append(unquoted)

            if isinstance(infos[i][INFO_ATTR][attr], (list, tuple)):
                infos[i][INFO_ATTR][attr] = messages
            else:
                infos[i][INFO_ATTR][attr] = messages[0]

    return infos


def message_to_event(direction, message):
    """Prepare an ``RFC1459Message`` for event dispatch.

    We do this because we have to handle special things as well, such as CTCP
    and deconstructing verbs properly.
    """
    server = message.server

    # change numerics into nice names
    if message.verb in numerics:
        message.verb = numerics[message.verb]
    verb = message.verb.lower()

    # modify public/private verbs
    if verb == 'privmsg':
        if server.is_channel(message.params[0]):
            verb = 'pubmsg'
    if verb == 'notice':
        verb = 'privnotice'
        if server.is_channel(message.params[0]):
            verb = 'pubnotice'
    elif verb == 'mode':
        verb = 'umode'
        if server.is_channel(message.params[0]):
            verb = 'cmode'

    # this is the same as ircreactor does
    info = message.__dict__
    info['direction'] = direction
    info['verb'] = verb

    infos = [[verb, info], ]

    # handle shitty ctcp
    if verb in ('privmsg', 'pubmsg', 'privnotice', 'pubnotice'):
        infos = ctcp_unpack_message(info)

    # work on each info object separately
    i = -1
    while i < (len(infos) - 1):
        i += 1
        name = infos[i][NAME_ATTR]

        # standard message attributes
        for attr, param_map in _verb_param_map.items():
            # escaping
            escaped = False
            if attr.startswith('escaped_'):
                attr = attr.lstrip('escaped_')
                escaped = True

            for param_number, verbs in param_map.items():
                if len(infos[i][INFO_ATTR]['params']) > param_number and name in verbs:
                    value = infos[i][INFO_ATTR]['params'][param_number]
                    if escaped:
                        value = escape(value)
                    infos[i][INFO_ATTR][attr] = value

        # custom processing
        if name == 'welcome':
            # for servers where a low nicklen makes them silently truncate our nick
            server.nick = server.istring(infos[i][INFO_ATTR]['nick'])

        # custom message attributes
        if name == 'ctcp':
            if infos[i][INFO_ATTR]['ctcp_verb'] == 'action':
                info = dict(infos[i][INFO_ATTR])
                info['message'] = info['ctcp_text']
                infos.append(['action', info])

        if name == 'umode' and len(infos[i][INFO_ATTR]['params']) > 1:
            modestring = infos[i][INFO_ATTR]['params'][1:]
            modes = parse_modes(modestring)

            infos[i][INFO_ATTR]['modestring'] = ' '.join(modestring).strip()
            infos[i][INFO_ATTR]['modes'] = modes

        if name == 'cmode' and len(infos[i][INFO_ATTR]['params']) > 1:
            modestring = infos[i][INFO_ATTR]['params'][1:]
            chanmodes = server.features.get('chanmodes')
            modes = parse_modes(modestring, chanmodes)

            infos[i][INFO_ATTR]['modestring'] = ' '.join(modestring).strip()
            infos[i][INFO_ATTR]['modes'] = modes

        if name == 'cmodeis':
            if len(infos[i][INFO_ATTR]['params']) > 2:
                modestring = infos[i][INFO_ATTR]['params'][2:]
                chanmodes = server.features.get('chanmodes')
                modes = parse_modes(modestring, chanmodes)

                infos[i][INFO_ATTR]['modestring'] = ' '.join(modestring).strip()
                infos[i][INFO_ATTR]['modes'] = modes
            else:
                infos[i][INFO_ATTR]['modestring'] = ''
                infos[i][INFO_ATTR]['modes'] = []

        if name == 'namreply':
            channel_name = infos[i][INFO_ATTR]['params'][2]
            server.info.create_channel(channel_name)
            channel = server.info.channels.get(channel_name)

            nice_names = []
            channel_prefixes = {}
            if len(infos[i][INFO_ATTR]['params']) > 3:
                raw_names = infos[i][INFO_ATTR]['params'][3].split(' ')
            else:
                raw_names = []

            for name in raw_names:
                # InspIRCd sends us an empty last param because they are cool
                if not len(name):
                    continue

                prefixes = ''
                while name[0] in server.features.available['prefix'].values():
                    prefixes += name[0]
                    name = name[1:]

                nick = NickMask(name).nick

                server.info.create_user(nick)
                nice_names.append(name)
                server.info.create_user(name)
                user = server.info.users.get(nick)
                channel_prefixes[user] = prefixes
                channel.add_user(nick, prefixes=prefixes)

            infos[i][INFO_ATTR]['users'] = ','.join(nice_names)
            infos[i][INFO_ATTR]['prefixes'] = channel_prefixes

        # source / target mapping
        for attr in ('source', 'target', 'channel'):
            if attr in infos[i][INFO_ATTR] and infos[i][INFO_ATTR][attr]:
                source = infos[i][INFO_ATTR][attr]
                if server.is_channel(source):
                    server.info.create_channel(source)
                    infos[i][INFO_ATTR][attr] = server.info.channels.get(source)
                elif '.' in source and server.is_server(source):
                    server.info.create_server(source)
                    infos[i][INFO_ATTR][attr] = server.info.servers.get(source)
                elif server.is_nick(source):
                    server.info.create_user(source)
                    infos[i][INFO_ATTR][attr] = server.info.users.get(NickMask(source).nick)
                else:  # we assume this is a user with messed up characters
                    server.info.create_user(source)
                    infos[i][INFO_ATTR][attr] = server.info.users.get(NickMask(source).nick)

        if 'channels' in infos[i][INFO_ATTR] and infos[i][INFO_ATTR]['channels']:
            channels = []
            for chan in infos[i][INFO_ATTR]['channels'].split(','):
                server.info.create_channel(chan)
                channels.append(server.info.channels.get(chan))
            infos[i][INFO_ATTR]['channels'] = channels

        if 'users' in infos[i][INFO_ATTR] and infos[i][INFO_ATTR]['users']:
            users = []
            for user in infos[i][INFO_ATTR]['users'].split(','):
                server.info.create_user(user)
                users.append(server.info.users.get(NickMask(user).nick))
            infos[i][INFO_ATTR]['users'] = users

        # custom from_to attribute for ease in bots
        verb = infos[i][INFO_ATTR]['verb']
        dir = infos[i][INFO_ATTR]['direction']
        source = infos[i][INFO_ATTR].get('source')
        target = infos[i][INFO_ATTR].get('target')

        if verb == 'privmsg':
            if dir == 'in':
                infos[i][INFO_ATTR]['from_to'] = source
            elif dir == 'out':
                infos[i][INFO_ATTR]['from_to'] = target
        elif verb == 'pubmsg':
            infos[i][INFO_ATTR]['from_to'] = target
        elif verb == 'privnotice':
            if dir == 'in':
                infos[i][INFO_ATTR]['from_to'] = source
            elif dir == 'out':
                infos[i][INFO_ATTR]['from_to'] = target
        elif verb == 'pubnotice':
            if dir == 'in':
                infos[i][INFO_ATTR]['from_to'] = target
            elif dir == 'out':
                infos[i][INFO_ATTR]['from_to'] = target

        if 'from_to' in infos[i][INFO_ATTR] and infos[i][INFO_ATTR]['from_to'].is_server:
            del infos[i][INFO_ATTR]['from_to']

    return infos


# list adapted from https://www.alien.net.au/irc/irc2numerics.html
# some stuff in here is insane, but we can fix bad numerics as we find them
# we prefer IRCv3 numerics over most everything else
numerics = {
    '001': 'welcome',
    '002': 'yourhost',
    '003': 'created',
    '004': 'myinfo',
    '005': 'features',
    '008': 'snomask',
    '009': 'statmemtot',
    '010': 'bounce',
    '014': 'yourcookie',
    '042': 'yourid',
    '043': 'savenick',
    '050': 'attemptingjunc',
    '051': 'attemptingreroute',
    '200': 'tracelink',
    '201': 'traceconnecting',
    '202': 'tracehandshake',
    '203': 'traceunknown',
    '204': 'traceoperator',
    '205': 'traceuser',
    '206': 'traceserver',
    '207': 'traceservice',
    '208': 'tracenewtype',
    '209': 'traceclass',
    '210': 'stats',
    '211': 'statslinkinfo',
    '212': 'statscommands',
    '213': 'statscline',
    '215': 'statsiline',
    '216': 'statskline',
    '218': 'statsyline',
    '219': 'endofstats',
    '221': 'umode',
    '234': 'servlist',
    '235': 'servlistend',
    '236': 'statsverbose',
    '237': 'statsengine',
    '239': 'statsiauth',
    '241': 'statslline',
    '242': 'statsuptime',
    '243': 'statsoline',
    '244': 'statshline',
    '245': 'statssline',
    '250': 'statsconn',
    '251': 'luserclient',
    '252': 'luserop',
    '253': 'luserunknown',
    '254': 'luserchannels',
    '255': 'luserme',
    '256': 'adminme',
    '257': 'adminloc1',
    '258': 'adminloc2',
    '259': 'adminemail',
    '261': 'tracelog',
    '263': 'tryagain',
    '265': 'localusers',
    '266': 'globalusers',
    '267': 'start_netstat',
    '268': 'netstat',
    '269': 'end_netstat',
    '270': 'privs',
    '271': 'silelist',
    '272': 'endofsilelist',
    '273': 'notify',
    '276': 'vchanexist',
    '277': 'vchanlist',
    '278': 'vchanhelp',
    '280': 'glist',
    '296': 'chaninfo_kicks',
    '299': 'end_chaninfo',
    '300': 'none',
    '301': 'away',
    '302': 'userhost',
    '303': 'ison',
    '305': 'unaway',
    '306': 'nowaway',
    '311': 'whoisuser',
    '312': 'whoisserver',
    '313': 'whoisoperator',
    '314': 'whowasuser',
    '315': 'endofwho',
    '317': 'whoisidle',
    '318': 'endofwhois',
    '319': 'whoischannels',
    '320': 'whoisspecial',
    '322': 'list',
    '323': 'listend',
    '324': 'cmodeis',
    '326': 'nochanpass',
    '327': 'chpassunknown',
    '328': 'channel_url',
    '329': 'chancreatetime',
    '331': 'notopic',
    '332': 'topic',
    '333': 'topicwhotime',
    '339': 'badchanpass',
    '340': 'userip',
    '341': 'inviting',
    '345': 'invited',
    '346': 'invitelist',
    '347': 'endofinvitelist',
    '348': 'exceptlist',
    '349': 'endofexceptlist',
    '351': 'version',
    '352': 'whoreply',
    '353': 'namreply',
    '354': 'whospcrpl',
    '355': 'namreply_',
    '364': 'links',
    '365': 'endoflinks',
    '366': 'endofnames',
    '367': 'banlist',
    '368': 'endofbanlist',
    '369': 'endofwhowas',
    '371': 'info',
    '372': 'motd',
    '374': 'endofinfo',
    '375': 'motdstart',
    '376': 'endofmotd',
    '381': 'youreoper',
    '382': 'rehashing',
    '383': 'youreservice',
    '385': 'notoperanymore',
    '388': 'alist',
    '389': 'endofalist',
    '391': 'time',
    '392': 'usersstart',
    '393': 'users',
    '394': 'endofusers',
    '395': 'nousers',
    '396': 'hosthidden',
    '400': 'unknownerror',
    '401': 'nosuchnick',
    '402': 'nosuchserver',
    '403': 'nosuchchannel',
    '404': 'cannotsendtochan',
    '405': 'toomanychannels',
    '406': 'wasnosuchnick',
    '407': 'toomanytargets',
    '408': 'nosuchservice',
    '409': 'noorigin',
    '410': 'invalidcapcmd',
    '411': 'norecipient',
    '412': 'notexttosend',
    '413': 'notoplevel',
    '414': 'wildtoplevel',
    '415': 'badmask',
    '416': 'querytoolong',
    '419': 'lengthtruncated',
    '421': 'unknowncommand',
    '422': 'nomotd',
    '423': 'noadmininfo',
    '424': 'fileerror',
    '425': 'noopermotd',
    '429': 'toomanyaway',
    '430': 'eventnickchange',
    '431': 'nonicknamegiven',
    '432': 'erroneusnickname',
    '433': 'nicknameinuse',
    '436': 'nickcollision',
    '439': 'targettoofast',
    '440': 'servicesdown',
    '441': 'usernotinchannel',
    '442': 'notonchannel',
    '443': 'useronchannel',
    '444': 'nologin',
    '445': 'summondisabled',
    '446': 'usersdisabled',
    '447': 'nonickchange',
    '449': 'notimplemented',
    '451': 'notregistered',
    '452': 'idcollision',
    '453': 'nicklost',
    '455': 'hostilename',
    '456': 'acceptfull',
    '457': 'acceptexist',
    '458': 'acceptnot',
    '459': 'nohiding',
    '460': 'notforhalfops',
    '461': 'needmoreparams',
    '462': 'alreadyregistered',
    '463': 'nopermforhost',
    '464': 'passwdmismatch',
    '465': 'yourebannedcreep',
    '467': 'keyset',
    '469': 'linkset',
    '471': 'channelisfull',
    '472': 'unknownmode',
    '473': 'inviteonlychan',
    '474': 'bannedfromchan',
    '475': 'badchannelkey',
    '476': 'badchanmask',
    '478': 'banlistfull',
    '479': 'linkfail',
    '481': 'noprivileges',
    '482': 'chanoprivsneeded',
    '483': 'cantkillserver',
    '485': 'uniqoprivsneeded',
    '488': 'tslesschan',
    '491': 'nooperhost',
    '493': 'nofeature',
    '494': 'badfeature',
    '495': 'badlogtype',
    '496': 'badlogsys',
    '497': 'badlogvalue',
    '498': 'isoperlchan',
    '499': 'chanownprivneeded',
    '501': 'umodeunknownflag',
    '502': 'usersdontmatch',
    '503': 'ghostedclient',
    '504': 'usernotonserv',
    '511': 'silelistfull',
    '512': 'toomanywatch',
    '513': 'badping',
    '515': 'badexpire',
    '516': 'dontcheat',
    '517': 'disabled',
    '522': 'whosyntax',
    '523': 'wholimexceed',
    '525': 'remotepfx',
    '526': 'pfxunroutable',
    '550': 'badhostmask',
    '551': 'hostunavail',
    '552': 'usingsline',
    '600': 'logon',
    '601': 'logoff',
    '602': 'watchoff',
    '603': 'watchstat',
    '604': 'nowon',
    '605': 'nowoff',
    '606': 'watchlist',
    '607': 'endofwatchlist',
    '608': 'watchclear',
    '611': 'islocop',
    '612': 'isnotoper',
    '613': 'endofisoper',
    '618': 'dcclist',
    '624': 'omotdstart',
    '625': 'omotd',
    '626': 'endofo',
    '630': 'settings',
    '631': 'endofsettings',
    '660': 'traceroute_hop',
    '661': 'traceroute_start',
    '662': 'modechangewarn',
    '663': 'chanredir',
    '664': 'servmodeis',
    '665': 'otherumodeis',
    '666': 'endof_generic',
    '670': 'starttls',
    # '670': 'whowasdetails',
    '671': 'whoissecure',
    '672': 'unknownmodes',
    '673': 'cannotsetmodes',
    '678': 'luserstaff',
    '679': 'timeonserveris',
    '682': 'networks',
    '687': 'yourlanguageis',
    '688': 'language',
    '689': 'whoisstaff',
    '690': 'whoislanguage',
    '691': 'starttls_error',
    '702': 'modlist',
    '703': 'endofmodlist',
    '704': 'helpstart',
    '705': 'helptxt',
    '706': 'endofhelp',
    '708': 'etracefull',
    '709': 'etrace',
    '710': 'knock',
    '711': 'knockdlvr',
    '712': 'toomanyknock',
    '713': 'chanopen',
    '714': 'knockonchan',
    '715': 'knockdisabled',
    '716': 'targumodeg',
    '717': 'targnotify',
    '718': 'umodegmsg',
    '720': 'omotdstart',
    '721': 'omotd',
    '722': 'endofomotd',
    '723': 'noprivs',
    '724': 'testmark',
    '725': 'testline',
    '726': 'notestline',
    '730': 'mononline',
    '731': 'monoffline',
    '732': 'monlist',
    '733': 'endofmonlist',
    '734': 'monlistfull',
    '760': 'whoiskeyvalue',
    '761': 'keyvalue',
    '762': 'metadataend',
    '764': 'metadatalimit',
    '765': 'targetinvalid',
    '766': 'nomatchingkey',
    '767': 'keyinvalid',
    '768': 'keynotset',
    '769': 'keynopermission',
    '771': 'xinfo',
    '773': 'xinfostart',
    '774': 'xinfoend',
    '900': 'loggedin',
    '901': 'loggedout',
    '902': 'nicklocked',
    '903': 'saslsuccess',
    '904': 'saslfail',
    '905': 'sasltoolong',
    '906': 'saslaborted',
    '907': 'saslalready',
    '908': 'saslmechs',
    '972': 'cannotdocommand',
    '973': 'cannotchangeumode',
    '974': 'cannotchangechanmode',
    '975': 'cannotchangeservermode',
    '976': 'cannotsendtonick',
    '977': 'unknownservermode',
    '979': 'servermodelock',
    '980': 'badcharencoding',
    '981': 'toomanylanguages',
    '982': 'nolanguage',
    '983': 'texttooshort',
    '999': 'numeric_error',
}
