from pathlib import Path


def test_door_popup_actions_do_not_send_full_props_save_before_ws_toggle_routes():
    src = Path('client/templates/play.html').read_text(encoding='utf-8')

    state_fn_start = src.index('function togglePropPopupDoorState() {')
    lock_fn_start = src.index('function togglePropPopupDoorLock() {')
    shop_fn_start = src.index('// ─── Shop prop actions')

    state_fn = src[state_fn_start:lock_fn_start]
    lock_fn = src[lock_fn_start:shop_fn_start]

    assert "sendWS({ type: 'door_toggle'" in state_fn
    assert 'saveEditorProps(true);' not in state_fn

    assert "sendWS({ type: 'door_lock_set'" in lock_fn
    assert 'saveEditorProps(true);' not in lock_fn
