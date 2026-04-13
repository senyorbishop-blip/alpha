(function () {
  const texturePaths = Object.freeze({
    1: '/static/textures/world/stone.png',
    2: '/static/textures/world/dirt-road.png',
    3: '/static/textures/world/grasslands.png',
    4: '/static/textures/world/water.png',
    5: '/static/textures/world/forest-ground.png',
    6: '/static/textures/world/cave-stone.png',
    7: '/static/textures/world/shallows-coast.png',
    8: '/static/textures/world/hills.png',
    9: '/static/textures/world/mountains.png',
    10: '/static/textures/world/desert-sand.png',
    11: '/static/textures/world/swamp-marsh.png',
    12: '/static/textures/world/snow-ice.png',
    13: '/static/textures/world/lava.png',
  });

  const terrainMeta = Object.freeze({
    1: { id: 1, key: 'stone', name: 'Stone', family: 'hardscape' },
    2: { id: 2, key: 'dirt_road', name: 'Dirt / Road', family: 'path' },
    3: { id: 3, key: 'grasslands', name: 'Grasslands', family: 'biome' },
    4: { id: 4, key: 'water', name: 'Water', family: 'water' },
    5: { id: 5, key: 'forest_ground', name: 'Forest Ground', family: 'biome' },
    6: { id: 6, key: 'cave_stone', name: 'Cave Stone', family: 'hardscape' },
    7: { id: 7, key: 'shallows_coast', name: 'Shallows / Coast', family: 'water' },
    8: { id: 8, key: 'hills', name: 'Hills', family: 'biome' },
    9: { id: 9, key: 'mountains', name: 'Mountains', family: 'biome' },
    10: { id: 10, key: 'desert_sand', name: 'Desert / Sand', family: 'biome' },
    11: { id: 11, key: 'swamp_marsh', name: 'Swamp / Marsh', family: 'biome' },
    12: { id: 12, key: 'snow_ice', name: 'Snow / Ice', family: 'biome' },
    13: { id: 13, key: 'lava', name: 'Lava', family: 'hazard' },
  });

  window.EditorTerrainManifest = Object.freeze({
    version: 1,
    texturePaths,
    terrainMeta,
    getTexturePath(terrain) {
      return texturePaths[Number(terrain) || 0] || null;
    },
    getTerrainMeta(terrain) {
      return terrainMeta[Number(terrain) || 0] || null;
    },
  });
})();
