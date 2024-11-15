import os
import re

# Base directory where the Lua files are stored
base_dir = '.'

# Mapping of original MediaWiki module paths to local paths
module_mappings = {
    "mw.loadData": "require",
    "mw.ustring.sub": "mw.ustring.sub",
    "mw.ustring.find": "mw.ustring.find",
    "mw.ustring.toNFD": "mw.ustring.toNFD",
    "Module:grc-conj/data": "grc-conj.data",
    "Module:grc-accent": "grc-accent",
    "Module:links": "links",
    "Module:languages": "languages",
    "Module:table": "table",
    "Module:grc-decl/shared": "grc-decl.shared",
    "Module:grc-decl/table": "grc-decl.table",
    "Module:grc-decl/decl": "grc-decl.decl",
}

# Pattern to find require/loadData statements
pattern = re.compile(r"(mw\.loadData|require)\(['\"](.*?)['\"]\)")

def update_lua_file(file_path):
    """Update imports in a Lua file to match the local directory structure."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Replace each module import with the corresponding local path
    def replace_match(match):
        func, module_path = match.groups()
        new_path = module_mappings.get(module_path, module_path)
        if func == "mw.loadData":
            return f"require('{new_path}')"
        return f"require('{new_path}')"

    updated_content = pattern.sub(replace_match, content)

    # Write back the updated content to the same file
    with open(file_path, 'w') as f:
        f.write(updated_content)

def process_lua_files(directory):
    """Recursively process all Lua files in the given directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.lua'):
                lua_file_path = os.path.join(root, file)
                print(f"Processing {lua_file_path}...")
                update_lua_file(lua_file_path)

# Run the script on the base directory
if __name__ == "__main__":
    process_lua_files(base_dir)
    print("All Lua files updated!")