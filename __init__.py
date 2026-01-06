from .rm_styler import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# This specific variable exposes the 'js' directory to ComfyUI
WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

print("\033[34mRM-Styler Nodes Loaded \033[92m(Success)\033[0m")