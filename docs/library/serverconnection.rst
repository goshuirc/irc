:class:`girc.client.ServerConnection` --- Single Server Connection
==================================================================

.. class:: girc.client.ServerConnection

This class handles a connection to a single IRC server. It's created by your :class:`girc.Reactor` using :meth:`girc.Reactor.create_server`, and usually accessed from events.

IRC casemapping
---------------

One of the important features of :class:`girc.client.ServerConnection` objects is the ability to easily create strings, lists, and dictionaries that follow the IRC server's casemapping. This is done using the following functions:

.. automethod:: girc.client.ServerConnection.istring

.. automethod:: girc.client.ServerConnection.ilist

.. automethod:: girc.client.ServerConnection.idict

Sending Messages
----------------

These are the main ways you'll interact with the server directly. It lets you send IRC messages directly to the server using a general sending function, as well as convenience methods for specific messages:

.. automethod:: girc.client.ServerConnection.send

.. automethod:: girc.client.ServerConnection.msg

.. automethod:: girc.client.ServerConnection.notice

.. automethod:: girc.client.ServerConnection.ctcp

.. automethod:: girc.client.ServerConnection.ctcp_reply

.. automethod:: girc.client.ServerConnection.mode

.. automethod:: girc.client.ServerConnection.join_channel
