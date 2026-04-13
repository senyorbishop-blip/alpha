(function(){
  function renderLogFeed(env, logEntries, usersById) {
    const feed = env.document.getElementById('log-feed');
    if (!feed) return;
    feed.innerHTML = '';
    (Array.isArray(logEntries) ? logEntries : []).forEach(entry => {
      const enriched = { ...(entry || {}) };
      if (!enriched.role && enriched.user_id && usersById && usersById[enriched.user_id]) {
        enriched.role = usersById[enriched.user_id].role;
      }
      env.addLogEntry(enriched);
    });
  }
  window.AppUIChatHistory = { renderLogFeed };
})();
