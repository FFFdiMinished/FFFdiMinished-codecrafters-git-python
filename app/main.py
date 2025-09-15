import sys
import os
import zlib
import hashlib


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    # print("Logs from your program will appear here!", file=sys.stderr)

    # Uncomment this block to pass the first stage
    #
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")
    elif command == "cat-file" and sys.argv[2] == "-p":
        file = sys.argv[3]
        filename = f'.git/objects/{file[0:2]}/{file[2:]}'
        with open(filename, "rb") as f:
            data = f.read()
            data = zlib.decompress(data)
            header_end = data.find(b'\x00')
            content = data[header_end+1:].strip()
            print(content.decode('utf-8'), end="")

    elif command == "hash-object":
        if sys.argv[2] == "-w":
            filename = sys.argv[3]
        else:
            filename = sys.argv[2]
        # get file content bin
        with open(filename, "rb") as f:
            data = f.read()
        out_data = f'blob {len(data)}\0'.encode('utf-8') + data
        hash = hashlib.sha1(out_data).hexdigest()
        new_dir = hash[0:2]
        new_path = f'.git/objects/{new_dir}/{hash[2:]}'
        out_data_compressed = zlib.compress(out_data)
        if sys.argv[2] == "-w":
            if not os.path.exists(f".git/objects/{hash[0:2]}"):
                os.mkdir(f".git/objects/{hash[0:2]}")
            with open(new_path, 'wb') as g:
                g.write(out_data_compressed)
        print(hash)

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()