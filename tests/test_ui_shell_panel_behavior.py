from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_tabs_module_updates_accessibility_and_active_shell_context():
    src = _read('client/static/js/ui/tabs.js')
    assert "btn.setAttribute('aria-selected', isVisible && isActive ? 'true' : 'false');" in src
    assert "pane.setAttribute('aria-hidden', isVisible && isActive ? 'false' : 'true');" in src
    assert "if (shell) shell.dataset.activeTab = activeTab;" in src


def test_tabs_module_resets_non_chat_pane_scroll_on_switch():
    src = _read('client/static/js/ui/tabs.js')
    assert 'function alignPaneScroll(tab, env)' in src
    assert "if (tab === 'log') return;" in src
    assert 'pane.scrollTop = 0;' in src


def test_play_page_has_scroll_gutter_and_dense_panel_grouping_polish():
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _read('client/static/css/play.css')
    assert 'scrollbar-gutter: stable both-edges;' in src
    assert '#combat-move-row,' in src
    assert '#combat-weapon-tray,' in src
    assert '#party-loot-log {' in src
    assert '#sidebar-right[data-active-tab="combat"] #right-panel-context-chip {' in src


def test_viewers_is_only_a_party_subsection_not_a_tab():
    src = _read('client/templates/play.html')
    assert 'id="party-roster-tab-viewers"' in src
    assert 'data-party-roster-view="viewers"' in src
    assert 'id="party-presence-summary"' in src
    assert 'id="party-presence-count"' in src
    assert 'id="viewer-presence-count"' in src
    assert 'class="viewer-tools-stack"' in src
    assert 'id="party-viewers-host"' in src
    assert 'id="viewers-panel"' in src
    assert 'id="rtab-viewers"' not in src
    assert 'id="rtab-pane-viewers"' not in src
    assert "switchRTab('viewers')" not in src
    assert "if (tab === 'viewers')" not in src


def test_tabs_module_no_longer_tracks_legacy_tools_dropdown():
    src = _read('client/static/js/ui/tabs.js')
    assert "triggerSelector: '#rtab-dropdown-library'" in src
    assert "triggerSelector: '#rtab-dropdown-tools'" not in src
    assert "menuSelector: '#rtab-menu-tools'" not in src



def test_editor_asset_manifest_versions_file_paths_for_refreshes():
    src = Path('client/static/js/editor/assets.js').read_text(encoding='utf-8')
    assert 'function versionAssetPath(path, version)' in src
    assert 'function applyManifestVersion(asset, version)' in src
    assert 'applyManifestVersion(asset, version)' in src
