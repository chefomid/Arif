"""Register NiceGUI pages (import side-effect registers @ui.page)."""


def register_ui() -> None:
    """Import app page so NiceGUI registers the '/' route."""
    import app.ui.app_page  # noqa: F401
