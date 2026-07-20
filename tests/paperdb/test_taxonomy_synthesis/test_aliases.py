"""Test alias resolution, ambiguity handling, merge operations."""

import pytest
from .conftest import make_mock_repo

def test_normalize_alias():
    """Test that normalize_alias lowercases and strips punctuation."""
    from paperdb.taxonomy.aliases import normalize_alias

    assert normalize_alias("DFT") == "dft"
    assert normalize_alias("  Molecular Dynamics  ") == "molecular dynamics"
    assert normalize_alias("Density Functional Theory (DFT)") == "density functional theory dft"
    assert normalize_alias("NC-AFM") == "nc-afm"
    assert normalize_alias("") == ""

def test_resolve_to_canonical_exact_match():
    """Test that exact canonical name match works."""
    from paperdb.taxonomy.aliases import resolve_to_canonical

    repo = make_mock_repo()
    tag_id = repo.add_tag("density functional theory", "domain")

    results = resolve_to_canonical("density functional theory", repo, category="domain")
    assert len(results) == 1
    assert results[0]['id'] == tag_id
    assert results[0]['canonical_name'] == "density functional theory"

def test_resolve_to_canonical_via_alias():
    """Test that alias resolution works through tag_aliases table."""
    from paperdb.taxonomy.aliases import resolve_to_canonical, add_alias

    repo = make_mock_repo()
    tag_id = repo.add_tag("density functional theory", "domain")
    add_alias(tag_id, "DFT", repo)

    results = resolve_to_canonical("DFT", repo, category="domain")
    assert len(results) == 1
    assert results[0]['id'] == tag_id

def test_resolve_to_canonical_ambiguous():
    """Test that ambiguous aliases return multiple results (MD = molecular dynamics OR Markdown)."""
    from paperdb.taxonomy.aliases import resolve_to_canonical, add_alias

    repo = make_mock_repo()
    tag1 = repo.add_tag("molecular dynamics", "method")
    tag2 = repo.add_tag("markdown", "software")
    add_alias(tag1, "MD", repo)
    add_alias(tag2, "MD", repo)

    # Without category filter — should return both
    results = resolve_to_canonical("MD", repo)
    assert len(results) == 2

    # With category filter — should return only matching category
    results = resolve_to_canonical("MD", repo, category="method")
    assert len(results) == 1
    assert results[0]['canonical_name'] == "molecular dynamics"

    results = resolve_to_canonical("MD", repo, category="software")
    assert len(results) == 1
    assert results[0]['canonical_name'] == "markdown"

def test_resolve_to_canonical_no_match():
    """Test that unknown alias returns empty list."""
    from paperdb.taxonomy.aliases import resolve_to_canonical

    repo = make_mock_repo()
    results = resolve_to_canonical("nonexistent tag", repo)
    assert len(results) == 0

def test_add_alias_normalizes():
    """Test that add_alias normalizes before storing."""
    from paperdb.taxonomy.aliases import add_alias, normalize_alias

    repo = make_mock_repo()
    tag_id = repo.add_tag("test tag", "domain")
    add_alias(tag_id, "Test Tag!!!", repo)

    aliases = repo.get_tag_aliases_by_normalized(normalize_alias("Test Tag!!!"))
    assert len(aliases) == 1
    assert aliases[0]['tag_id'] == tag_id

def test_merge_tags_preserves_raw_name():
    """Test that merge_tags preserves raw_name in paper_tags."""
    from paperdb.taxonomy.aliases import merge_tags

    repo = make_mock_repo()
    canonical_id = repo.add_tag("density functional theory", "domain")
    alias_id = repo.add_tag("dft", "domain")

    paper_id = repo.add_paper("Test_2020_Merge")
    repo.add_paper_tag(paper_id, alias_id, source='llm', run_id=1, confidence=0.8, raw_name="DFT")

    merge_tags(canonical_id, alias_id, repo)

    # Check that paper_tag now points to canonical tag with raw_name preserved
    paper_tags = repo.conn.execute("SELECT * FROM paper_tags WHERE paper_id=? AND tag_id=?", (paper_id, canonical_id)).fetchall()
    assert len(paper_tags) == 1
    assert paper_tags[0]['raw_name'] == "DFT"  # raw_name preserved!

    # Old tag should be deleted
    old_tag = repo.get_tag_by_id(alias_id)
    assert old_tag is None

def test_merge_tags_moves_aliases():
    """Test that merge_tags moves tag_aliases from old tag to canonical."""
    from paperdb.taxonomy.aliases import merge_tags, add_alias

    repo = make_mock_repo()
    canonical_id = repo.add_tag("molecular dynamics", "method")
    alias_id = repo.add_tag("md simulation", "method")
    add_alias(alias_id, "MD simulations", repo)

    merge_tags(canonical_id, alias_id, repo)

    # Alias should now point to canonical tag
    from paperdb.taxonomy.aliases import normalize_alias
    aliases = repo.get_tag_aliases_by_normalized(normalize_alias("MD simulations"))
    assert len(aliases) == 1
    assert aliases[0]['tag_id'] == canonical_id

def test_merge_tags_same_tag_raises():
    """Test that merging a tag into itself raises ValueError."""
    from paperdb.taxonomy.aliases import merge_tags

    repo = make_mock_repo()
    tag_id = repo.add_tag("test", "domain")

    with pytest.raises(ValueError, match="Cannot merge a tag into itself"):
        merge_tags(tag_id, tag_id, repo)

def test_analyze_tag_distribution():
    """Test that analyze_tag_distribution returns correct stats."""
    from paperdb.taxonomy.aliases import analyze_tag_distribution

    repo = make_mock_repo()
    t1 = repo.add_tag("dft", "domain")
    t2 = repo.add_tag("molecular dynamics", "method")
    t3 = repo.add_tag("orphan tag", "domain")  # no paper_tags — orphan

    p1 = repo.add_paper("Paper_1")
    p2 = repo.add_paper("Paper_2")
    repo.add_paper_tag(p1, t1, source='llm', run_id=1, confidence=0.8, raw_name="DFT")
    repo.add_paper_tag(p2, t1, source='llm', run_id=1, confidence=0.8, raw_name="DFT")
    repo.add_paper_tag(p1, t2, source='llm', run_id=1, confidence=0.8, raw_name="MD")

    dist = analyze_tag_distribution(repo)

    assert dist['total_tags'] == 3
    assert dist['total_paper_tags'] == 3
    assert 'orphan tag' in dist['orphan_tags']
    assert 'domain' in dist['by_category']
    assert dist['by_category']['domain']['count'] == 2  # dft + orphan tag
    assert dist['by_category']['method']['count'] == 1  # molecular dynamics

def test_apply_clean_tags_rules():
    """Test that consolidation rules from clean_tags.py are applied correctly."""
    import tempfile, os
    from paperdb.taxonomy.aliases import apply_clean_tags_rules, resolve_to_canonical

    repo = make_mock_repo()
    # Create tags that should be consolidated
    repo.add_tag("dft", "domain")
    repo.add_tag("density functional theory", "domain")
    repo.add_tag("density functional theory (dft)", "domain")

    p1 = repo.add_paper("Paper_DFT")
    dft_id = repo.get_tag_by_name("dft", "domain")['id']
    repo.add_paper_tag(p1, dft_id, source='llm', run_id=1, confidence=0.8, raw_name="DFT")

    # Write a temporary rules file
    rules_content = '''
CONSOLIDATION_RULES = {
    "density functional theory (dft)": [
        r"density functional theory",
        r"\\bdft\\b"
    ],
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(rules_content)
        rules_path = f.name

    try:
        apply_clean_tags_rules(rules_path, repo)
        # After consolidation, "dft" and "density functional theory" should be merged
        # into "density functional theory (dft)"
        results = resolve_to_canonical("DFT", repo)
        assert len(results) >= 1
        # The canonical tag should be "density functional theory (dft)"
        canonical_names = [r['canonical_name'] for r in results]
        assert "density functional theory (dft)" in canonical_names
    finally:
        os.unlink(rules_path)
