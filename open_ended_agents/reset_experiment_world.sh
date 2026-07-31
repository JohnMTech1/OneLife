#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--yes" ]]; then
    echo "Usage: ./reset_experiment_world.sh --yes"
    echo "Stop the agents and OneLifeServer first. This archives and resets world state."
    exit 2
fi

server_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/server" 2>/dev/null && pwd)" || {
    echo "Run this from the OneLife repository root (the directory containing server/)."
    exit 2
}

if pgrep -x OneLifeServer >/dev/null 2>&1; then
    echo "OneLifeServer is still running. Stop it before resetting the world."
    exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="$server_dir/world_backups/reset-$stamp"
mkdir -p "$backup_dir"

world_files=(
    biome.db eve.db floor.db floorTime.db grave.db lookTime.db
    map.db mapTime.db playerStats.db meta.db
    mapDummyRecall.txt lastEveLocation.txt recentPlacements.txt
    landingLocations.txt shutdownLongLineagePos.txt
)

moved=0
for name in "${world_files[@]}"; do
    source_path="$server_dir/$name"
    if [[ -e "$source_path" && ! -L "$source_path" ]]; then
        mv -- "$source_path" "$backup_dir/$name"
        moved=$((moved + 1))
    fi
done

echo "Reset complete: archived $moved world-state files in:"
echo "$backup_dir"
echo "Start the server again with: cd server && ./OneLifeServer"
echo "Natural resources will be generated fresh as the new map is explored."
