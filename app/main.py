import sys
import os
import zlib
import hashlib


def init():
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")


def cat_file(file_path):
    with open(f".git/objects/{file_path[:2]}/{file_path[2:]}", "rb") as f:
        raw = zlib.decompress(f.read())
        size, content = raw.split(b"\0")
        print(content.decode(), end="")


def hash_object(file_path):
    with open(file_path, "rb") as f:
        content = f.read()
        header = f"blob {len(content)}\0"

        store = header.encode("ascii") + content

        hash = hashlib.sha1(store).hexdigest()

        object_path = os.path.join(os.getcwd(), ".git/objects", hash[:2])

        os.mkdir(object_path)
        with open(os.path.join(object_path, hash[2:]), "wb") as f_path:
            f_path.write(zlib.compress(store))
        print(hash, end="")


def ls_tree(hash):
    with open(f".git/objects/{hash[:2]}/{hash[2:]}", "rb") as f:
        data = zlib.decompress(f.read())
        _, tree_data = data.split(b"\x00", maxsplit=1)
        while tree_data:
            mode, tree_data = tree_data.split(b"\x00", maxsplit=1)
            _, name = mode.split()
            print(name.decode('utf-8'))
            tree_data = tree_data[20:]


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    # print("Logs from your program will appear here!")

    # Uncomment this block to pass the first stage

    command = sys.argv[1]
    if command == "init":
        init()
    elif command == "cat-file":
        if sys.argv[2] != "-p":
            raise RuntimeError(f"Unknown flag {sys.argv[2]}")
        cat_file(sys.argv[3])
    elif command == "hash-object":
        if sys.argv[2] != "-w":
            raise RuntimeError(f"Unknown flag {sys.argv[2]}")
        hash_object(sys.argv[3])
    elif command == "ls-tree":
        if sys.argv[2] != "--name-only":
            raise RuntimeError(f"Unknown flag {sys.argv[2]}")
        ls_tree(sys.argv[3])

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()