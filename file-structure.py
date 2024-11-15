import os
import re

# Base directory containing all Lua files
base_dir = '.'

# Mapping MediaWiki module paths to local paths
module_mappings = {
    "Module:grc-decl": "grc-decl.lua",
    "Module:grc-conj": "grc-conj.lua",
    "Module:grc-conj/data": "grc-conj.data.lua",
    "Module:grc-accent": "grc-accent.lua",
    "Module:links": "links.lua",
    "Module:languages": "languages.lua",
    "Module:languages/data": "languages.data.lua",
    "Module:table": "table.lua",
    "Module:grc-decl/shared": "grc-decl.shared.lua",
    "Module:grc-decl/table": "grc-decl.table.lua",
    "Module:grc-decl/decl": "grc-decl.decl.lua",
    "Module:grc-utilities/data": "grc-utilities.data.lua",
    "Module:string/char": "string.char.lua",
    "Module:grc-decl/params": "grc-decl.params.lua",
    "Module:parameters": "parameters.lua",
    "Module:debug": "debug.lua",
    "Module:script utilities": "script_utilities.lua",
    "Module:grc-utilities": "grc-utilities.lua",
    "Module:labels": "labels.lua",
    "Module:fun": "fun.lua",
    "Module:TemplateStyles": "TemplateStyles.lua",
    "Module:array": "array.lua",
    "Module:string utilities": "string_utilities.lua",
    "Module:pron qualifier": "pron_qualifier.lua",
    "Module:string/encode entities": "string.encode_entities.lua",
    "Module:en-utilities": "en_utilities.lua",
    "Module:utilities": "utilities.lua",
    "Module:debug/track": "debug.track.lua",
    "Module:languages/data/patterns": "languages.data.patterns.lua",
    "Module:languages/doSubstitutions": "languages.doSubstitutions.lua",
    "Module:language-like": "language_like.lua",
    "Module:scripts": "scripts.lua",
    "Module:families": "families.lua",
    "Module:JSON": "JSON.lua",
    "Module:families/track-bad-etym-code": "families.track_bad_etym_code.lua",
    "Module:languages/errorGetBy": "languages.errorGetBy.lua",
    "Module:languages/error": "languages.error.lua",
    "Module:pages": "pages.lua",
    "Module:anchors": "anchors.lua",
    "Module:grc-utilities/templates": "grc-utilities.templates.lua",
    "Module:grc-translit": "grc_translit.lua",
    "Module:scripts/charToScript": "scripts.charToScript.lua",
    "Module:scripts/data": "scripts.data.lua",
}

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