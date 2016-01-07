.. image:: https://cdn.rawgit.com/DanielOaks/girc/master/docs/logo.png
    :alt: gIRC
    :align: center


A modern Python IRC library for Python 3.4, based on asyncio. In Development.

----

.. image:: https://img.shields.io/pypi/v/girc.svg?label=latest%20version
    :alt: PyPi Latest Version
    :target: https://pypi.python.org/pypi/girc
.. image:: https://travis-ci.org/DanielOaks/girc.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/DanielOaks/girc
.. image:: https://coveralls.io/repos/DanielOaks/girc/badge.svg?branch=master&service=github
    :alt: Coveralls Code Coverage
    :target: https://coveralls.io/github/DanielOaks/girc?branch=master

----

This is barely in alpha right now. If you use this, anything can change without any notice whatsoever, everything can be overhauled, and development may even stop entirely without any warning.

If you would like to help build this, awesome! Otherwise, I'd stay away for now and use another library: `irc <https://bitbucket.org/jaraco/irc>`_, `irc3 <https://github.com/gawel/irc3/>`_.

`Hosted Documentation <http://girc.readthedocs.org/en/latest/>`_


Features
--------
This library is in development, so these features may be in various levels of completion right now.

* Incoming and outgoing events.
* Info and state tracking.
* Server-based IRC mapping for dicts, lists, and strings.
* IRCv3 capability support.
* Escaping and unescaping IRC formatting for ease-of-use (bold, colours, etc).


Why?
----
I've been using another IRC library for a long time. It's been pretty good, but I need more features. Handling both incoming and outgoing messages, automatic information tracking, converting IRC formatting (bold/colours/etc) to and from an escaped, human-readable and writable format.

I've looked at some other libraries, but they're usually either too low-level, too involved, or too 'magic' for my liking. That said, this one is planning to be pretty magic, but it's going to be magic in a way I think makes sense.

So I decided to write my own. As part of `mammon-ircd <https://github.com/mammon-ircd/mammon>`_, a nice low-level library called `ircreactor <https://github.com/mammon-ircd/ircreactor>`_ was developed. This is also a chance to give that a spin from the client side, rather than the server side.


Running Tests
-------------
To run the test cases, go to the ``tests`` directory and run: ``python3 -m unittest``.


Acknowledgements
----------------
We bundle the `ircreactor <https://github.com/mammon-ircd/ircreactor>`_ library developed as a part of `mammon-ircd <https://github.com/mammon-ircd>`_. This license for this library can be found in the ``LICENSE.ircreactor`` file.
