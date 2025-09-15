import sys
import os
import hashlib
import zlib


def main():
    command = sys.argv[1]
    if command == 'init':
        os.mkdir('.git')
        os.mkdir('.git/objects')
        os.mkdir('.git/refs')
        with open('.git/HEAD', 'w') as f:
            f.write('ref: refs/heads/main\n')
        print(f'Initialized git directory at {os.getcwd()}')

    elif command == 'cat-file':
        if len(sys.argv) < 3:
            raise RuntimeError('not enough arguments for "cat-file" command')
        if sys.argv[2] == '-p':
            hash = sys.argv[3]
            print(plumbing_cat_file(hash), end='')

    elif command == 'hash-object':
        if len(sys.argv) < 3:
            raise RuntimeError('not enough arguments for "hash-object" command')
        if sys.argv[2] == '-w':
            print(plumbing_hash_obj(sys.argv[3]))
        else:
            with open(sys.argv[2], 'rb') as file:
                print(get_hash(file.read()).hex())

    elif command == 'ls-tree':
        plumbing_ls_tree(sys.argv[3])

    elif command == 'write-tree':
        print(plumbing_hash_obj(os.path.join(os.curdir, ".")))

    else:
        raise RuntimeError(f'Unknown command #{command}')

def get_object_path(hash: str) -> tuple[str, str]:
    '''
    Takes a hash as an argument and returns the full path to the hash directory and the full path to the file, respectively
    '''
    obj_dir = os.path.join(os.getcwd(), '.git', 'objects')
    try:
        os.stat(obj_dir)
    except FileNotFoundError:
        raise RuntimeError('".git" directory is missing or improperly configured; please run "git init" to fix')

    hash_folder_name = hash[0:2]
    hash_file_name = hash[2:]
    dir_path = os.path.join(obj_dir, hash_folder_name)
    file_path = os.path.join(dir_path, hash_file_name)

    return (dir_path, file_path)



def plumbing_cat_file(hash: str) -> str:
    def get_hash_file_data(hash: str) -> bytes:
        _, file_path = get_object_path(hash)
        with open(file_path, 'rb') as file:
            return zlib.decompress(file.read())

    file_bytes = get_hash_file_data(hash)
    null_idx = file_bytes.find(b'\x00')
    if null_idx != -1:
        file_type, length = file_bytes[0:null_idx].decode('utf-8').split(' ')
        if file_type == 'tree':
            # Helps ensure we stop reading once we've reached/exceeded `length`
            tracker = 0
            # Index of first digit of file mode
            start_idx = null_idx + 1
            # Index of entry's null byte
            null_idx = file_bytes.find(b'\x00', start_idx)
            # Index of the last byte in the SHA-1
            end_idx = null_idx + 20

            result: list[str] = []
            while tracker < int(length):
                bytes_before_null = file_bytes[start_idx:null_idx].decode('utf-8')
                if null_idx != -1:
                    mode, name = bytes_before_null.split(' ')
                    sha1 = file_bytes[null_idx + 1:end_idx + 1].hex()
                    entry_file_data = get_hash_file_data(sha1)
                    # Each hashed object is formatted <ENTRY_TYPE><SPACE_CHAR><LENGTH><\x00><DATA>
                    entry_type = entry_file_data[0:entry_file_data.find(b' ')].decode('utf-8')
                    result.append(f'{mode} {entry_type} {sha1}    {name}')

                    # <mode bytes> + <space char byte> + <name bytes> + <null byte> + <SHA-1 bytes>
                    tracker += len(mode) + 1 + len(name) + 1 + 20

                    start_idx = end_idx + 1
                    null_idx = file_bytes.find(b'\x00', start_idx)
                    end_idx = null_idx + 20
                else:
                    raise RuntimeError('tree entry is improperly formatted: missing null byte directly before SHA-1')
            return '\n'.join(result)

        elif file_type == 'blob':
            return file_bytes[null_idx + 1:].decode('utf-8')

        else:
            raise RuntimeError('unsupported git object type: ' + file_type)
    else:
        raise RuntimeError('file is improperly formatted: no null byte detected')


def get_hash(data: bytes) -> bytes:
    '''
    Returns a 20 byte hash of the data
    '''
    sha1_hash = hashlib.sha1()
    sha1_hash.update(data)
    return sha1_hash.digest()


def plumbing_hash_obj(path: str) -> str:
    '''
    Creates an entry in the .git/objects folder and returns the hexidecimal SHA-1 hash of the newly created blob/tree.

    Parameters:
    path (str): The path to the object
    '''
    def create_hash_entry(data: bytes) -> str:
        compressed_data = zlib.compress(data)
        hash = get_hash(data).hex()
        hash_dir, hash_file = get_object_path(hash)
        os.makedirs(hash_dir, mode=644, exist_ok=True)
        with open(hash_file, 'wb') as f:
            f.write(compressed_data)
        return hash

    if os.path.isdir(path):
        tree_entries: bytes = b''
        dir_entries = os.listdir(path)
        if not dir_entries:
            # Handle empty directories by returning early
            return ''
        for obj_name in sorted(dir_entries):
            if obj_name == ".git":
                continue
            full_path = os.path.join(path, obj_name)
            file_mode = "40000" if os.path.isdir(full_path) else "100644"
            # Recursively create entries in .git/objects
            hash = plumbing_hash_obj(full_path)
            # Ignore empty directories
            if hash != '':
                tree_entries += f'{file_mode} {obj_name}\0'.encode('utf-8') + bytes.fromhex(hash)

        return create_hash_entry(f'tree {len(tree_entries)}\0'.encode('utf-8') + tree_entries)

    elif os.path.isfile(path):
        with open(path, 'rb') as f:
            data = f.read()
        data = f'blob {len(data)}\0'.encode('utf-8') + data
        return create_hash_entry(data)


def plumbing_ls_tree(hash: str):
    tree_contents = plumbing_cat_file(hash)
    for entry in tree_contents.split('\n'):
        print(entry.split(' ')[-1])


if __name__ == '__main__':
    main()