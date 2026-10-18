def test_gui_imports_without_tk_root():
    import generator.gui.app as app
    import generator.gui.tab_data as tab_data
    assert hasattr(app, "build_app") and hasattr(app, "main")
    assert hasattr(tab_data, "DataTab")


def test_settings_tab_exists():
    import generator.gui.tab_settings as t
    assert hasattr(t, "SettingsTab")


def test_template_tab_exists():
    import generator.gui.tab_template as t
    assert hasattr(t, "TemplateTab")
