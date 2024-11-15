import os
import re

from module_mappings import module_mappings

# Base directory containing all Lua files
base_dir = '.'

# Regex patterns
require_pattern = re.compile(r"(require\(['\"])(Module:[\w/-]+)(['\"]\))")
module_in_function_pattern = re.compile(r"(['\"])(Module:[\w/-]+)(['\"])")
lua_suffix_pattern = re.compile(r"(Module:[\w/-]+)\.lua")


def update_paths_in_text(content):
    """Update all module paths in Lua content."""
    # Identify and remove '.lua' suffixes from module paths
    def remove_lua_suffix(match):
        module_path = match.group(1)
        return module_path[:-4]  # Remove '.lua'

    content = lua_suffix_pattern.sub(remove_lua_suffix, content)

    # Replace require statements
    def replace_require(match):
        prefix, module_path, suffix = match.groups()
        local_path = module_mappings.get(module_path)
        if not local_path:
            print(f"Warning: No mapping found for {module_path}")
            local_path = module_path  # Leave unchanged if no mapping
        return f"{prefix}{local_path}{suffix}"

    content = require_pattern.sub(replace_require, content)

    # Replace module paths within functions or strings
    def replace_function_module(match):
        _, module_path, _ = match.groups()
        local_path = module_mappings.get(module_path)
        if not local_path:
            print(f"Warning: No mapping found for {module_path}")
            local_path = module_path  # Leave unchanged if no mapping
        return f'"{local_path}"'

    content = module_in_function_pattern.sub(replace_function_module, content)

    return content


def update_require_paths(file_path):
    """Update require paths in a Lua file."""
    with open(file_path, 'r') as file:
        content = file.read()

    updated_content = update_paths_in_text(content)

    # Write back the updated content if changes were made
    if updated_content != content:
        with open(file_path, 'w') as file:
            file.write(updated_content)
        print(f"Updated require paths in {file_path}")


def process_lua_files(directory):
    """Process all Lua files in the directory and update require paths."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.lua'):
                file_path = os.path.join(root, file)
                print(f"Processing: {file_path}")
                update_require_paths(file_path)


if __name__ == "__main__":
    process_lua_files(base_dir)
    print("All require paths updated!")