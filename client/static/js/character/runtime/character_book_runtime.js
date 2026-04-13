(function initCharacterBookRuntime(global) {
  'use strict';

  var hooks = {};

  function setHooks(nextHooks) {
    hooks = (nextHooks && typeof nextHooks === 'object') ? nextHooks : {};
  }

  function createEnv() {
    if (!hooks || typeof hooks.createEnv !== 'function') return null;
    return hooks.createEnv();
  }

  function callBook(method, args) {
    if (!(global.AppUICharacterBook && typeof global.AppUICharacterBook[method] === 'function')) return;
    var env = createEnv();
    if (!env) return;
    global.AppUICharacterBook[method].apply(global.AppUICharacterBook, [env].concat(args || []));
  }

  function closeCharacterBook() {
    callBook('closeCharacterBook');
  }

  function openCharacterBook(page) {
    callBook('openCharacterBook', [(!page || page === 'overview') ? 'premiumsheet' : page]);
  }

  function goCharacterBookPage(page, instant) {
    callBook('goCharacterBookPage', [(page === 'overview' ? 'premiumsheet' : page), !!instant]);
  }

  function handleCharacterBookScroll() {
    callBook('handleCharacterBookScroll');
  }

  function updateCharacterBookTabs(page) {
    callBook('updateCharacterBookTabs', [page]);
  }

  function openCharacterLevelupPlanner() {
    callBook('openCharacterLevelupPlanner');
  }

  global.CharacterBookRuntime = {
    registerHooks: setHooks,
    closeCharacterBook: closeCharacterBook,
    openCharacterBook: openCharacterBook,
    goCharacterBookPage: goCharacterBookPage,
    handleCharacterBookScroll: handleCharacterBookScroll,
    updateCharacterBookTabs: updateCharacterBookTabs,
    openCharacterLevelupPlanner: openCharacterLevelupPlanner,
  };

  global.closeCharacterBook = closeCharacterBook;
  global.openCharacterBook = openCharacterBook;
  global.goCharacterBookPage = goCharacterBookPage;
  global.handleCharacterBookScroll = handleCharacterBookScroll;
  global.updateCharacterBookTabs = updateCharacterBookTabs;
  global.openCharacterLevelupPlanner = openCharacterLevelupPlanner;
})(window);
