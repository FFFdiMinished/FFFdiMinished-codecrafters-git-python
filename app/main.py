import sys
import os
import zlib
import hashlib

DIR_MODE = 40000
FILE_MODE = 100644

def hash_blob(content, type = 'blob') -> str:
    header = f'{type} {len(content)}\0'.encode()
    content = header + content
    hash = hashlib.sha1(content).hexdigest()
    os.makedirs(f".git/objects/{hash[:2]}",exist_ok=True)
    with open(f".git/objects/{hash[:2]}/{hash[2:]}", "wb") as wb:
        wb.write(zlib.compress(content))
    return hash

def write_blob(file_path: str) -> str:
    with open(f"{file_path}", "rb") as f:
        return hash_blob(f.read())
        
def encode_mode(mode, name, hash) -> bytes:
    return f"{mode} {name}".encode() + b'\0' + bytes.fromhex(hash)

def write_tree(root = ".") -> str:
    hash_map = {}
    for entry in os.scandir(root):
        if entry.name.startswith(('.', '_')):
            continue
        if entry.is_file():
            hash = write_blob(os.path.join(root, entry.name))
            hash_map[entry.name] = encode_mode(FILE_MODE, entry.name, hash)
        else:
            hash = write_tree(os.path.join(root, entry.name))
            hash_map[entry.name] = encode_mode(DIR_MODE, entry.name, hash)
    
    hash_list = [v for k, v in sorted(hash_map.items())]

    content = b''.join(hash_list)

    return hash_blob(content, 'tree')

def commit_tree(tree_sha, parent_sha, message):
    content = f"tree {tree_sha}\n parent {parent_sha}\nauthor Anunay <anunay@gmail.com>\ncommiter anunay <anunay@gmail.com>\n\n{message}\n".encode()
    return hash_blob(content, 'commit')


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    
    # cwd = os.getcwd()

    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Intialized git directory")

    elif command == "cat-file":
        param, hash = sys.argv[2], sys.argv[3]
        if param == '-p':
            with open(f".git/objects/{hash[:2]}/{hash[2:]}", "rb") as f:
                compressed = f.read()
                content = zlib.decompress(compressed).split(b'\0')[1].decode('utf-8')
                print(content, end="")

    elif command == "hash-object":
        param, file = sys.argv[2], sys.argv[3]
        if param == '-w':
            print(write_blob(file))

    elif command == "ls-tree":
        param, hash = sys.argv[2], sys.argv[3]
        if(param == '--name-only'):
            with open(f".git/objects/{hash[:2]}/{hash[2:]}", "rb") as f:
                data = zlib.decompress(f.read())
                _, binary_data = data.split(b'\x00', maxsplit=1)
                while binary_data:
                    mode, binary_data = binary_data.split(b'\x00', maxsplit=1)
                    _, name = mode.split()
                    binary_data = binary_data[20:]
                    print(name.decode('utf-8'))

    elif command == 'write-tree':
        print(write_tree())
    elif command == 'commit-tree':
        tree_sha, parent_sha, message = sys.argv[2], sys.argv[4], sys.argv[6]
        print(commit_tree(tree_sha, parent_sha, message)) 
    else:
        raise RuntimeError(f"Unknown command #{command}")
    



if __name__ == "__main__":
    main()