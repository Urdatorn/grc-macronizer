import os
import requests

# Base directory for your project
base_dir = '.'

# Base URL for fetching Lua modules
base_url = "https://en.wiktionary.org/wiki/Module:{}?action=raw"

# Mapping MediaWiki module paths to local paths with folder hierarchy
module_mappings = {
    "Module:grc-decl": "grc-decl/grc-decl.lua",
    "Module:grc-conj": "grc-conj/grc-conj.lua",
    "Module:grc-conj/data": "grc-conj/data.lua",
    "Module:grc-accent": "grc-accent.lua",
    "Module:links": "links/links.lua",
    "Module:languages": "languages/languages.lua",
    "Module:languages/data": "languages/data.lua",
    "Module:table": "table.lua",
    "Module:grc-decl/shared": "grc-decl/shared.lua",
    "Module:grc-decl/table": "grc-decl/table.lua",
    "Module:grc-decl/decl": "grc-decl/decl.lua",
    "Module:grc-utilities/data": "grc-utilities/data.lua",
    "Module:string/char": "string/char.lua",
    "Module:grc-decl/params": "grc-decl/params.lua",
    "Module:parameters": "parameters.lua",
    "Module:debug": "debug/debug.lua",
    "Module:script utilities": "script_utilities.lua",
    "Module:grc-utilities": "grc-utilities/grc-utilities.lua",
    "Module:labels": "labels/labels.lua",
    "Module:fun": "fun.lua",
    "Module:TemplateStyles": "TemplateStyles.lua",
    "Module:array": "array.lua",
    "Module:string utilities": "string_utilities.lua",
    "Module:pron qualifier": "pron_qualifier.lua",
    "Module:string/encode entities": "string/encode_entities.lua",
    "Module:en-utilities": "en_utilities.lua",
    "Module:utilities": "utilities/utilities.lua",
    "Module:debug/track": "debug/track.lua",
    "Module:languages/data/patterns": "languages/data/patterns.lua",
    "Module:languages/doSubstitutions": "languages/doSubstitutions.lua",
    "Module:language-like": "language_like/language_like.lua",
    "Module:scripts": "scripts/scripts.lua",
    "Module:families": "families/families.lua",
    "Module:JSON": "JSON/JSON.lua",
    "Module:families/track-bad-etym-code": "families/track_bad_etym_code.lua",
    "Module:languages/errorGetBy": "languages/errorGetBy.lua",
    "Module:languages/error": "languages/error.lua",
    "Module:pages": "pages/pages.lua",
    "Module:anchors": "anchors/anchors.lua",
    "Module:grc-utilities/templates": "grc-utilities/templates.lua",
    "Module:grc-translit": "grc-translit/grc-translit.lua",
    "Module:scripts/charToScript": "scripts/charToScript.lua",
    "Module:scripts/data": "scripts/data.lua",
    "Module:headword/data": "headword/data.lua",
    "Module:headword/page": "headword/page.lua",
    "Module:labels/data": "labels/data.lua",
    "Module:labels/data/lang": "labels/data/lang.lua",
    "Module:labels/data/regional": "labels/data/regional.lua",
    "Module:labels/data/topical": "labels/data/topical.lua",
    "Module:labels/data/qualifiers": "labels/data/qualifiers.lua",
    "Module:zh/data/ts": "zh/data/ts.lua",
    "Module:zh/data/st": "zh/data/st.lua",
    "Module:links/data": "links/data.lua",
    "Module:data/entities": "data/entities.lua",
    "Module:data/namespaces": "data/namespaces.lua",
    "Module:data/interwikis": "data/interwikis.lua",
    "Module:families/data": "families/data.lua",
    "Module:families/data/etymology": "families/data/etymology.lua",
    "Module:th": "th/th.lua",
    "Module:km": "km/km.lua",
    "Module:yesno": "yesno/yesno.lua",
    "Module:references": "references/references.lua",
    "Module:collation": "collation/collation.lua"
}

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

def process_modules():
    """Download Lua modules based on the mappings."""
    for module_name, local_path in module_mappings.items():
        save_path = os.path.join(base_dir, local_path)
        if not os.path.exists(save_path):
            download_module(module_name, save_path)
        else:
            print(f"Already exists: {local_path}, skipping download.")

if __name__ == "__main__":
    process_modules()
    print("All modules processed!")