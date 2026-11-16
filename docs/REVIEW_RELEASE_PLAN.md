# First external review build

Target: a portable Windows ZIP that a reviewer extracts and starts by double-clicking `Benghazi Handicap.exe`. This is a playtest build, not a final campaign or installer. Keep the existing Python source launch and JSON scenarios usable for development.

## Reviewer journey

1. Start at a main menu with **New game**, **Continue**, **How to play**, **Options**, and **Quit**. Continue is available when a save exists.
2. New game offers every shipped scenario, its dates, High Command aims, an experimental Axis sea-delivery setting, and who commands Axis and Commonwealth: human, Easy, Standard, Hard, or no-orders spectator. Defaults are the short Sidi Rezegh scenario, the current campaign estimate, Commonwealth human, Axis Standard.
3. Start immediately at the game map. The in-game Game menu and Escape offer resume, save/load, help, options, a new game, and exit. Starting another game first autosaves the current one.
4. Help explains the first turn, orders, air, supply, turn playback, saves, and feedback capture. F1 opens it at any point. Options cover counter symbols, sound, visual/reminder preferences, and the Game Files path with a button to open it in the host file manager. Preferences survive a restart.
5. Saves, screenshots, logs and preferences go under the user's writable app-data folder in a packaged build. Source checkouts continue to use their existing local folders unless explicitly configured.
6. Windows CI creates and smoke-tests a portable onedir build, then publishes a ZIP artifact with a short reviewer README. A reviewer should not need Python or a console.

## Acceptance checks

- Double-click launch reaches the menu with no arguments and no console window.
- Both scenarios and all human/computer pairings can be started; game choice remains saveable and loadable.
- A saved game resumes after quitting and relaunching; an incompatible or damaged save gives a readable message.
- Help and options can be opened from the menu and during play; closing them resumes the same turn.
- Window X exits and autosaves; sound off remains off after restart; F12 captures a screenshot in a writable folder.
- Options shows the actual Game Files path and opens it in Windows Explorer; saves and screenshots have named folders there.
- Offscreen rendering and the existing engine/UI tests pass. The Windows CI ZIP starts and can render a screenshot there.

Local check, 31 October 2026: the Windows onedir EXE and 22 MB ZIP built on the development PC. The packaged EXE rendered a menu and Sidi Rezegh frame in dummy video mode. A live Windows launch showed the titled game window and closed with exit code 0 through its window control. The source menu flow tests cover setup, save/continue, help, options and minimum-size rendering. External reviewer feedback and a GitHub-hosted workflow run are still pending.

Local rebuild, 5 November 2026: the full source suite passed **411 tests**. The Windows build script produced `dist/Benghazi-Handicap-Windows-Review.zip` (22 MB) and verified packaged screenshots for the menu, Sidi Rezegh, and the opt-in Compass research trial. ZIP inspection confirmed the Compass draft JSON and `Compass Research Trial.cmd` are included. The archive SHA-256 is `f6a3b796d57d89cfa1dfb827dfe5cb2967c233d5c62bde4e51bc4503fb0ef56e`. A live Windows window-control test was not repeated for this rebuild. The trial is deliberately absent from New battle and New campaign while its 1940 evidence is reviewed.

Later rebuild, 5 November 2026: the extracted Compass research trial now
continues through the linked 17 December–2 January interval. The source
integration tests for the Compass trial, interval, handoff and supply passed
**32/32**. The Windows build script passed its packaged menu, Sidi Rezegh and
Compass screenshot checks. ZIP inspection confirmed both research JSON files
match source and `Compass Research Trial.cmd` remains included. The rebuilt
archive is **22,550,034 bytes**, SHA-256
`8e30bc513f61acb06fe34c49f8a907a2183f4bcac4b9bc95e8262fb8ed3435fb`.
The Bardia assault is not in this build; its operation is still under research.

Latest rebuild, 5 November 2026: the linked research path now reaches the
3–5 January Bardia assault. The full source suite passed **420 tests**. The
Windows build script passed its packaged menu, Sidi Rezegh and Compass
screenshot checks. ZIP inspection confirmed the three research JSON files
match source and the launcher and reviewer guide are included. The archive is
**22,555,003 bytes**, SHA-256
`a2c6c2ef7311fd1d2f3edd4a7b0d726862bd48f28c7a3e6382185daf83ee93f8`.
Three Hard/Hard seed traces held Bardia for Axis; the research assault is a
playable diagnostic and remains outside the standard battle menu.

## Boundaries for this build

Scenario and player choices are read from existing registries. The sea-delivery option is a small scenario transformation recorded inside the saved scenario; it is a sensitivity test of an estimated schedule, not a historical reconstruction of Malta. The review build does not promise scenario balance, a tutorial campaign, historical audit completion, or a Windows installer. Record playtest findings for later revisions.
