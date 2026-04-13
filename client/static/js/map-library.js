// map-library.js
// Tavern Tabletop — Map Library Scorer and Loader
// No dependencies. Pure JS. Global script.

(function() {
  'use strict';

  class MapLibrary {
    constructor() {
      this.maps = [];
      this.loaded = false;
    }

    // Load maps.json once on init
    async load(jsonPath) {
      jsonPath = jsonPath || '/static/data/maps.json';
      const res = await fetch(jsonPath);
      this.maps = await res.json();
      this.loaded = true;
      return this;
    }

    // Score a single map against form state
    // Returns integer score 0-100
    scoreMap(map, query) {
      var score = 0;

      // Scope match — most important (40 pts)
      if (map.scope === query.scope) score += 40;

      // Terrain overlap (up to 30 pts)
      if (query.terrain && query.terrain.length > 0) {
        var overlap = map.terrain.filter(function(t) { return query.terrain.indexOf(t) !== -1; }).length;
        score += Math.min(overlap * 15, 30);
      }

      // Style match (15 pts)
      if (map.style === query.style) score += 15;

      // Size match (10 pts)
      if (map.size === query.size) score += 10;

      // Tag bonus (up to 5 pts)
      if (query.tags && query.tags.length > 0) {
        var tagOverlap = map.tags.filter(function(t) { return query.tags.indexOf(t) !== -1; }).length;
        score += Math.min(tagOverlap * 2, 5);
      }

      return score;
    }

    // Return top N matches sorted by score
    // Returns array of { map, score }
    query(formState, topN) {
      topN = topN || 3;
      if (!this.loaded) {
        console.warn('[MapLibrary] Not loaded yet');
        return [];
      }

      var self = this;
      var scored = this.maps.map(function(map) {
        return { map: map, score: self.scoreMap(map, formState) };
      });

      return scored
        .sort(function(a, b) { return b.score - a.score; })
        .slice(0, topN)
        .filter(function(r) { return r.score > 0; });
    }

    // Get best single match
    best(formState) {
      var results = this.query(formState, 1);
      return results.length > 0 ? results[0] : null;
    }

    // Check if any good match exists (for AI fallback decision)
    hasSufficientMatch(formState, threshold) {
      threshold = threshold || 40;
      var best = this.best(formState);
      return best && best.score >= threshold;
    }

    // Get map by ID
    getById(id) {
      return this.maps.find(function(m) { return m.id === id; }) || null;
    }
  }

  window.MapLibrary = MapLibrary;
})();
