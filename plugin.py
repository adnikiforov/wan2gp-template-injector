import gradio as gr
import os
import re
import random
import time
from shared.utils.plugins import WAN2GPPlugin

PlugIn_Name = "Template Injector"
PlugIn_Id = "TemplateInjector"

# Path to templates folder
TEMPLATES_FOLDER = "templates"

def debug_print(*args, **kwargs):
    print(*args, **kwargs)


def get_templates_folder():
    """Get absolute path to templates folder."""
    # Get the Wan2GP root (go up 3 levels from plugin.py)
    # plugin.py -> wan2gp-template-injector/ -> plugins/ -> Wan2GP/
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    plugins_dir = os.path.dirname(plugin_dir)
    wan2gp_root = os.path.dirname(plugins_dir)
    templates_path = os.path.join(wan2gp_root, TEMPLATES_FOLDER)
    return templates_path


def get_random_line_from_file(filepath):
    """Read a random non-empty line from a file (skipping comment lines starting with #)."""
    try:
        if not os.path.isfile(filepath):
            return None

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

        if not lines:
            return None

        return random.choice(lines)
    except Exception as e:
        debug_print(f"[Template Injector] Error reading file {filepath}: {e}")
        return None


def get_random_line_from_files(filepaths):
    """Read random non-empty lines from multiple files and return one random line (skipping comments)."""
    try:
        all_lines = []
        for filepath in filepaths:
            if not os.path.isfile(filepath):
                continue
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
                all_lines.extend(lines)

        if not all_lines:
            return None

        return random.choice(all_lines)
    except Exception as e:
        debug_print(f"[Template Injector] Error reading files: {e}")
        return None


def find_matching_files(search_pattern, templates_dir):
    """
    Find files matching the search pattern.

    Supports wildcards:
    - __*outfit*__ - searches all folders for files containing 'outfit'
    - __folder/outfit*__ - searches specific folder for files starting with 'outfit'
    - __folder/*__ - all files in folder
    """
    import fnmatch

    # Convert path to use os.sep for local matching
    search_pattern = search_pattern.replace("/", os.sep)

    # Split into folder path and filename pattern
    # Handle case where pattern starts with * (global search)
    if search_pattern.startswith("*"):
        # Global search - search all subdirectories
        folder_part = "**"
        file_part = search_pattern[1:]  # Remove leading *
    elif os.sep in search_pattern:
        parts = search_pattern.rsplit(os.sep, 1)
        folder_part = parts[0]
        file_part = parts[1]
    else:
        # Just a filename pattern, search root
        folder_part = ""
        file_part = search_pattern

    search_path = (
        os.path.join(templates_dir, folder_part) if folder_part else templates_dir
    )

    # Use glob to find matching files
    if folder_part == "**":
        # Recursive search from templates root
        glob_pattern = "**" + os.sep + file_part
        matching_files = []
        for root, dirs, files in os.walk(templates_dir):
            for filename in files:
                if fnmatch.fnmatch(filename, file_part):
                    matching_files.append(os.path.join(root, filename))
    else:
        # Direct search in folder
        matching_files = []
        if os.path.exists(search_path):
            for filename in os.listdir(search_path):
                filepath = os.path.join(search_path, filename)
                if os.path.isfile(filepath) and fnmatch.fnmatch(filename, file_part):
                    matching_files.append(filepath)

    return matching_files


def process_template_tags(prompt):
    """
    Process all __template_path__ tags in the prompt.

    Format options:
    - __folder1/folder2/file__ - exact file match
    - __folder/file*__ - wildcard prefix match
    - __folder/*__ - all files in folder
    - __*outfit*__ - global search for files containing 'outfit'

    Replaced with: random line from matched file(s)

    Example: __styles/cinematic__ → dramatic lighting
    Example: __*outfit*__ → some outfit (random from any file with 'outfit')
    
    Note: Each occurrence of the same tag gets a NEW random line,
    so "__styles/cinematic__ __styles/cinematic__" will have two different values.
    """
    if not prompt or not isinstance(prompt, str):
        return prompt

    # Use non-greedy match to capture everything between __ and __
    pattern = r"__(.+?)__"
    matches = re.findall(pattern, prompt)

    debug_print(f"[Template Injector] Found template tags: {matches}")

    if not matches:
        return prompt

    templates_dir = get_templates_folder()
    debug_print(f"[Template Injector] Using templates_dir: {templates_dir}")

    def replace_tag(match):
        """Replace a single template tag with a random line."""
        tag_content = match.group(1)
        tag = match.group(0)  # The full __tag__ string

        # Check if the pattern contains wildcards
        if "*" in tag_content:
            # Wildcard search
            matching_files = find_matching_files(tag_content, templates_dir)

            if not matching_files:
                debug_print(f"[Template Injector] No files match pattern: {tag_content}")
                return tag  # Return original tag if no match

            random_line = get_random_line_from_files(matching_files)

            if random_line is None:
                debug_print(
                    f"[Template Injector] No content in matching files for: {tag_content}"
                )
                return tag  # Return original tag if no content

            debug_print(
                f"[Template Injector] Wildcard '{tag_content}' matched {len(matching_files)} files, selected: {random_line}"
            )
            return random_line
        else:
            # Exact file match (original behavior)
            relative_path = tag_content.replace("/", os.sep)
            template_file = os.path.join(templates_dir, relative_path + ".txt")

            random_line = get_random_line_from_file(template_file)

            if random_line is None:
                debug_print(
                    f"[Template Injector] Template file not found or empty: {template_file}"
                )
                return tag  # Return original tag if file not found

            return random_line

    # Use re.sub with callback - each match gets processed independently
    # This ensures duplicate tags get different random lines
    processed_prompt = re.sub(pattern, replace_tag, prompt)

    return processed_prompt


def scan_templates_folder():
    """Scan templates folder and return file tree."""
    templates_dir = get_templates_folder()
    tree_data = []

    if not os.path.exists(templates_dir):
        return tree_data

    for root, dirs, files in os.walk(templates_dir):
        # Sort and filter out directories starting with underscore
        dirs[:] = sorted([d for d in dirs if not d.startswith("_")])
        files = sorted(files)

        rel_path = os.path.relpath(root, templates_dir)

        for f in files:
            # Skip files starting with underscore
            if f.startswith("_"):
                continue
            if f.endswith(".txt"):
                full_path = os.path.join(root, f)
                rel_file_path = os.path.relpath(full_path, templates_dir)
                tag_path = rel_file_path[:-4]
                tag_path = tag_path.replace(os.sep, "/")

                tree_data.append(
                    {
                        "path": full_path,
                        "tag": f"__{tag_path}__",
                        "filename": f,
                        "folder": rel_path if rel_path != "." else "",
                    }
                )

    return tree_data


def get_file_contents(filepath):
    """Read and return file contents."""
    try:
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return ""
    except Exception as e:
        return f"Error: {e}"


def upload_template_file(folder, filename, content):
    """Save uploaded template file."""
    templates_dir = get_templates_folder()

    if folder and folder != ".":
        target_dir = os.path.join(templates_dir, folder)
    else:
        target_dir = templates_dir

    os.makedirs(target_dir, exist_ok=True)

    if not filename.endswith(".txt"):
        filename += ".txt"

    filepath = os.path.join(target_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Saved: {filepath}"


class ConfigTabPlugin(WAN2GPPlugin):
    def __init__(self):
        super().__init__()

    def setup_ui(self):
        self.request_component("state")
        self.request_component("refresh_form_trigger")
        self.request_component("main_tabs")
        # Request the global function to get model settings
        self.request_global("get_current_model_settings")

        # Register hook for automatic template injection before generation
        self.register_data_hook("process_prompt", self.process_prompt_hook)

        self.add_tab(
            tab_id=PlugIn_Id,
            label=PlugIn_Name,
            component_constructor=self.create_template_tab,
        )

    def process_prompt_hook(self, prompt):
        """Hook to process template tags in prompt before generation."""
        if not prompt or not isinstance(prompt, str):
            return prompt

        debug_print(f"[Template Injector] Hook called with prompt: {prompt[:100]}...")

        # First, check if templates folder exists
        templates_dir = get_templates_folder()
        debug_print(f"[Template Injector] Templates folder: {templates_dir}")
        debug_print(
            f"[Template Injector] Templates folder exists: {os.path.exists(templates_dir)}"
        )

        result = process_template_tags(prompt)

        debug_print(
            f"[Template Injector] Result: {result[:100] if result else 'None'}..."
        )

        return result

    def on_tab_select(self, state: dict):
        """Load template choices when tab is selected (but NOT current prompt to avoid wiping user input)."""
        tree_data = scan_templates_folder()

        if not tree_data:
            choices = []
            default_choice = ""
        else:
            choices = []
            for item in tree_data:
                choices.append(item["tag"])
            default_choice = choices[0] if choices else ""

        # Don't load current prompt - user may have typed it manually
        # Use gr.no_update to keep existing value instead of clearing it

        # Return 2 values matching on_tab_outputs: [dropdown, textbox]
        # For dropdown, return update dict with choices and value
        dropdown_update = gr.update(choices=choices, value=default_choice)
        return dropdown_update, gr.no_update()

    def create_template_tab(self):
        """Create the template injector tab UI."""

        def load_template_tree():
            """Load template list and return dropdown update."""
            templates_dir = get_templates_folder()
            debug_print(
                f"[Template Injector] Scanning templates folder: {templates_dir}"
            )
            debug_print(
                f"[Template Injector] Folder exists: {os.path.exists(templates_dir)}"
            )

            tree_data = scan_templates_folder()
            debug_print(f"[Template Injector] Found {len(tree_data)} template files")

            if not tree_data:
                return gr.update(choices=[], value="")

            choices_list = []
            for item in tree_data:
                choices_list.append(item["tag"])

            default_choice = choices_list[0] if choices_list else ""
            return gr.update(choices=choices_list, value=default_choice)

        def load_file_preview(tag_path):
            if not tag_path:
                return ""

            tree_data = scan_templates_folder()
            for item in tree_data:
                if item["tag"] == tag_path:
                    return get_file_contents(item["path"])
            return "File not found"

        def create_new_template(folder, filename, content):
            if not filename:
                return "Please enter a filename", ""

            result = upload_template_file(folder, filename, content)
            return result, ""

        state = self.state

        with gr.Column():
            gr.HTML("""
            <div style="padding: 10px; background: #f0f0f0; border-radius: 8px; margin-bottom: 10px;">
                <b>Template Injector</b><br>
                Use <code>__folder/subfolder/file__</code> in your prompt to inject random lines from template files.<br>
                <br>
                <b>Wildcards supported:</b><br>
                • <code>__*outfit*__</code> - any file with 'outfit' in name (all folders)<br>
                • <code>__folder/outfit*__</code> - files starting with 'outfit' in folder<br>
                • <code>__folder/*__</code> - all files in folder<br>
                <br>
                Example: <code>__styles/cinematic__</code> → <code>dramatic lighting</code>
            </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("Template Browser")
                    refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

                    # Dropdown to search/select templates (replaces the list)
                    template_dropdown = gr.Dropdown(
                        label="Search Template",
                        choices=[],
                        interactive=True,
                        allow_custom_value=True,
                        info="Type to search templates",
                    )

                    file_preview = gr.Textbox(
                        label="Template Content Preview", lines=10, interactive=False
                    )

                    gr.HTML("Create New Template")
                    new_folder = gr.Textbox(
                        label="Folder (optional)",
                        placeholder="e.g., styles, subjects/myfolder",
                    )
                    new_filename = gr.Textbox(
                        label="Filename",
                        placeholder="e.g., mytemplate (will become mytemplate.txt)",
                    )
                    new_content = gr.Textbox(
                        label="Content (one option per line)",
                        lines=5,
                        placeholder="option 1\noption 2\noption 3",
                    )
                    create_btn = gr.Button("Create Template", variant="primary")
                    create_status = gr.Textbox(label="Status", interactive=False)

                with gr.Column(scale=1):
                    gr.HTML("Current Prompt")
                    current_prompt = gr.Textbox(
                        label="Prompt",
                        lines=8,
                        placeholder="Enter your prompt with __template__ tags...",
                    )

                    load_prompt_btn = gr.Button("Load Current Prompt")

                    with gr.Row():
                        inject_only_btn = gr.Button(
                            "🔄 Inject Only", variant="secondary"
                        )
                        send_btn = gr.Button("📤 Send (with vars)", variant="secondary")
                        inject_send_btn = gr.Button(
                            "🎯 Inject & Send", variant="primary"
                        )

                    result_prompt = gr.Textbox(label="Result Preview", lines=8)

            # on_tab_outputs: dropdown + prompt (no markdown list anymore)
            self.on_tab_outputs = [template_dropdown, current_prompt]

            refresh_btn.click(
                fn=load_template_tree, inputs=[], outputs=[template_dropdown]
            )

            template_dropdown.change(
                fn=load_file_preview, inputs=[template_dropdown], outputs=[file_preview]
            )

            def load_current_prompt(state):
                """Load current prompt from model settings."""
                settings = self.get_current_model_settings(state)
                return settings.get("prompt", "")

            load_prompt_btn.click(
                fn=load_current_prompt, inputs=[state], outputs=[current_prompt]
            )

            # Inject Only - just process templates and show result (don't send to video)
            def inject_only(prompt):
                if not prompt:
                    return "", ""
                new_prompt = process_template_tags(prompt)
                return prompt, new_prompt

            inject_only_btn.click(
                fn=inject_only,
                inputs=[current_prompt],
                outputs=[current_prompt, result_prompt],
            )

            # Send - just send current prompt (with vars) to video tab
            def send_to_video(state, prompt):
                settings = self.get_current_model_settings(state)
                settings["prompt"] = prompt
                return time.time()

            send_btn.click(
                fn=send_to_video,
                inputs=[state, current_prompt],
                outputs=[self.refresh_form_trigger],
            ).then(fn=self.goto_video_tab, inputs=[state], outputs=[self.main_tabs])

            # Inject & Send - process templates AND send to video tab
            def inject_and_send(state, prompt):
                new_prompt = process_template_tags(prompt)
                settings = self.get_current_model_settings(state)
                settings["prompt"] = new_prompt
                return new_prompt, time.time()

            inject_send_btn.click(
                fn=inject_and_send,
                inputs=[state, current_prompt],
                outputs=[result_prompt, self.refresh_form_trigger],
            ).then(fn=self.goto_video_tab, inputs=[state], outputs=[self.main_tabs])

            create_btn.click(
                fn=create_new_template,
                inputs=[new_folder, new_filename, new_content],
                outputs=[create_status, new_content],
            ).then(fn=load_template_tree, inputs=[], outputs=[template_dropdown])
