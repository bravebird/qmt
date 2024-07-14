import os

def test_working_directory():
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    assert 'qmt' in current_dir  # 确保工作目录包含预期路径