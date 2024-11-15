import os
import requests

# Base directory for your project
base_dir = '.'

# Mapping MediaWiki module paths to local paths
module_mappings = {
    "Module:scripts/data": "scripts/data.lua",
    "Module:scripts/charToScript": "scripts/charToScript.lua",
}

# Base URL for fetching Lua modules
base_url = "https://en.wiktionary.org/wiki/Module:{}?action=raw"

def download_module(module_name, save_path):
    """Download a Lua module from Wiktionary and save it to the specified path."""
    url = base_url.format(module_name.replace("Module:", ""))
    try:
        print(f"Downloading: {module_name}")
        response = requests.get(url)
        response.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(response.text)
        print(f"Saved to: {save_path}")
    except requests.RequestException as e:
        print(f"Failed to download {module_name}: {e}")

def process_new_modules():
    """Download only the Lua modules that are not already present."""
    for module_name, local_path in module_mappings.items():
        save_path = os.path.join(base_dir, local_path)
        if not os.path.exists(save_path):
            download_module(module_name, save_path)
        else:
            print(f"Already exists: {local_path}, skipping download.")

if __name__ == "__main__":
    process_new_modules()
    print("All missing modules processed!")