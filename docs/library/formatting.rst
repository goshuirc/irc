:mod:`girc.formatting` --- Formatting
========================================

.. module:: girc.formatting

This module handles formatting codes within messages, such as italics, bold, and colour codes.

Formatting codes in girc are prepended with a ``$`` symbol. This is a full table of formatting codes:

===========   ============  ===============
   Code           Name        Description
-----------   ------------  ---------------
 ``$b``        Bold           Shows the message as bold
 ``$i``        Italics        Shows the message as italics (often not implemented)
 ``$u``        Underline      Shows the message as underlined (often not implemented)
 ``$c``        Colours        Allows for `colour codes <#id1>`_
 ``$r``        Reset          Removes all formatting codes, sets back to standard text
===========   ============  ===============


Colour Codes
------------

Using colour codes, you can specify the foreground and background colours of text.

To use colour codes in girc, you can use the simplified colour syntax, as the examples below:

``Test $c[blue]message $c[red]$b*BZZT*$r``

``Test $c[blue,green]message$r``

Valid colour codes:

- ``white``
- ``black``
- ``blue``
- ``green``
- ``red``
- ``brown``
- ``magenta``
- ``orange``
- ``yellow``
- ``light green``
- ``cyan``
- ``light cyan``
- ``light blue``
- ``light magenta``
- ``grey``
- ``light grey``


Escaping and Unescaping
-----------------------

There are two standard functions to convert a message to and from the original to an escaped version:

.. automethod:: girc.formatting.escape

.. automethod:: girc.formatting.unescape
