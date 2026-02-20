# Wan2GP Template Injector Plugin

A Wan2GP plugin that enables dynamic prompt templating using `__template_path__` syntax. Replace template tags with random lines from text files, with support for wildcards and automatic injection.

Updated for and tested on Wan2GP 10.90.

- **Template generation.

## Features 
- **Syntax**: Use `__folder/subfolder/file__` in prompts to inject random lines
- **Wildcard Support**: 
  - `__*keyword*__` - Search all folders for files containing keyword
  - `__folder/prefix*__` - Match files starting with prefix in folder
  - `__folder/*__` - All files in a folder
- **Automatic Injection**: Templates are automatically processed when you click "Generate"
- **UI Controls**: Browse, create, and preview templates from the plugin tab
- **Comment Support**: Lines starting with `#` in template files are skipped

## Installation

### 1. Install plugin to Wan2GP

In `Plugins` tab install via `Install from URL`:

```
https://github.com/adnikiforov/wan2gp-template-injector.git
```

(manual way) Copy all files to your Wan2GP plugins directory:

```
Wan2GP/plugins/wan2gp-template-injector/
├── __init__.py
├── plugin.py
└── plugin_info.json
```

### 2. Patch wgp.py (Required)

The plugin requires a small patch to `Wan2GP/wgp.py` to enable automatic template injection upon generation.

**Find this code in `validate_settings()` function (around line 659-660):**

```python
prompt = inputs["prompt"]
prompt, errors = prompt_parser.process_template(prompt, keep_empty_lines=model_def.  get("preserve_empty_prompt_lines", False))
if len(errors) > 0:
    gr.Info("Error processing prompt template: " + errors)
    return ret()
prompt = prompt.strip("\n").strip()
```

**Add after the `prompt.strip()` line:**

```python
if hasattr(app, "plugin_manager"):
    prompt = app.plugin_manager.run_data_hooks(
        "process_prompt",
        configs=prompt
    ) or prompt
```

### 3. Create Templates Folder

Create a `templates` folder in your Wan2GP root directory:

```
Wan2GP/templates/
├── styles/
│   ├── cinematic.txt
│   └── moody.txt
├── subjects/
│   └── character.txt
└── modifiers/
    └── lighting.txt
```

### 4. Restart Wan2GP

Enable plugin in `Plugins` tab and restart Wan2GP.

## Usage

### Creating Template Files

Create `.txt` files in the `templates` folder with one option per line:

```
Wan2GP/templates/styles/cinematic.txt:
---
dramatic lighting
golden hour
blue hour
noir shadows
soft focus
---

Lines starting with # are comments (skipped):
Wan2GP/templates/subjects/character.txt:
---
# These are character types
warrior mage
rogue thief
noble knight
elf ranger
---
```

### Using Templates in Prompts

Add template tags to your prompt:

```
A portrait __styles/cinematic__ of __subjects/character__ with __modifiers/lighting__
```

When processed, each `__tag__` is replaced with a random line from the matching file:

```
A portrait dramatic lighting of warrior mage with blue hour
```

### Wildcard Examples

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `__*outfit*__` | Any file with 'outfit' in name (all folders) | `subjects/outfit.txt`, `clothes/outfits.txt` |
| `__styles/dramatic*__` | Files starting with 'dramatic' in styles folder | `styles/dramatic.txt`, `styles/dramatic_2.txt` |
| `__styles/*__` | All .txt files in styles folder | Any file in styles/ |

### Plugin UI Buttons

- **Load Current Prompt**: Load the prompt from the main form
- **Inject Only**: Process templates and show result (doesn't send to video tab)
- **Send (with vars)**: Send current prompt to video tab without processing
- **Inject & Send**: Process templates AND send to video tab (convenience button)
