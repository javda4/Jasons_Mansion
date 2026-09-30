#!/bin/sh
# Re-bake every lightmapped zone, then rebuild all assets. Long-running (GPU); run after authoring changes.
set -e
cd "$(dirname "$0")/.."
npm run bake -- lobby 4096 256
for z in hall_west hall_east poker blackjack baccarat roulette slots; do npm run bake -- "$z" 2048 256; done
npm run build:assets
