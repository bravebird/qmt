import os
import configparser
import pytest


def test_start_mini_xt():
    from mini_xtclient.mini_xt import ProgramMonitor

    monitor = ProgramMonitor()
    monitor.monitor()

# def test_click_btn():
#     from mini_xtclient.pyauto import WinController
#     wc = WinController(window_title=)
