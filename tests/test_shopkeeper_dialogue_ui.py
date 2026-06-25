import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _node(script: str):
    code = f"""
const fs = require('fs');
const vm = require('vm');
global.window = global;
{script}
"""
    out = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_shopkeeper_dialogue_haggle_fail_is_stable_and_in_character():
    result = _node(r'''
vm.runInThisContext(fs.readFileSync('client/static/js/ui/shopkeeper_dialogue.js', 'utf8'));
const ctx = { shop_id: 'shop-gruff-1', personality: 'gruff', shop_type: 'blacksmith' };
const first = window.ShopkeeperDialogue.say('haggle_fail', ctx);
const second = window.ShopkeeperDialogue.say('haggle_fail', ctx);
console.log(JSON.stringify({ first, second, stable: first === second }));
''')
    assert result['stable'] is True
    assert result['first']
    assert any(word in result['first'].lower() for word in ['price', 'charity', 'offer', 'bargaining'])


def test_dialogue_disabled_renders_no_speech_strip():
    result = _node(r'''
const created = [];
const modal = { querySelector: () => ({ appendChild: (node) => created.push(node) }) };
global.document = {
  getElementById: (id) => id === 'dnd-shop-view' ? modal : null,
  createElement: (tag) => ({ tag, innerHTML: '', className: '', querySelector: () => ({ addEventListener() {}, innerHTML: '' }) }),
  head: { appendChild() {} }
};
vm.runInThisContext(fs.readFileSync('client/static/js/ui/shopkeeper_dialogue.js', 'utf8'));
const text = window.ShopkeeperDialogue.say('greeting', { shop_id: 'disabled-shop', dialogue_enabled: false });
console.log(JSON.stringify({ text, rendered: created.length }));
''')
    assert result == {'text': '', 'rendered': 0}


def test_buying_item_triggers_purchase_line_only_from_purchase_result():
    src = Path('client/static/js/editor/shop_view.js').read_text(encoding='utf-8')
    assert "say('purchase'" in src
    assert src.count("say('purchase'") == 1
    buy_body = src.split('function _buy(itemId)', 1)[1].split('function _haggle', 1)[0]
    assert "say('purchase'" not in buy_body
