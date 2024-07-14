import os

def test_working_directory():
    current_dir = os.getcwd()
    print(f"Current working directory during test: {current_dir}")
    assert 'new directory substring' in current_dir  # 确保期望的工作目录存在