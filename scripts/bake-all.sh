#!/bin/sh
# Re-bake every lightmapped zone, then rebuild all assets. Long-running (GPU); run after authoring changes.
set -e
cd "$(dirname "$0")/.."
npm run bake -- stair_hall 4096 256
npm run bake -- grand_salon 2048 256
npm run bake -- library 4096 256
npm run bake -- ballroom 4096 256
npm run bake -- exterior 2048 256
npm run build:assets
