# Mansion — redesign plan (2026-10-07)

Mansion is a fork of CasinoV2. Its direction is **a French Riviera villa in which casino games are played**,
not a casino styled as a villa. Every room is first a real room of a Belle Époque Riviera house: a library,
a salon, a ballroom, a dining room. Each is furnished and dressed as densely as a wealthy owner's house would
be. Games appear only where a house of that era would plausibly host them.

## Decisions (user, 2026-10-07)

| Question | Decision |
|---|---|
| Mood | **Night, as now.** Warm chandelier-lit interiors and the night sea through French windows. |
| Games | **Woven through rooms.** One or two showpiece tables per game, each in a room that suits it. |
| Scope | **Ground floor first.** The upper floor (bedrooms, boudoir, study) is a later phase. |
| Staircase | Replace the straight stair with a grand stair: twin curved flights or an imperial stair (below). |
| Dressing rule | Every room carries the full furnishing of its type, layered and lived-in, high end and classy. No bare walls, no empty corners, no box rooms with props dropped in. |

## What changes and what stays

**Stays (layers 2–4 contracts):**
- the GLB + manifest pipeline, bake, KTX2/Meshopt and validation;
- streaming, the player, collision and the interaction framework;
- the `ANCHOR_` table presenters, the placeholder game engines and the Kraffing tables and slots;
- the Salon Privé fire, the night sea texture and the `LightPool`.

**Changes (layer 1 content, plus one layout contract):**
- **Floor plan.** The current plan is a hub lobby, two corridors and one game room per game, each holding
  identical tables. The new plan is a real villa plan: a stair hall, an enfilade of reception rooms on the
  sea front, and service galleries behind them.
- **Rooms.** The shared `shell()` box (damask, pilasters, coffers) gives way to one authoring script per
  room type, each with its own architecture: library gallery, ballroom mirrors, dining-room buffet niche,
  orangerie glazing.
- **Layout contract.** Zone placement moves from the fixed `LOBBY_SLOTS` / `HALL_SLOTS` (left / right /
  end) to a master layout file, `blender/mansion/layout.json`, which holds each zone's world transform and
  its door connections. `build-assets` copies the transforms into the manifest, and `zoneGraph.ts` reads
  them from there. This is a cross-layer change, so the validator and docs change in the same commit.

## Ground-floor plan

```
                                 SEA — terrace balustrade, night sea through French windows
 ┌────────────┬──────────────┬──────────────┬────────────────┬──────────────┬──────────────┐
 │ ORANGERIE  │  BALLROOM    │ GRAND SALON  │   STAIR HALL   │   LIBRARY    │ BILLIARD RM  │
 │ palms,     │ Salon de     │ drawing room │  twin curved   │ two-storey   │ + bar        │
 │ citrus,    │ Musique      │              │  stairs around │ bookcases    │              │
 │ fountain   │ ◆ roulette×2 │ ◆ baccarat   │  centrepiece   │ ◆ poker ×1–2 │ ◆ blackjack  │
 ├────────────┴──────┬───────┴──────────────┤                ├──────────────┴──┬───────────┤
 │ DINING ROOM       │ WEST GALLERY         │   VESTIBULE    │ EAST GALLERY    │ SALLE DES │
 │ table for 16      │ busts, consoles      │   entrance     │ portraits       │ MACHINES  │
 │                   │                      │                │                 │ ◆ slots×6 │
 └───────────────────┴──────────────────────┴────────────────┴─────────────────┴───────────┘
        FUMOIR (current Salon Privé with its fire, re-dressed) opens off the East Gallery
                          FORECOURT — seen through the front door at night
```

The sea-front rooms link to each other through aligned double doors (a true enfilade), and also to the
galleries behind them. In the streaming graph each door is a portal, so standing in the Grand Salon loads
the Ballroom, the Stair Hall and the West Gallery.

## Rooms and their dressing

The ◆ marks a game. Tables come from the Kraffing pack, which keeps the anchors calibrated, and are placed so
they read as the room's centrepiece rather than as a casino floor.

| Zone | Architecture | Dressing (minimum) | Game |
|---|---|---|---|
| **Vestibule** | Marble floor and limestone walls, glazed inner doors, coffered ceiling | Pair of consoles with mirrors, umbrella stand, bench, porcelain urns, lantern, coat niche, palms | — |
| **Stair Hall** | Double height (≈11 m), upper gallery with balustrade, skylight or lantern dome, the grand staircase | Centrepiece, large chandelier, long-case clock, busts on pedestals, tapestry, consoles, landing with locked upper doors | — |
| **Grand Salon** | Painted boiserie with gilt, Versailles parquet, marble fireplace with trumeau mirror, French windows | Three Louis XV seating groups, Aubusson-style carpets, bureau plat, vitrine of porcelain, ormolu clock and candelabra, piano, flowers, books and objects on every surface | Baccarat ×1, roped off at the window end |
| **Ballroom / Salon de Musique** | Mirrored arcades, Versailles parquet, three chandeliers, musicians' alcove | Grand piano, harp, gilt chairs lining the walls, banquettes, palms in jardinières, wall girandoles | Roulette ×2, set at the centre of the floor |
| **Library** | Walnut bookcases on two levels with a gallery and spiral stair, fireplace, coffered ceiling | Thousands of book spines, library table, globe, reading chairs, writing desk with lamp, chess table, busts above the cases, ladder | Poker ×1–2, under green-shaded lamps |
| **Billiard Room** | Dark panelling, beamed ceiling, bar niche | Billiard table (the pack's pool table, moved from the Salon Privé), cue rack, Chesterfields, bar cart with decanters, trophies, sporting prints | Blackjack ×1–2 |
| **Salle des Machines** | Small panelled cabinet room | The pack's slot cabinets along the panelling like curios, leather banquette, palm | Slots ×6 + Lucky Spin |
| **Dining Room** | Panelling, sideboard niche, two fireplaces | Table for 16 fully set (china, silver, glass, candelabra, flowers), sideboards with silver, porcelain, still lifes | — |
| **Orangerie** | Glazed iron and glass conservatory, terracotta and marble floor, fountain | Palms and citrus in Versailles planters, wicker and rattan seating, lanterns, statues | — |
| **Galleries** | Vaulted corridors with runners | Busts, consoles with clocks and vases, portraits and landscapes, benches, jardinières | — |
| **Fumoir** | The current Salon Privé | Keep the fire. Swap the jukebox for a gramophone and add a cigar cabinet, humidors, newspapers and pipes | — |

### Grand staircase (Stair Hall)

Two forms are possible: **twin curved flights** that arc up to the gallery around a centrepiece, or an
**imperial stair** (one flight to a half-landing that splits left and right).

Recommended: **twin curved flights.** Two flights of about 2.2 m each sweep up symmetrically from the hall
floor to the gallery landing. Between them, under the landing, stands a centrepiece: a marble statue on a
round fountain basin, with a massive floral arrangement on a round table directly under the main chandelier.

Construction:
- treads are lathe/sweep geometry with marble treads and walnut handrails;
- balusters are instanced turned balusters;
- the collider is a stepped helical ramp, so the existing step-up controller handles it;
- the upper landing is walkable, and its doors are locked with the prompt "Private apartments" until the
  upper-floor phase.

The imperial stair remains a drop-in alternative inside the same hall if you prefer it.

## Assets

- **Poly Haven (CC0), add to `fetch-models`:**
  - furniture: `Chandelier_01–03`, `GothicCabinet_01`, `GothicCommode_01`, `vintage_cabinet_01`,
    `vintage_day_bed`, `Ottoman_01`, `dining_table`, `dining_chair_02`, `ClassicNightstand_01`;
  - objects: `book_encyclopedia_set_01`, `decorative_book_set_01`, `chess_set`, `tea_set_01`, `brass_goblets`,
    `wine_bottles_01`, `seadogs_compass`, `magnifying_glass_01`, `ceramic_vase_01–04`, `brass_vase_01–04`,
    `fancy_picture_frame_01–02`, `standing_picture_frame_01–02`, `throw_pillows_01`, `lion_head`, `wall_clock`;
  - plants: `island_tree_01–03`, `pachira_aquatica_01`, `calathea_orbifolia_01`, `anthurium_botany_01`,
    `potted_plant_01/04`;
  - all at 1k, instanced.
- **Authored in Blender (no CC0 source):**
  - furniture and architecture: grand piano, harp, bookcases with generated book spines (atlas), boiserie
    panel kit, fireplaces with trumeau mirrors, curtains with tiebacks, the staircase;
  - table and floral details: dining place settings, floral arrangements (built from the plant scans).
- **Met Open Access (CC0):**
  - more paintings, including portraits for the galleries and still lifes for the dining room;
  - more carpets: Savonnerie / Aubusson-style rugs for the salon.

## Performance

Dense dressing is the main risk. The current lobby is already 1.08 M triangles.

Mitigations:
- every repeated prop is an instanced prototype (shared mesh);
- props under about 0.3 m skip the lightmap and are lit by AO + probe only;
- small clutter gets a `_LOD1` and is culled beyond about 12 m;
- book spines are one merged mesh per bookcase with an atlas.

Budgets per zone will be re-set in `docs/performance.md` once the Grand Salon is measured, before the other
rooms are dressed.

## Phases

| # | Deliverable | Verify |
|---|---|---|
| **M0** | Layout contract (`layout.json` → manifest → `zoneGraph`), fetch the new props, retire the five box game rooms from the graph | typecheck/tests, existing zones still load at their new transforms |
| **M1** | Vestibule + Stair Hall with the twin curved staircase and the walkable upper gallery | walk the stairs both ways, collider wireframes, FPS |
| **M2** | Grand Salon + baccarat; set the dressing-density and performance budgets here | seated at baccarat; FPS / draw calls / tris against budget |
| **M3** | Library + poker, Ballroom + roulette | seated at each table |
| **M4** | Billiard Room + blackjack, Salle des Machines + slots, Fumoir re-dress | seated at each table; slots spin |
| **M5** | Dining Room, Orangerie, both galleries, forecourt and terrace views, ambience audio per room | full walk-through, console clean |
| **Later** | Upper floor: bedrooms (canopy bed, dressing table, armoire, chaise, boudoir), study, bathrooms | — |

Each phase follows CLAUDE.md §3: author → bake → `build:assets` → typecheck/test/build → browser check → docs.
