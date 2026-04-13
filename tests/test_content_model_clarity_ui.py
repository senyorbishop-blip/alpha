from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_play_page_labels_distinguish_journal_moments_handouts_discoveries():
    src = _read('client/templates/play.html')
    assert '📖 Journal & Quests' in src
    assert 'Search journal notes and quest intel…' in src
    assert 'Journal:</strong> campaign notes, lore, NPC/location references, and shared quest briefs.' in src
    assert 'Model:</strong> Quests = objectives, Discoveries = clue reveals, Handouts = DM documents, Moments = quick timeline beats.' in src
    assert '📖</span>Moments' in src
    assert 'Moments are quick timeline beats from play' in src
    assert 'Party is your live snapshot: who is connected, who is up in initiative, and who needs help right now.' in src
    assert '📜</span>Handouts' in src
    assert 'Handouts are DM-issued documents.' in src
    assert 'Discoveries are clue drops' in src


def test_player_shell_dashboard_copy_separates_journal_moments_and_handouts():
    src = _read('client/static/js/ui/player_shell.js')
    assert '<strong>Moments</strong> for quick timeline beats, and <strong>Handouts</strong> for DM-issued documents.' in src
    assert 'Open <strong>Journal</strong> for quest progress/campaign notes, watch for <strong>Discoveries</strong> as clue cards, and check <strong>Handouts</strong> for DM-issued docs.' in src
    assert 'Journal & Quests<span class="btn-kicker">Canon, clues, quest progress</span>' in src
