# PyInstaller hook for llama-cpp-python >= 0.3.x
# Collects the llama_cpp/lib/*.dll files and the llama_cpp/lib/*.so files.
from PyInstaller.utils.hooks import collect_data_files

# Collect everything in llama_cpp/lib/ as data
datas = collect_data_files('llama_cpp', includes=['lib/*.dll', 'lib/*.so', 'lib/*.dylib'])
