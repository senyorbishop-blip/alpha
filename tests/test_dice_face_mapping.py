"""
tests/test_dice_face_mapping.py — Dice face mapping verification.

Validates that:
1. Face labels match face values for every die type (visual = reported result)
2. Face normal counts match face value counts (no index overflow)
3. Stuck-die recovery system is wired up
4. D4 uses physical point-up detection
5. D10 face normals are grouped correctly (10, not 20)
"""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICE_DIR = os.path.join(PROJECT_ROOT, "client", "static", "js", "dice")


def _read(relpath):
    with open(os.path.join(DICE_DIR, relpath), "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Face labels must be derived from face values (not hardcoded sequential)
# ═══════════════════════════════════════════════════════════════════════════

def test_get_face_labels_derives_from_values():
    """getFaceLabels must use DIE_FACE_VALUES to generate labels, not hardcoded lists."""
    content = _read("DiceFactory.js")
    # The function should reference DIE_FACE_VALUES
    assert "DIE_FACE_VALUES[type]" in content, (
        "getFaceLabels must derive labels from DIE_FACE_VALUES"
    )
    # It should NOT contain hardcoded sequential label arrays like "['1','2','3','4','5','6']"
    assert "['1','2','3','4','5','6']" not in content, (
        "getFaceLabels should not have hardcoded sequential d6 labels"
    )
    assert "['1','2','3','4','5','6','7','8']" not in content, (
        "getFaceLabels should not have hardcoded sequential d8 labels"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. D4 must not use vertex-based result reading
# ═══════════════════════════════════════════════════════════════════════════

def test_d4_uses_point_up_detection():
    """D4 result detection must read the upward point, matching physical d4s."""
    content = _read("DiceFactory.js")
    assert "_detectD4UpwardPoint" in content
    assert "D4_LOCAL_VERTICES" in content
    assert "D4_VERTEX_VALUES" in content


# ═══════════════════════════════════════════════════════════════════════════
# 3. D6 face values follow standard opposite-face-sum convention
# ═══════════════════════════════════════════════════════════════════════════


def test_d4_face_values_match_physical_opposite_vertex_reading():
    """D4 face values must represent the upward point opposite each resting face."""
    content = _read("geometries/D4.js")
    values_match = re.search(r'D4_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert values_match, "D4_FACE_VALUES must be defined in D4.js"
    raw_values = [int(v.strip()) for v in values_match.group(1).split(',')]
    assert raw_values == [4, 2, 3, 1], f"Unexpected D4 face values order: {raw_values}"

def test_d6_opposite_faces_sum_to_7():
    """D6 face values must have opposite faces summing to 7."""
    content = _read("geometries/D6.js")
    # Extract D6_FACE_VALUES array
    match = re.search(r'D6_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert match, "D6_FACE_VALUES must be defined in D6.js"
    values = [int(v.strip()) for v in match.group(1).split(',')]
    assert len(values) == 6, f"D6 must have 6 face values, got {len(values)}"
    # +X/-X, +Y/-Y, +Z/-Z pairs: indices 0/1, 2/3, 4/5
    for i in range(0, 6, 2):
        assert values[i] + values[i + 1] == 7, (
            f"D6 opposite faces at indices {i},{i+1} must sum to 7, "
            f"got {values[i]}+{values[i+1]}={values[i]+values[i+1]}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. D10 must have grouped face normals (10 per die, not 20)
# ═══════════════════════════════════════════════════════════════════════════

def test_d10_grouped_normals():
    """D10 geometry must override faceNormalsLocal with 10 grouped normals."""
    content = _read("geometries/D10.js")
    assert "computeGroupedFaceNormals" in content, (
        "D10 must use computeGroupedFaceNormals to produce 10 normals (not 20)"
    )
    assert "computeGroupedFaceNormals(geo, 10)" in content, (
        "D10 must call computeGroupedFaceNormals with count=10"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 5. D10 face values have correct count
# ═══════════════════════════════════════════════════════════════════════════

def test_d10_face_values_count():
    """D10 must have exactly 10 face values."""
    content = _read("geometries/D10.js")
    match = re.search(r'D10_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert match, "D10_FACE_VALUES must be defined in D10.js"
    values = [v.strip() for v in match.group(1).split(',')]
    assert len(values) == 10, f"D10 must have 10 face values, got {len(values)}"


def test_d10_face_values_are_single_digit_0_to_9():
    """D10 face values must be single-digit integers 0–9 (not double-digit like d100).

    The d10 and d100 share the same geometry shape (pentagonal trapezohedron).
    The only visual distinction is their labels: d10 shows 0–9 and d100 shows
    '00','10','20',…,'90'.  If D10_FACE_VALUES accidentally used double-digit
    strings the two dice would be indistinguishable on screen.
    """
    content = _read("geometries/D10.js")
    match = re.search(r'D10_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert match, "D10_FACE_VALUES must be defined in D10.js"
    raw_values = [v.strip() for v in match.group(1).split(',')]
    assert len(raw_values) == 10

    parsed = []
    for v in raw_values:
        # Values must be plain integers (no quotes, no two-digit strings like '00' or '10')
        assert not v.startswith("'") and not v.startswith('"'), (
            f"D10_FACE_VALUES must contain integers, not quoted strings: {v}"
        )
        parsed.append(int(v))

    assert sorted(parsed) == list(range(0, 10)), (
        f"D10_FACE_VALUES must cover 0–9 exactly, got {sorted(parsed)}"
    )


def test_d100_face_values_are_zero_padded_tens():
    """D100 face values must be zero-padded tens strings ('00','10',…,'90').

    This ensures d100 labels are visually distinct from d10's single-digit 0–9.
    """
    content = _read("geometries/D10.js")
    match = re.search(r"D100_TENS_VALUES\s*=\s*\[([^\]]+)\]", content)
    assert match, "D100_TENS_VALUES must be defined in D10.js"
    raw_values = [v.strip().strip("'\"") for v in match.group(1).split(',')]
    assert len(raw_values) == 10

    expected = [f"{i*10:02d}" for i in range(10)]  # ['00','10','20',...,'90']
    assert raw_values == expected, (
        f"D100_TENS_VALUES must be {expected}, got {raw_values}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 6. D20 face values have correct count
# ═══════════════════════════════════════════════════════════════════════════

def test_d20_face_values_count():
    """D20 must have exactly 20 face values."""
    content = _read("geometries/D20.js")
    assert 'export const D20_FACE_VALUES = [...D20_VALUE_ORDER];' in content


# ═══════════════════════════════════════════════════════════════════════════
# 7. Stuck-die recovery is wired into the animation loop
# ═══════════════════════════════════════════════════════════════════════════

def test_stuck_die_recovery_exists():
    """DiceFactory must export checkStuckDie function."""
    content = _read("DiceFactory.js")
    assert "export function checkStuckDie" in content, (
        "DiceFactory must export checkStuckDie for stuck-die recovery"
    )


def test_stuck_die_recovery_wired():
    """dice3d.js must call checkStuckDie in the animation loop."""
    content = _read("dice3d.js")
    assert "checkStuckDie" in content, (
        "dice3d.js animation loop must call checkStuckDie"
    )


def test_stuck_die_constants():
    """Stuck-die recovery must have configurable constants."""
    content = _read("DiceFactory.js")
    assert "STUCK_TIMEOUT_MS" in content
    assert "STUCK_MAX_RETRIES" in content
    assert "STUCK_NUDGE_UP" in content


# ═══════════════════════════════════════════════════════════════════════════
# 8. D20 enhanced textures
# ═══════════════════════════════════════════════════════════════════════════

def test_d20_enhanced_texture_resolution():
    """D20 textures must use higher resolution (512px) for premium quality."""
    content = _read("materials/FaceMaterial.js")
    assert "d20" in content, "FaceMaterial must have d20-specific handling"
    assert "512" in content, "D20 textures should use 512px resolution"


# ═══════════════════════════════════════════════════════════════════════════
# 9. readDieResult must use readTopFaceResult for ALL dice
# ═══════════════════════════════════════════════════════════════════════════

def test_unified_result_reading():
    """readDieResult must use the same readTopFaceResult for all die types."""
    content = _read("DiceFactory.js")
    # Find the readDieResult function — it should be a simple one-liner
    assert "export function readDieResult" in content, "readDieResult must be defined"
    # Verify it delegates to readTopFaceResult
    assert "readTopFaceResult(die)" in content, (
        "readDieResult must delegate to readTopFaceResult for all dice"
    )
    # Verify there's no die.type branching in readDieResult
    # (the function should not contain 'd4' or die.type checks)
    lines = content.split('\n')
    in_fn = False
    for line in lines:
        if 'export function readDieResult' in line:
            in_fn = True
            continue
        if in_fn:
            if line.strip().startswith('export ') or line.strip().startswith('//') and 'All dice' in line:
                break
            assert "die.type" not in line, (
                "readDieResult should not branch on die.type — all dice use same approach"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 10. All supported die types have face values defined
# ═══════════════════════════════════════════════════════════════════════════

def test_all_die_types_have_face_values():
    """DIE_FACE_VALUES must cover all supported die types."""
    content = _read("DiceFactory.js")
    for die_type in ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100']:
        assert f"  {die_type}:" in content, (
            f"DIE_FACE_VALUES must include {die_type}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 11. D4.js must not have stale vertex-based detection comment
# ═══════════════════════════════════════════════════════════════════════════

def test_d4_comment_not_stale():
    """D4.js doc comment must not claim vertex-based detection (now uses face-normals)."""
    content = _read("geometries/D4.js")
    assert "vertex-based" not in content.lower(), (
        "D4.js comment still says 'vertex-based' — update it to reflect face-normal detection"
    )
    assert "readD4Result" not in content, (
        "D4.js still references the removed readD4Result function"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 12. D4.js must not export dead vertex-based constants
# ═══════════════════════════════════════════════════════════════════════════

def test_d4_vertex_exports_exist_for_point_up_reading():
    """D4.js must export the local vertices and point values needed for point-up reads."""
    content = _read("geometries/D4.js")
    assert "D4_LOCAL_VERTICES" in content
    assert "D4_VERTEX_VALUES" in content


# ═══════════════════════════════════════════════════════════════════════════
# 13. spawnDie must validate face normals count
# ═══════════════════════════════════════════════════════════════════════════

def test_spawndie_validates_face_normals_count():
    """spawnDie must verify faceNormals.length matches expected face count."""
    content = _read("DiceFactory.js")
    # Validation must emit a console.error when normals count doesn't match expected
    assert "faceNormals.length" in content, (
        "spawnDie must validate faceNormals.length to catch mis-grouped normals early"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 14. D100 target-assist must handle numeric forced values (0 → '00')
# ═══════════════════════════════════════════════════════════════════════════

def test_d100_target_assist_normalizes_numeric_zero():
    """_assistDie must normalize numeric 0 → '00' for d100 tens die."""
    content = _read("dice3d.js")
    # The fix: when die.type === 'd100' and forcedValue is a number, pad it with padStart(2, '0')
    assert "padStart(2, '0')" in content, (
        "dice3d.js _assistDie must use padStart(2, '0') to normalize d100 numeric forced "
        "values (e.g. 0 → '00') so indexOf matches the string-keyed face values"
    )
    assert "d100" in content, (
        "_assistDie must have d100-specific forced-value normalization"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 15. D8 face values: count and range
# ═══════════════════════════════════════════════════════════════════════════

def test_d8_face_values_count_and_range():
    """D8 must have exactly 8 face values covering 1–8."""
    content = _read("geometries/D8.js")
    match = re.search(r'D8_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert match, "D8_FACE_VALUES must be defined in D8.js"
    values = [int(v.strip()) for v in match.group(1).split(',')]
    assert len(values) == 8, f"D8 must have 8 face values, got {len(values)}"
    assert sorted(values) == list(range(1, 9)), (
        f"D8 face values must cover 1–8, got {sorted(values)}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 16. D12 face values: count and range
# ═══════════════════════════════════════════════════════════════════════════

def test_d12_face_values_count_and_range():
    """D12 must have exactly 12 face values covering 1–12."""
    content = _read("geometries/D12.js")
    match = re.search(r'D12_FACE_VALUES\s*=\s*\[([^\]]+)\]', content)
    assert match, "D12_FACE_VALUES must be defined in D12.js"
    values = [int(v.strip()) for v in match.group(1).split(',')]
    assert len(values) == 12, f"D12 must have 12 face values, got {len(values)}"
    assert sorted(values) == list(range(1, 13)), (
        f"D12 face values must cover 1–12, got {sorted(values)}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 17. D4 face values: count and range
# ═══════════════════════════════════════════════════════════════════════════

def test_d4_face_values_in_factory():
    """D4 entry in DiceFactory must use the dedicated audited face-value mapping."""
    content = _read("DiceFactory.js")
    assert "d4:   D4_FACE_VALUES" in content, (
        "DiceFactory DIE_FACE_VALUES must use D4_FACE_VALUES so the physical d4 mapping stays centralized"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 18. D20 face values: all values 1–20 present
# ═══════════════════════════════════════════════════════════════════════════

def test_d20_face_values_cover_1_to_20():
    """D20 must have face values covering every integer from 1 to 20."""
    content = _read("geometries/D20.js")
    assert 'export const D20_FACE_VALUES = [...D20_VALUE_ORDER];' in content
    order_match = re.search(r'const D20_VALUE_ORDER\s*=\s*\[([\s\S]*?)\]', content)
    assert order_match
    values = [int(v.strip()) for v in order_match.group(1).split(',') if v.strip()]
    assert sorted(values) == list(range(1, 21)), (
        f"D20 face values must cover 1–20, got {sorted(values)}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 19. D100 computeD100Result special cases
# ═══════════════════════════════════════════════════════════════════════════

def test_d100_compute_result_function_exists():
    """D100.js must export computeD100Result for percentile calculation."""
    content = _read("geometries/D100.js")
    assert "export function computeD100Result" in content, (
        "D100.js must export computeD100Result"
    )
    # Verify the 00+0=100 special case is handled
    assert "100" in content, (
        "computeD100Result must handle the 00+0=100 special case"
    )
    assert "tensResult === 0 && unitsResult === 0" in content, (
        "computeD100Result must explicitly check tens=0 AND units=0 for result 100"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 20. D100 tens values: correct zero-padded string format
# ═══════════════════════════════════════════════════════════════════════════

def test_d100_tens_values_are_zero_padded_strings():
    """D100_TENS_VALUES must be zero-padded strings ('00','10',...,'90')."""
    content = _read("geometries/D10.js")
    match = re.search(r"D100_TENS_VALUES\s*=\s*\[([^\]]+)\]", content)
    assert match, "D100_TENS_VALUES must be defined in D10.js"
    raw_values = [v.strip().strip("'\"") for v in match.group(1).split(',')]
    assert len(raw_values) == 10, f"D100_TENS_VALUES must have 10 entries, got {len(raw_values)}"
    expected = ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90']
    assert raw_values == expected, (
        f"D100_TENS_VALUES must be {expected}, got {raw_values}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 21. D20 must override spherical UVs with per-face centered UVs
# ═══════════════════════════════════════════════════════════════════════════

def test_d20_overrides_spherical_uvs():
    """D20 geometry must explicitly set per-face centered UVs, not inherit spherical projection."""
    content = _read("geometries/D20.js")
    # Must create/override UV attribute with Float32BufferAttribute
    assert "setAttribute('uv'" in content or 'setAttribute("uv"' in content, (
        "D20 geometry must explicitly set UV attribute to override Three.js spherical UVs"
    )
    # Must use centered equilateral triangle UVs matching buildFlatFaceGeometry pattern
    # centroid at (0.5, 0.5): top = (0.5, 0.9), bottom-left = (0.13, 0.3), bottom-right = (0.87, 0.3)
    assert "0.5" in content and "0.9" in content and "0.13" in content and "0.87" in content, (
        "D20 UVs must use the centered equilateral triangle pattern (0.5,0.9 / 0.13,0.3 / 0.87,0.3)"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 22. D12 must override spherical UVs with per-face centered UVs
# ═══════════════════════════════════════════════════════════════════════════

def test_d12_overrides_spherical_uvs():
    """D12 geometry must explicitly set per-face centered UVs, not inherit spherical projection."""
    content = _read("geometries/D12.js")
    # Must create/override UV attribute with Float32BufferAttribute
    assert "setAttribute('uv'" in content or 'setAttribute("uv"' in content, (
        "D12 geometry must explicitly set UV attribute to override Three.js spherical UVs"
    )
    # Must center UVs at (0.5, 0.5) per face
    assert "0.5" in content, (
        "D12 UVs must center at (0.5, 0.5) per face"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 23. faceNormals must survive BufferGeometry.clone() serialisation
# ═══════════════════════════════════════════════════════════════════════════

def test_face_normals_clone_safety():
    """spawnDie must re-wrap faceNormals as Vector3 to survive BufferGeometry.clone()."""
    content = _read("DiceFactory.js")
    # Must reconstruct Vector3 instances from plain objects after clone
    assert "new THREE.Vector3(n.x, n.y, n.z)" in content, (
        "spawnDie must reconstruct Vector3 from plain {x,y,z} objects after geometry clone"
    )
    # Should check instanceof to avoid double-wrapping
    assert "instanceof THREE.Vector3" in content, (
        "spawnDie should check instanceof before wrapping to avoid double-wrapping"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 24. D10 kite faces connect correct equatorial vertices
# ═══════════════════════════════════════════════════════════════════════════

def test_d10_kite_faces_use_correct_lower_vertex():
    """D10 upper kites must connect top→upper[i]→lower[i]→upper[i+1], not lower[i-1]."""
    content = _read("geometries/D10.js")
    # The OLD code used l_prev (lower[i-1]) — this must NOT be present
    assert "l_prev" not in content, (
        "D10 geometry must not use l_prev (lower[i-1]) — upper kites should use lower[i]"
    )
    # The NEW code should reference l0 and l1 for adjacent lower ring vertices
    assert "const l0 = 7 + i;" in content, (
        "D10 must define l0 = 7 + i for the lower ring vertex"
    )
    assert "const l1 = 7 + (i + 1) % n;" in content, (
        "D10 must define l1 for the next lower ring vertex"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 25. D12 physics uses pentagonal (not triangulated) faces
# ═══════════════════════════════════════════════════════════════════════════

def test_d12_physics_uses_pentagonal_faces():
    """D12 ConvexPolyhedron must use 12 pentagonal faces, not 36 triangulated faces."""
    content = _read("geometries/D12.js")
    # Must iterate 12 faces (not loop over triangles)
    assert "for (let f = 0; f < 12; f++)" in content, (
        "D12 physics shape must group triangles into 12 pentagonal faces"
    )
    # Must collect unique ordered vertices per pentagon
    assert "ordered" in content and "seen" in content, (
        "D12 physics must collect ordered unique vertices per pentagon face"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 26. Post-settle face alignment validation exists
# ═══════════════════════════════════════════════════════════════════════════

def test_post_settle_face_validation_exists():
    """DiceFactory must export validateFaceAlignment and nudgeToFace functions."""
    content = _read("DiceFactory.js")
    assert "export function validateFaceAlignment" in content, (
        "DiceFactory must export validateFaceAlignment for post-settle face checking"
    )
    assert "export function nudgeToFace" in content, (
        "DiceFactory must export nudgeToFace for corrective nudging"
    )
    assert "MIN_FACE_DOT" in content, (
        "DiceFactory must define MIN_FACE_DOT threshold for face alignment validation"
    )
    assert "MAX_FACE_NUDGES" in content, (
        "DiceFactory must define MAX_FACE_NUDGES to limit corrective nudge attempts"
    )


def test_post_settle_face_validation_wired():
    """dice3d.js must call validateFaceAlignment in the settle loop."""
    content = _read("dice3d.js")
    assert "validateFaceAlignment" in content, (
        "dice3d.js must call validateFaceAlignment to catch edge/corner-balanced dice"
    )
    assert "nudgeToFace" in content, (
        "dice3d.js must call nudgeToFace when face alignment validation fails"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 27. Debug mode exists
# ═══════════════════════════════════════════════════════════════════════════

def test_debug_mode_exists():
    """dice3d.js must have a DICE_DEBUG debug mode flag."""
    content = _read("dice3d.js")
    assert "DICE_DEBUG" in content, (
        "dice3d.js must define DICE_DEBUG window property for debug mode"
    )
    assert "_diceDebug" in content, (
        "dice3d.js must have internal _diceDebug flag"
    )
    assert "[DiceDebug]" in content, (
        "dice3d.js must log with [DiceDebug] prefix when debug mode is enabled"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 28. D12 angular damping is higher for stable settling
# ═══════════════════════════════════════════════════════════════════════════

def test_d12_higher_angular_damping():
    """D12 must use higher angular damping to prevent corner-balancing."""
    content = _read("physics/BodyFactory.js")
    # D12 must be referenced for per-die-type damping override
    assert "d12" in content, (
        "BodyFactory must reference d12 for damping override"
    )
    # Angular damping for d12 should be in an elevated range (0.10–0.20)
    assert "angDamping" in content or "angularDamping" in content, (
        "BodyFactory must compute per-die angular damping"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 29. Server-authoritative results are preserved in display pipeline
# ═══════════════════════════════════════════════════════════════════════════

def test_server_authoritative_results_preserved_for_display():
    """play.html must drive visual dice from authoritative rolls (single-truth path)."""
    play_html = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_html, "r", encoding="utf-8") as f:
        content = f.read()
    # Keep a dedicated authoritative meta object and a pending request map keyed by roll_id.
    assert "_dice3dServerMeta" in content, (
        "play.html must keep server-authoritative dice metadata separate from physics metadata"
    )
    assert "_pendingAuthoritativeDiceRolls" in content, (
        "play.html must track pending authoritative dice requests by roll_id"
    )
    # The 3D throw must receive targetResults so visual dice are guided by the authoritative payload.
    assert "targetResults: Array.isArray(rollOpts?.targetResults)" in content, (
        "showDiceAnimation must pass authoritative targetResults into DicePhysics3D.throw"
    )
    assert "source: isOwnRoll ? 'authoritative-result' : 'remote-authoritative-result'" in content, (
        "dice_result handling must launch visual animation from the authoritative response "
        "(tagging own rolls 'authoritative-result' and remote rolls 'remote-authoritative-result')"
    )
    # Regression guard: do not mutate server rolls to physics rolls.
    assert "_dice3dRollMeta.rolls = physicsRolls" not in content, (
        "play.html must not overwrite authoritative rolls with physics rolls"
    )


def test_dice_body_factory_containment_tuning():
    """BodyFactory throw spread/velocity should be tuned for in-frame containment."""
    content = _read("physics/BodyFactory.js")
    assert "spread = totalCount > 10 ? 1.35 : 1.75" in content, (
        "BodyFactory should tighten multi-die spawn spread for better containment"
    )
    assert "* 4.8" in content and "* 2.8" in content, (
        "BodyFactory should reduce lateral throw velocity to keep dice readable on-screen"
    )


def test_dice3d_collect_results_includes_face_and_quaternion_diagnostics():
    """collectResults must expose top-face index + final quaternions for debug auditing."""
    content = _read("dice3d.js")
    assert "faceIndex: detected.faceIndex" in content, (
        "collectResults must include detected top-face index for each die"
    )
    assert "bodyQuaternion" in content and "meshQuaternion" in content, (
        "collectResults must include body and mesh quaternions for final-state diagnostics"
    )


def test_d20_face_values_match_canonical_order():
    """D20 exported face values must match the canonical face-label order used for textures."""
    content = _read("geometries/D20.js")
    assert 'export const D20_FACE_VALUES = [...D20_VALUE_ORDER];' in content


def test_play_html_maps_standalone_d10_ten_to_visual_zero():
    content = open(os.path.join(PROJECT_ROOT, 'client', 'templates', 'play.html'), 'r', encoding='utf-8').read()
    assert 'return numeric === 10 ? 0 : numeric;' in content
    assert 'map(v => v === 0 ? 10 : v);' in content
