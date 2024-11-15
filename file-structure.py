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
    "Module:pron qualifier": "pron_qualifier",
    "Module:string/encode entities": "string.encode_entities",
    "Module:en-utilities": "en_utilities",
    "Module:utilities": "utilities",
    "Module:debug/track": "debug.track",
    "Module:languages/data/patterns": "languages.data.patterns",
    "Module:languages/doSubstitutions": "languages.doSubstitutions",
    "Module:language-like": "language_like",
    "Module:scripts": "scripts",
    "Module:families": "families",
    "Module:JSON": "JSON",
    "Module:families/track-bad-etym-code": "families.track_bad_etym_code",
    "Module:languages/errorGetBy": "languages.errorGetBy",
    "Module:languages/error": "languages.error",
    "Module:pages": "pages",
    "Module:anchors": "anchors",
    "Module:grc-utilities/templates": "grc-utilities.templates",
    "Module:grc-translit": "grc_translit",
    "Module:scripts/charToScript": "scripts.charToScript",
    "Module:scripts/data": "scripts.data"
}

# Regex to match require statements
require_pattern = re.compile(r"(require\(['\"])(Module:[\w/-]+)(['\"]\))")
lua_suffix_pattern = re.compile(r"(Module:[\w/-]+)\.lua")

def update_require_paths(file_path):
    """Update require paths in a Lua file to match local paths."""
    with open(file_path, 'r') as file:
        content = file.read()

    # Identify and remove '.lua' suffixes from module paths in require statements
    def remove_lua_suffix(match):
        module_path = match.group(1)
        print(f"Found '.lua' in {module_path}. Removing suffix.")
        return module_path[:-4]  # Remove '.lua'

    # First pass: fix module paths with '.lua'
    content = lua_suffix_pattern.sub(remove_lua_suffix, content)

    # Find all require statements
    matches = require_pattern.findall(content)
    if matches:
        print(f"Found require statements in {file_path}: {[match[1] for match in matches]}")

    # Replace MediaWiki paths with local paths
    def replace_match(match):
        prefix, module_path, suffix = match.groups()
        local_path = module_mappings.get(module_path)
        if local_path is None:
            print(f"Warning: No mapping found for {module_path} in {file_path}")
            local_path = module_path  # Leave unchanged if no mapping
        return f"{prefix}{local_path}{suffix}"

    updated_content = require_pattern.sub(replace_match, content)

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