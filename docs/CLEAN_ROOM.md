# Clean room: what this project may and may not use

*Western Desert* is a new, original game. It is inspired by the 8-bit desert
wargames of the 1980s, in particular *Desert Rats* (CCS, 1985), but it contains
nothing taken from them. This page says how that is kept true. (This is a
working practice, not legal advice.)

## The rule

Nothing in this repository is copied or derived from another game's program,
data, text or graphics. Everything comes from:

- **history** — what happened, where, when, and with which formations (facts are
  free to use; see `SOURCES.md`, and write the data in our own words and form);
- **geography** — public geographic data (see `SOURCES.md`);
- **our own design** — the rules in `DESIGN.md`, with numbers chosen and tuned
  for this game.

Game *mechanics* in general (hex maps, zones of control, supply lines,
simultaneous orders) are common to the genre and free to use. A particular
game's *expression* — its code, map data, unit tables, text, art and its exact
formulas and constants — is not.

## What must not come in

No program, data, text, art or numbers from any earlier game or from any
reconstruction of one. Contributors who have studied an earlier game's code or
data in detail should not write this project's rules tables or code; a fresh
contributor, working only from `DESIGN.md` and `SOURCES.md`, should.

## Before publishing this project

- [ ] Choose the name (see `README.md`).
- [ ] `docs/SOURCES.md` lists every source used for the map and the orders of
      battle, with its licence; attributions are in place (OpenStreetMap needs one).
- [ ] No file, name, text or number has come from another game or a reconstruction of one.
- [ ] Art is generated or drawn for this game.
- [ ] Repository history contains only this project.
