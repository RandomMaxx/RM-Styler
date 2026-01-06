# 🎨 RM Styler for ComfyUI

**RM Styler** is a powerful prompt styling suite for ComfyUI designed to streamline your workflow. It features dynamic menu updating, advanced prompt weighting, and a "Multi-Styler" system that allows you to stack, mix, and toggle up to 8 distinct styles simultaneously.

---

## ✨ Key Features

* **Dynamic Menus:** The style list updates automatically based on the selected category, powered by real-time Python-to-JavaScript communication.
* **Smart Weighting:** Supports ComfyUI weighting syntax. Styles with weights other than `1.0` are automatically wrapped in `(text:weight)` format.
* **Style Stacking:** Dedicated **Multi-Styler** nodes allow you to layer 2, 4, 6, or 8 styles on top of a base prompt.
* **Granular Control:** In Multi-Styler nodes, you can toggle the **Positive** or **Negative** influence for *each* style layer independently.
* **Hot-Loading:** Simply add new JSON files to the data folder and restart to expand your library.

---

## 📥 Installation

1.  Navigate to your ComfyUI `custom_nodes` directory.
2.  Clone this repository:
    ```bash
    git clone [https://github.com/yourusername/RM_Styler.git](https://github.com/yourusername/RM_Styler.git)
    ```
3.  **Restart ComfyUI**.

---

## 📂 Required Folder Structure

For the node to function correctly, your directory must look like this. The node specifically looks for JSON files inside **subdirectories** of the data folder to generate Category names.

```text
ComfyUI/custom_nodes/RM_Styler/
├── __init__.py
├── rm_styler.py
├── requirements.txt
├── js/
│   └── rm_styler.js        <-- Required for menu logic
└── data/
    └── Basic/              <-- Folder Name = "Category" in Menu
        └── RM-Basic.json   <-- Your Style Definitions
```

🛠️ Usage
1. The Single Styler (RMStyler)
Ideal for applying a comprehensive style to a prompt.

Category: Selects the folder containing your styles (e.g., "Basic", "Artists").

Style: Selects the specific template. This list dynamically refreshes based on the Category.

Weight: Adjusts the strength of the style (0.0 - 10.0).

Log Prompt: If set to True, the final constructed prompt is printed to the console for debugging.

2. The Multi-Stylers (RMStylerMulti2 - RMStylerMulti8)
These nodes are designed for advanced composition.

Stacking Order: Styles are processed from the highest slot number down to 1.

Slot 8 = Inner-most style (applied first).

Slot 1 = Outer-most style (applied last).

Pos/Neg Toggles: Each style slot has _pos_on and _neg_on booleans. This allows you to use the visual aesthetics of a style (Positive) without inheriting its unwanted elements (Negative), or vice versa.

📝 Customizing Styles
You can add unlimited styles by creating JSON files in the data/ directory.

1. Create a Category Folder: Create a folder inside data/. The name of this folder becomes the Category in the dropdown menu.

2. Create a JSON File: Inside that folder, create a .json file with the following structure:

```text
[
    {
        "name": "My Custom Style",
        "prompt": "breathtaking artwork of {prompt} . cinematic lighting, 8k",
        "negative_prompt": "ugly, blurry, low res"
    },
    {
        "name": "Cyberpunk",
        "prompt": "cyberpunk city involving {prompt} . neon lights, chrome, high tech",
        "negative_prompt": "natural, rustic, vintage"
    }
]
```
{prompt}: This token is replaced by your input text.

If {prompt} is missing, the style text is simply appended to your input.

⚠️ Troubleshooting
"No Styles Found":

Ensure your JSON files are inside a subdirectory of data/ (e.g., data/MyStyles/styles.json). Files directly in data/ are ignored.

Check the console for JSON syntax errors.

Menus not updating:

Refresh your browser. The JavaScript extension needs to load the API route /rm_styler/data on startup.
