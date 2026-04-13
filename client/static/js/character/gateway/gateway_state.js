(function initGatewayState(global) {
  const DEFAULT_STATE = {
    characters: [],
    selectedProfileId: null,
  };

  function createGatewayState(initialState) {
    const state = Object.assign({}, DEFAULT_STATE, initialState || {});
    const listeners = new Set();

    function emit() {
      const snapshot = {
        characters: Array.isArray(state.characters) ? state.characters.slice() : [],
        selectedProfileId: state.selectedProfileId,
      };
      listeners.forEach((listener) => {
        try {
          listener(snapshot);
        } catch (_) {
          // Never let one listener break the gateway lifecycle.
        }
      });
    }

    return {
      getState() {
        return {
          characters: Array.isArray(state.characters) ? state.characters.slice() : [],
          selectedProfileId: state.selectedProfileId,
        };
      },
      setCharacters(characters) {
        state.characters = Array.isArray(characters) ? characters.slice() : [];
        if (!state.characters.some((item) => item && item.id === state.selectedProfileId)) {
          state.selectedProfileId = null;
        }
        emit();
      },
      selectProfile(profileId) {
        state.selectedProfileId = profileId || null;
        emit();
      },
      subscribe(listener) {
        if (typeof listener !== 'function') return function noop() {};
        listeners.add(listener);
        return function unsubscribe() {
          listeners.delete(listener);
        };
      },
    };
  }

  global.CharacterGatewayState = {
    createGatewayState,
  };
})(window);
