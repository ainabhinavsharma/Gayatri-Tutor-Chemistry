from app.windows.main_window import MainWindow


def test_sub_bridges_registered(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    channel = window._channel

    assert "chat_bridge" in channel.registeredObjects()
    assert "settings_bridge" in channel.registeredObjects()
    assert "provider_bridge" in channel.registeredObjects()
    assert "model_bridge" in channel.registeredObjects()
    assert "window_bridge" in channel.registeredObjects()

    chat = channel.registeredObjects()["chat_bridge"]
    assert not hasattr(chat, "save_provider_key")

    settings = channel.registeredObjects()["settings_bridge"]
    errors = []
    settings.error.connect(lambda msg: errors.append(msg))

    settings.set_setting("UNKNOWN_HACKER_KEY", "value")
    assert len(errors) == 1
    assert "Unknown setting key" in errors[0]

def test_settings_facade_backward_compat(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    channel = window._channel
    bridge = channel.registeredObjects()["bridge"]

    assert hasattr(bridge, "set_setting")
    assert hasattr(bridge, "send_message")
