from loggers import logger


def test_start_mini_xt():
    from mini_xtclient.mini_xt import ProgramMonitor
    import os
    import configparser

    project_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_dir, 'config', 'config.ini')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)

    if 'xt_client' not in config:
        raise KeyError('The section xt_client is missing in the configuration file.')

    app = ProgramMonitor(config_path)

    assert app.program_name == 'C:/e_trader/bin.x64/XtItClient.exe'
    assert app.process_name == 'XtItClient'
    assert app.check_interval == 10