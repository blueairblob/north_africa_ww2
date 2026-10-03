"""The screen: a window, mouse and keyboard on top of the engine (DESIGN.md §12).

It is one kind of player. It is shown its side's view and gives orders, like the scripted
players; the engine knows nothing about it. session.py holds a game in progress and has no
pygame in it; draw.py paints a frame; app.py is the window and its keys.
"""
