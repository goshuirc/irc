gIRC
====
A modern Python IRC library for Python 3.4, based on asyncio and ircreactor.

Very in-development right now.


Why?
----
I've been using the `irc library <https://bitbucket.org/jaraco/irc>`_ maintained by Jaraco for ages. That library is damn awesome, works well, and generally doesn't really give me any issues.

But there are things I need to add to it for my uses, such as more extensive info and state tracking, tracking of both incoming and outgoing messages, formatting (bold/colour/etc). In addition, with Python's shiny new `asyncio <https://docs.python.org/3.4/library/asyncio.html>`_ library, I figured it would be a good idea to start looking at a new library.

I had a look at some others, but quickly just settled on doing the cool thing and trying to write my own. For fun, so I can get closer to the protocol level, and it lets me test out `mammon's <https://github.com/mammon-ircd/mammon>`_ `ircreactor <https://github.com/mammon-ircd/ircreactor>`_ code.


License
-------
Released under the ISC license.
