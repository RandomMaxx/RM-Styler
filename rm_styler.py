import json
import pathlib
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Union
from aiohttp import web

import server # Import ComfyUI Server to create API routes

# Setup logging
logger = logging.getLogger("RMStyler")

class Template:
    """Represents a single style template with prompt manipulation logic."""
    def __init__(self, prompt: str, negative_prompt: str, **kwargs: Any) -> None:
        self.prompt = prompt
        self.negative_prompt = negative_prompt

    def replace_prompts(self, positive_prompt: str, negative_prompt: str) -> Tuple[str, str]:
        """Simple replacement (Legacy/Fast mode)."""
        pos_res = self.prompt.replace('{prompt}', positive_prompt)
        neg_res = ', '.join(filter(None, (self.negative_prompt, negative_prompt)))
        return pos_res, neg_res

    def apply_weighted_style(self, current_positive: str, current_negative: str, 
                             enable_pos: bool, enable_neg: bool, weight: float) -> Tuple[str, str]:
        """
        Applies style with weighting. 
        If weight == 1.0, it avoids adding (style:1.0) syntax.
        """
        
        # --- Positive Prompt Logic ---
        pos_result = current_positive
        
        if enable_pos:
            # Split around {prompt} to weight only the style parts
            parts = self.prompt.split('{prompt}')
            
            styled_parts = []
            for part in parts:
                part = part.strip()
                if not part:
                    styled_parts.append("")
                    continue
                
                # Only apply weight syntax if strictly necessary
                if weight != 1.0:
                    styled_parts.append(f"({part}:{round(weight, 2)})")
                else:
                    styled_parts.append(part)

            # Reassemble: Prefix + UserPrompt + Suffix
            if len(parts) == 2:
                # Standard case: "style_prefix {prompt} style_suffix"
                components = [styled_parts[0], current_positive, styled_parts[1]]
                pos_result = ' '.join(filter(None, components))
            else:
                # Fallback for templates without {prompt} or multiple {prompt}s
                # Wraps the entire replaced string if weighted
                temp_res = self.prompt.replace('{prompt}', current_positive)
                if weight != 1.0:
                    pos_result = f"({temp_res}:{round(weight, 2)})"
                else:
                    pos_result = temp_res

        # --- Negative Prompt Logic ---
        neg_result = current_negative
        
        if enable_neg and self.negative_prompt:
            clean_neg = self.negative_prompt.strip()
            
            # Apply weight to the added negative style
            if weight != 1.0:
                clean_neg = f"({clean_neg}:{round(weight, 2)})"
            
            neg_result = ', '.join(filter(None, (clean_neg, current_negative)))
            
        return pos_result, neg_result


class StylerData:
    """Singleton to manage loading style templates."""
    def __init__(self, datadir: pathlib.Path | None = None) -> None:
        self._data: Dict[str, Dict[str, Template]] = defaultdict(dict)
        self.category_map: Dict[str, List[str]] = defaultdict(list)
        self.all_styles_list: List[str] = []      # For Multi-node (Category: Name)
        self.all_style_names: set = set()         # For Single-node validation (Name only)

        if datadir is None:
            datadir = pathlib.Path(__file__).parent / 'data'
            
        if not datadir.exists():
            logger.warning(f"Data directory not found: {datadir}")
            return

        for file_path in sorted(datadir.glob('*/*.json')):
            if file_path.name.startswith('.'): continue
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    content = json.load(f)
                group = file_path.parent.name
                for template in content:
                    if 'name' in template and 'prompt' in template:
                        t_name = template['name']
                        self._data[group][t_name] = Template(**template)
                        self.category_map[group].append(t_name)
                        
                        # Populate lists for validation
                        self.all_styles_list.append(f"{group}: {t_name}")
                        self.all_style_names.add(t_name)
                        
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                
        self.all_styles_list.sort()

    def get_template_by_flat_key(self, flat_key: str) -> Template | None:
        if not flat_key or flat_key == "None": return None
        try:
            group, name = flat_key.split(": ", 1)
            return self._data[group][name]
        except (ValueError, KeyError):
            return None

styler_data = StylerData()

# --- API ROUTE FOR JAVASCRIPT ---
@server.PromptServer.instance.routes.get("/rm_styler/data")
async def get_styler_data(request):
    return web.json_response(styler_data.category_map)


class RMStyler:
    """
    Styler with Dynamic JS update and Prompt Weighting.
    """
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        categories = sorted(list(styler_data.category_map.keys()))
        
        # VALIDATION FIX: 
        # We populate 'style' with ALL possible style names from ALL categories.
        # This ensures that when JS sets the value to "Neon", the backend validates it as a known option.
        all_styles = sorted(list(styler_data.all_style_names))
        
        return {
            "required": {
                "text_positive": ("STRING", {"default": "", "multiline": True}),
                "text_negative": ("STRING", {"default": "", "multiline": True}),
                "category": (categories, ), 
                "style": (all_styles, ),  # <--- FIXED HERE
                "weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
                "log_prompt": ("BOOLEAN", {"default": True, "label_on": "Yes", "label_off": "No"}),
            },
        }

    RETURN_TYPES = ('STRING', 'STRING',)
    RETURN_NAMES = ('text_positive', 'text_negative',)
    FUNCTION = 'prompt_styler'
    CATEGORY = 'RM Nodes/Styler'

    def prompt_styler(self, text_positive: str, text_negative: str, category: str, style: str, weight: float, log_prompt: bool) -> Tuple[str, str]:
        # Validation checks
        if category not in styler_data._data:
            return text_positive, text_negative
            
        # Even though validation passed, we must check if the style belongs to THIS category
        # because the input list contains styles from ALL categories.
        if style not in styler_data._data[category]:
            logger.warning(f"Style '{style}' not found in category '{category}'. Skipping.")
            return text_positive, text_negative

        template = styler_data._data[category][style]
        
        pos, neg = template.apply_weighted_style(
            current_positive=text_positive,
            current_negative=text_negative,
            enable_pos=True, 
            enable_neg=True,
            weight=weight
        )

        pos = re.sub(r'\s+', ' ', pos).strip()
        neg = re.sub(r'\s+', ' ', neg).strip()

        if log_prompt:
            print(f"[RMStyler] Applied: {category} -> {style} (w={weight})")

        return pos, neg


class RMStylerMultiBase:
    """Base class for Multi-Styler nodes. Defines logic, subclasses define slot count."""
    
    _slot_count = 6 # Default, overridden by subclasses

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        style_options = ["None"] + styler_data.all_styles_list
        
        inputs = {
            "required": {
                "text_positive": ("STRING", {"default": "", "multiline": True}),
                "text_positive_weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
                "text_negative": ("STRING", {"default": "", "multiline": True}),
                "text_negative_weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
            }
        }
        
        # Dynamically create inputs based on _slot_count
        for i in range(1, cls._slot_count + 1):
            inputs["required"][f"style_{i}"] = (style_options, {"default": "None"})
            inputs["required"][f"style_{i}_weight"] = ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1})
            inputs["required"][f"style_{i}_pos_on"] = ("BOOLEAN", {"default": True, "label_on": "Pos: On", "label_off": "Pos: Off"})
            inputs["required"][f"style_{i}_neg_on"] = ("BOOLEAN", {"default": True, "label_on": "Neg: On", "label_off": "Neg: Off"})

        inputs["required"]["log_prompt"] = ("BOOLEAN", {"default": True, "label_on": "Yes", "label_off": "No"})
        
        return inputs

    RETURN_TYPES = ('STRING', 'STRING',)
    RETURN_NAMES = ('text_positive', 'text_negative',)
    FUNCTION = 'apply_multi_styles'
    CATEGORY = 'RM Nodes/Styler'

    def apply_multi_styles(self, text_positive: str, text_positive_weight: float, 
                           text_negative: str, text_negative_weight: float, 
                           log_prompt: bool, **kwargs) -> Tuple[str, str]:
        
        # Apply Base Weights
        pos = text_positive.strip()
        if pos and text_positive_weight != 1.0:
            pos = f"({pos}:{round(text_positive_weight, 2)})"

        neg = text_negative.strip()
        if neg and text_negative_weight != 1.0:
            neg = f"({neg}:{round(text_negative_weight, 2)})"

        # Iterate Styles in REVERSE (Max Slot -> 1)
        # Inner-most style is applied first (Max Slot), Outer-most last (Slot 1)
        for i in range(self._slot_count, 0, -1):
            style_key = kwargs.get(f"style_{i}")
            
            if style_key and style_key != "None":
                template = styler_data.get_template_by_flat_key(style_key)
                
                if template:
                    weight = kwargs.get(f"style_{i}_weight", 1.0)
                    pos_on = kwargs.get(f"style_{i}_pos_on", True)
                    neg_on = kwargs.get(f"style_{i}_neg_on", True)
                    
                    pos, neg = template.apply_weighted_style(
                        current_positive=pos,
                        current_negative=neg,
                        enable_pos=pos_on,
                        enable_neg=neg_on,
                        weight=weight
                    )

        # Cleanup
        pos = re.sub(r'\s+', ' ', pos).strip()
        pos = re.sub(r'\s,\s', ', ', pos)
        pos = pos.replace(' . . ', ' . ')
        neg = re.sub(r'\s+', ' ', neg).strip()
        neg = re.sub(r'\s,\s', ', ', neg)

        if log_prompt:
            print(f"[{self.__class__.__name__}] Final Pos: {pos}")
            print(f"[{self.__class__.__name__}] Final Neg: {neg}")

        return pos, neg


# --- Subclasses for Specific Slot Counts ---

class RMStylerMulti2(RMStylerMultiBase):
    _slot_count = 2

class RMStylerMulti4(RMStylerMultiBase):
    _slot_count = 4

class RMStylerMulti6(RMStylerMultiBase):
    _slot_count = 6

class RMStylerMulti8(RMStylerMultiBase):
    _slot_count = 8


# --- Node Registration ---

NODE_CLASS_MAPPINGS = {
    "RMStyler": RMStyler,
    "RMStylerMulti2": RMStylerMulti2,
    "RMStylerMulti4": RMStylerMulti4,
    "RMStylerMulti6": RMStylerMulti6,
    "RMStylerMulti8": RMStylerMulti8,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMStyler": "RM Styler",
    "RMStylerMulti2": "RM Multi Styler 2",
    "RMStylerMulti4": "RM Multi Styler 4",
    "RMStylerMulti6": "RM Multi Styler 6",
    "RMStylerMulti8": "RM Multi Styler 8",
}