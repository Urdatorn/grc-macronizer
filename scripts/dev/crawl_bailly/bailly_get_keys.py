from grc_utils import macrons_map

def read_stardict_idx_file(idx_path):
    keys = []
    with open(idx_path, 'rb') as f:
        while True:
            # Read the word (null-terminated UTF-8 string)
            chars = []
            while (b := f.read(1)) != b'\x00':
                if not b:
                    return keys  # EOF
                chars.append(b)
            word = b''.join(chars).decode('utf-8')
            keys.append(word)

            # Skip 8 bytes: 4 bytes for offset, 4 bytes for size
            f.read(8)
    return keys

keys = read_stardict_idx_file("db/Bailly2020-stardict/Bailly2020-grc-fra.idx")

output_file = 'bailly_keys.py'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("bailly_keys = {\n")
    for key in keys:
        if any(char in macrons_map.values() for char in key) and '–' not in key:
            f.write(f'    "{key.replace('²', '').replace(' ', '')}",\n')
    f.write("}\n")