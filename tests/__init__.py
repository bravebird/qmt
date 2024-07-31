import os
import pytest
from pathlib import Path

from loggers import logger

@pytest.fixture(scope='session', autouse=True)
def set_working_directory():
    original_dir = os.getcwd()
    new_directory = Path(__file__).parent.parent.as_posix()

    if not os.path.exists(new_directory):
        os.makedirs(new_directory)

    os.chdir(new_directory)
    logger.debug(f"工作目录修改为: {new_directory}")
    print(f"工作目录修改为: {new_directory}")

    yield

    os.chdir(original_dir)
    logger.debug(f"工作目录还原为: {original_dir}")
    print(f"工作目录还原为: {original_dir}")