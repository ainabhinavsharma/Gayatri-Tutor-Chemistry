"""Runtime hook: set LLAMA_CPP_LIB_PATH so llama_cpp finds its DLLs in the frozen bundle."""
import os
import sys

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Point llama_cpp to its lib/ folder inside _MEIPASS
    llama_lib_path = os.path.join(sys._MEIPASS, 'llama_cpp', 'lib')
    if os.path.isdir(llama_lib_path):
        os.environ['LLAMA_CPP_LIB_PATH'] = llama_lib_path
        # Also add to DLL search path for Windows
        if sys.platform == 'win32':
            os.add_dll_directory(llama_lib_path)
