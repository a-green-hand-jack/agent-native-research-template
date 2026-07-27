from project import template_status


def test_template_vertical_slice() -> None:
    assert template_status() == "ready"
