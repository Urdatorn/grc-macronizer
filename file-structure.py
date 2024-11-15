import os
import re

# Base directory containing all Lua files
base_dir = '.'

# Mapping MediaWiki module paths to local paths
module_mappings = {
    "Module:grc-conj/data": "grc-conj.data",
    "Module:grc-accent": "grc-accent",
    "Module:links": "links",
    "Module:languages": "languages",
    "Module:table": "table",
    "Module:grc-decl/shared": "grc-decl.shared",
    "Module:grc-decl/table": "grc-decl.table",
    "Module:grc-decl/decl": "grc-decl.decl",
    "Module:grc-utilities/data": "grc-utilities.data",
    "Module:string/char": "string.char",
    "Module:grc-decl/params": "grc-decl.params",
    "Module:parameters": "parameters",
    "Module:debug": "debug",
    "Module:script utilities": "script_utilities",
    "Module:grc-utilities": "grc-utilities",
    "Module:labels": "labels",
    "Module:fun": "fun",
    "Module:TemplateStyles": "TemplateStyles",
    "Module:array": "array",
    "Module:string utilities": "string_utilities",
}

# Regex to match require statements
require_pattern = re.compile(r"(require\(['\"])(Module:[\w/-]+)(['\"]\))")

def update_require_paths(file_path):
    """Update require paths in a Lua file to match local paths."""
    with open(file_path, 'r') as file:
        content = file.read()

    # Replace MediaWiki paths with local paths
    def replace_match(match):
        prefix, module_path, suffix = match.groups()
        local_path = module_mappings.get(module_path, module_path)
        return f"{prefix}{local_path}{suffix}"

    updated_content = require_pattern.sub(replace_match, content)

    # Write back the updated content
    with open(file_path, 'w') as file:
        file.write(updated_content)

def process_lua_files(directory):
    """Process all Lua files in the directory and update require paths."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.lua'):
                file_path = os.path.join(root, file)
                print(f"Updating: {file_path}")
                update_require_paths(file_path)

if __name__ == "__main__":
    process_lua_files(base_dir)
    print("All require paths updated!")