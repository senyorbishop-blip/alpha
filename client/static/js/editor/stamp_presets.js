(function () {
  'use strict';

  const PRESETS = [
    {
      id: 'small-square-room',
      name: 'Small Square Room',
      category: 'Rooms',
      widthCells: 4,
      heightCells: 4,
      walls: [
        { x1: 0, y1: 0, x2: 4, y2: 0 },
        { x1: 4, y1: 0, x2: 4, y2: 4 },
        { x1: 4, y1: 4, x2: 0, y2: 4 },
        { x1: 0, y1: 4, x2: 0, y2: 0 },
      ],
      doors: [{ x: 2, y: 4, facing: 'h', kind: 'door' }],
    },
    {
      id: 'medium-square-room',
      name: 'Medium Square Room',
      category: 'Rooms',
      widthCells: 6,
      heightCells: 6,
      walls: [
        { x1: 0, y1: 0, x2: 6, y2: 0 },
        { x1: 6, y1: 0, x2: 6, y2: 6 },
        { x1: 6, y1: 6, x2: 0, y2: 6 },
        { x1: 0, y1: 6, x2: 0, y2: 0 },
      ],
      doors: [{ x: 3, y: 6, facing: 'h', kind: 'door' }],
    },
    {
      id: 'large-square-room',
      name: 'Large Square Room',
      category: 'Rooms',
      widthCells: 8,
      heightCells: 8,
      walls: [
        { x1: 0, y1: 0, x2: 8, y2: 0 },
        { x1: 8, y1: 0, x2: 8, y2: 8 },
        { x1: 8, y1: 8, x2: 0, y2: 8 },
        { x1: 0, y1: 8, x2: 0, y2: 0 },
      ],
      doors: [{ x: 4, y: 8, facing: 'h', kind: 'door' }],
    },
    {
      id: 'rectangle-room',
      name: 'Rectangle Room',
      category: 'Rooms',
      widthCells: 8,
      heightCells: 5,
      walls: [
        { x1: 0, y1: 0, x2: 8, y2: 0 },
        { x1: 8, y1: 0, x2: 8, y2: 5 },
        { x1: 8, y1: 5, x2: 0, y2: 5 },
        { x1: 0, y1: 5, x2: 0, y2: 0 },
      ],
      doors: [{ x: 4, y: 5, facing: 'h', kind: 'door' }],
    },
    {
      id: 'long-corridor',
      name: 'Long Corridor',
      category: 'Corridors',
      widthCells: 10,
      heightCells: 2,
      walls: [
        { x1: 0, y1: 0, x2: 10, y2: 0 },
        { x1: 0, y1: 2, x2: 10, y2: 2 },
      ],
    },
    {
      id: 'short-corridor',
      name: 'Short Corridor',
      category: 'Corridors',
      widthCells: 5,
      heightCells: 2,
      walls: [
        { x1: 0, y1: 0, x2: 5, y2: 0 },
        { x1: 0, y1: 2, x2: 5, y2: 2 },
      ],
    },
    {
      id: 'l-corridor',
      name: 'L-shaped Corridor',
      category: 'Corridors',
      widthCells: 6,
      heightCells: 6,
      walls: [
        { x1: 0, y1: 0, x2: 6, y2: 0 }, { x1: 0, y1: 2, x2: 4, y2: 2 },
        { x1: 4, y1: 2, x2: 4, y2: 6 }, { x1: 2, y1: 2, x2: 2, y2: 6 },
        { x1: 2, y1: 6, x2: 4, y2: 6 },
      ],
    },
    {
      id: 't-junction',
      name: 'T-junction Corridor',
      category: 'Corridors',
      widthCells: 7,
      heightCells: 6,
      walls: [
        { x1: 0, y1: 0, x2: 7, y2: 0 }, { x1: 0, y1: 2, x2: 7, y2: 2 },
        { x1: 2, y1: 2, x2: 2, y2: 6 }, { x1: 5, y1: 2, x2: 5, y2: 6 },
      ],
    },
    {
      id: 'crossroad',
      name: 'Crossroad Corridor',
      category: 'Corridors',
      widthCells: 7,
      heightCells: 7,
      walls: [
        { x1: 0, y1: 2, x2: 7, y2: 2 }, { x1: 0, y1: 5, x2: 7, y2: 5 },
        { x1: 2, y1: 0, x2: 2, y2: 7 }, { x1: 5, y1: 0, x2: 5, y2: 7 },
      ],
    },
    {
      id: 'doorway',
      name: 'Doorway',
      category: 'Doorways',
      widthCells: 1,
      heightCells: 1,
      walls: [],
      doors: [{ x: 0, y: 0, facing: 'h', kind: 'door' }],
    },
    {
      id: 'double-doorway',
      name: 'Double Doorway',
      category: 'Doorways',
      widthCells: 2,
      heightCells: 1,
      walls: [],
      doors: [
        { x: 0, y: 0, facing: 'h', kind: 'door' },
        { x: 1, y: 0, facing: 'h', kind: 'door' },
      ],
    },
    {
      id: 'square-building',
      name: 'Square Building',
      category: 'Buildings',
      widthCells: 7,
      heightCells: 7,
      walls: [
        { x1: 0, y1: 0, x2: 7, y2: 0 },
        { x1: 7, y1: 0, x2: 7, y2: 7 },
        { x1: 7, y1: 7, x2: 0, y2: 7 },
        { x1: 0, y1: 7, x2: 0, y2: 0 },
      ],
      doors: [{ x: 3, y: 7, facing: 'h', kind: 'door' }],
      props: [{ kind: 'table', x: 2, y: 2, w: 2, h: 1 }],
    },
    {
      id: 'tavern-room',
      name: 'Tavern Room',
      category: 'Buildings',
      widthCells: 10,
      heightCells: 7,
      walls: [
        { x1: 0, y1: 0, x2: 10, y2: 0 },
        { x1: 10, y1: 0, x2: 10, y2: 7 },
        { x1: 10, y1: 7, x2: 0, y2: 7 },
        { x1: 0, y1: 7, x2: 0, y2: 0 },
      ],
      doors: [{ x: 5, y: 7, facing: 'h', kind: 'door' }],
      props: [{ kind: 'table', x: 2, y: 2, w: 2, h: 1 }, { kind: 'barrel', x: 7, y: 2, w: 1, h: 1 }],
    },
    {
      id: 'dungeon-chamber',
      name: 'Dungeon Chamber',
      category: 'Special / Dungeon',
      widthCells: 9,
      heightCells: 7,
      walls: [
        { x1: 0, y1: 1, x2: 2, y2: 0 }, { x1: 2, y1: 0, x2: 7, y2: 0 }, { x1: 7, y1: 0, x2: 9, y2: 1 },
        { x1: 9, y1: 1, x2: 9, y2: 6 }, { x1: 9, y1: 6, x2: 7, y2: 7 }, { x1: 7, y1: 7, x2: 2, y2: 7 },
        { x1: 2, y1: 7, x2: 0, y2: 6 }, { x1: 0, y1: 6, x2: 0, y2: 1 },
      ],
      doors: [{ x: 4, y: 7, facing: 'h', kind: 'door' }],
    },
    {
      id: 'boss-room',
      name: 'Boss Room',
      category: 'Special / Dungeon',
      widthCells: 12,
      heightCells: 9,
      walls: [
        { x1: 0, y1: 0, x2: 12, y2: 0 }, { x1: 12, y1: 0, x2: 12, y2: 9 },
        { x1: 12, y1: 9, x2: 0, y2: 9 }, { x1: 0, y1: 9, x2: 0, y2: 0 },
      ],
      doors: [{ x: 6, y: 9, facing: 'h', kind: 'double' }],
      props: [{ kind: 'chest', x: 5, y: 3, w: 1, h: 1 }],
    },
    {
      id: 'cave-chamber',
      name: 'Cave Chamber',
      category: 'Special / Dungeon',
      widthCells: 9,
      heightCells: 8,
      walls: [
        { x1: 1, y1: 0, x2: 5, y2: 0 }, { x1: 5, y1: 0, x2: 8, y2: 1 },
        { x1: 8, y1: 1, x2: 9, y2: 4 }, { x1: 9, y1: 4, x2: 8, y2: 7 },
        { x1: 8, y1: 7, x2: 5, y2: 8 }, { x1: 5, y1: 8, x2: 2, y2: 8 },
        { x1: 2, y1: 8, x2: 0, y2: 6 }, { x1: 0, y1: 6, x2: 0, y2: 2 },
        { x1: 0, y1: 2, x2: 1, y2: 0 },
      ],
      doors: [{ x: 4, y: 8, facing: 'h', kind: 'opening' }],
    },
  ];

  function byId(id) {
    return PRESETS.find((entry) => String(entry.id || '') === String(id || '')) || null;
  }

  window.EditorStampPresets = Object.freeze({
    list: () => PRESETS.map((entry) => ({ ...entry })),
    byId,
  });
})();
