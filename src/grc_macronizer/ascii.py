import logging

ascii_macronizer = [
    r'#                                      _              ',
    r'# _ __ ___   __ _  ___ _ __ ___  _ __ (_)_______ _ __ ',
    r"#| '_ ` _ \ / _` |/ __| '__/ _ \| '_ \| |_  / _ \ '__|",
    r'#| | | | | | (_| | (__| | | (_) | | | | |/ /  __/ |   ',
    r'#|_| |_| |_|\__,_|\___|_|  \___/|_| |_|_/___\___|_|   ',
    r'#                                                     ',
    r'#                                                     '
]


def wrap_ascii_in_print(file_path):
    """
    Reads a file containing ASCII art and wraps each line in print(r" ").
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    for line in lines:
        print(f'print(r"{line.rstrip()}")')

if __name__ == "__main__":

    wrap_ascii_in_print('ascii.txt')