from fermentd.web.markdown import find_recipe, render


def test_markdown_escapes_html_and_renders_the_subset():
    out = render(
        "## Day 0\n\nHello <script>x</script> **bold** `code`\n\n1. First\n2. Second\n\n- a\n- b\n", checkable=True
    )
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert '<h3 id="day-0">Day 0</h3>' in out
    assert "<strong>bold</strong>" in out and "<code>code</code>" in out
    assert out.count('type="checkbox"') == 2
    assert 'data-step="day-0-1"' in out
    assert "<ul>" in out and "<li>a</li>" in out


def test_recipe_paths_cannot_escape_the_repo():
    assert find_recipe("../../etc/passwd") is None
    assert find_recipe("/etc/passwd") is None
    assert find_recipe("docs/recipes/soda_cola.md") is not None
