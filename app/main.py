import sys
import os
import zlib
import hashlib
import time
from datetime import datetime, timezone
from typing import List, Tuple, Dict
from urllib.parse import urlparse
import urllib.request
import struct

# Store the absolute path to the .git directory
GIT_DIR = os.path.join(os.getcwd(), ".git")
def init():
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")

def catfile():
    blob_sha = sys.argv[-1]
    dir = blob_sha[0:2]
    file = blob_sha[2:]
    file = file.strip("\r")
    file_path = f".git/objects/{dir}/{file}"
    with open(file_path, 'rb') as f_in:
        compressed_data = f_in.read()
    decompressed_data = zlib.decompress(compressed_data)
    size = decompressed_data.split(b'\x00', 1)[0]
    data = decompressed_data.split(b'\x00', 1)[1]
    data = data.decode("utf-8").strip("\n")
    print(data, end="")

def hashobject(command_list):
    if len(command_list) < 3:
        print("The command is missing arguments. usage: hash-object <optional flag> <file>", file=sys.stderr)
        exit()
    file_name= command_list[-1]
    with open(file_name, "rb") as file:
            file_content = file.read()
    header = f"blob {len(file_content)}\x00"
    store = header.encode("ascii") + file_content
    compressed_data = zlib.compress(store)
    sha = hashlib.sha1(store).hexdigest()
    if command_list[-2] == "-w":
        dir = GIT_DIR + "/objects/" + sha[0:2]
        try:
            os.mkdir(dir)  # Create the directory
        except FileExistsError:
            pass  # Ignore error if directory already exists
        file = dir + "/" +sha[2:]
        with open(file, "wb") as file:
            file.write(compressed_data)
        return sha
    else:
        return sha

def lstree():
    tree_sha = sys.argv[-1]
    dir = tree_sha[0:2]
    file = tree_sha[2:]
    file = file.strip("\r")
    file_path = f".git/objects/{dir}/{file}"
    with open(file_path, 'rb') as f_in:
        compressed_data = f_in.read()
    decompressed_data = zlib.decompress(compressed_data)
    size = decompressed_data.split(b'\x00', 1)[0]
    data = decompressed_data.split(b'\x00', 1)[1]
    position = 0
    i = 0
    mode = []
    name = []
    sha_hash = []
    while position < len(data):
        mode_end = data.find(b' ', position)
        mode.append(data[position:mode_end].decode("utf-8"))
        position = mode_end

        name_end = data.find(b'\x00', position)
        name.append(data[position+1:name_end].decode("utf-8"))
        position = name_end

        sha_hash.append(data[position+1:position+21].hex())
        position = position + 21

        i+=1
    names = '\n'.join(name)
    print(names)

def wrtree():
    cwd = os.getcwd()  # Current working directory
    tree_content = bytes()  # To store the serialized tree data

    # Serialize files in the current directory
    entries = sorted(os.scandir(cwd), key=lambda entry: entry.name)
    for entry in entries:
        if entry.name == ".git":
            continue
        mode = get_mode(entry.path)
        if entry.is_file():
            # Compute the blob hash for the file
            file_sha = hashobject(["hash-object", "-w", entry.name])
            # Add the file's mode, name, and hash to the tree
            tree_content += f"{mode} {entry.name}\0".encode("utf-8") + bytes.fromhex(file_sha)
        elif entry.is_dir():
            os.chdir(entry.name)  # Enter the subdirectory
            sub_tree_sha = wrtree()  # Recursively generate the tree object for the subdirectory
            os.chdir("..")  # Return to the parent directory
            # Add the directory's mode, name, and tree hash to the tree
            tree_content += f"{mode} {entry.name}\0".encode("utf-8") + bytes.fromhex(sub_tree_sha)

    # Create the tree object header
    header = f"tree {len(tree_content)}\0".encode("utf-8")
    tree_object = header + tree_content

    # Compute the tree's SHA-1 hash
    tree_sha = hashlib.sha1(tree_object).hexdigest()

    # Store the tree object in the Git object database
    compressed_tree = zlib.compress(tree_object)
    dir_path = f".git/objects/{tree_sha[:2]}"
    file_path = f"{dir_path}/{tree_sha[2:]}"
    os.makedirs(dir_path, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(compressed_tree)

    return tree_sha
        

def get_mode(path):
    """Determine the mode for a given path."""
    if os.path.isdir(path):
        return "40000"  # Directory
    elif os.path.islink(path):
        return "120000"  # Symbolic link
    elif os.path.isfile(path):
        if os.access(path, os.X_OK):
            return "100755"  # Executable file
        else:
            return "100644"  # Regular file
    else:
        raise ValueError(f"Unknown file type for path: {path}")

def cmtree():
    msg = sys.argv[-1]
    
    tree_sha = sys.argv[2]
    name = "Mohammed Omair Mohiuddin"
    email = "mohammedomair07@gmail.com"
    epoch_time = int(time.time())
    timezone_offset = get_timezone_offset()
    if "-p" in sys.argv:
        parent_commit_sha = sys.argv[-3]
        commit_content = (
            f"tree {tree_sha}\n"
            f"parent {parent_commit_sha}\n"  # Omit if there's no parent commit
            f"author {name} {epoch_time} {timezone_offset}\n"
            f"committer {name} {epoch_time} {timezone_offset}\n"
            f"\n"
            f"{msg}\n"
        )
    else:
        commit_content = (
            f"tree {tree_sha}\n"
            f"author {name} {epoch_time} {timezone_offset}\n"
            f"committer {name} {epoch_time} {timezone_offset}\n"
            f"\n"
            f"{msg}\n"
        )
    commit_content_bytes = commit_content.encode("utf-8")
    header = f"commit {len(commit_content_bytes)}\0".encode("utf-8")
    full_content = header + commit_content_bytes

    #Compute the SHA-1 hash
    sha1_hash = hashlib.sha1(full_content).hexdigest()

    #Compress the content
    compressed_content = zlib.compress(full_content)

    #Save the compressed content in .git/objects
    dir_path = f".git/objects/{sha1_hash[:2]}"
    file_path = f"{dir_path}/{sha1_hash[2:]}"
    os.makedirs(dir_path, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(compressed_content)

    return sha1_hash
    
def get_timezone_offset():
    # Get the current time with UTC offset
    now = datetime.now()
    if now.utcoffset() is None:
        # If no timezone info, assume local timezone
        now = datetime.now(timezone.utc).astimezone()
    
    # Get the offset in seconds from UTC
    offset_seconds = now.utcoffset().total_seconds()
    
    # Calculate hours and minutes
    hours, remainder = divmod(abs(offset_seconds), 3600)
    minutes = remainder // 60
    
    # Determine the sign of the offset
    sign = '+' if offset_seconds >= 0 else '-'
    
    # Format as ±HHMM
    return f"{sign}{int(hours):02d}{int(minutes):02d}"

def clone():
    # Get repository URL and directory
    remote = sys.argv[2]
    if len(sys.argv) == 4:
        local = sys.argv[3]
    else:
        parsed = urlparse(remote)
        local = parsed.path.split("/")[-1].replace(".git", "")

    # Initialize repository
    os.makedirs(local)
    os.makedirs(os.path.join(local, ".git", "objects"))
    os.makedirs(os.path.join(local, ".git", "refs"))

    print(f"Cloning {remote} to {local}")

    # Fetch refs
    caps, refs = get_refs(remote)
    default_branch = caps.get("default_branch", "refs/heads/main")

    default_ref_sha = None
    for sha, ref in refs:
        if ref == default_branch:
            default_ref_sha = sha
            break

    if default_ref_sha is None:
        raise RuntimeError(f"Default branch not found: {default_branch}")

    # Download and process packfile
    print(f"Downloading {default_branch} ({default_ref_sha})")
    packfile = download_packfile(remote, default_ref_sha)
    write_packfile(packfile, local)

    # Write HEAD ref
    with open(os.path.join(local, ".git", "HEAD"), "w") as f:
        f.write(f"ref: {default_branch}\n")

    # Write branch ref
    ref_dir = os.path.join(local, ".git", os.path.dirname(default_branch))
    os.makedirs(ref_dir, exist_ok=True)
    with open(os.path.join(local, ".git", default_branch), "w") as f:
        f.write(f"{default_ref_sha}\n")

    # Read the commit and tree
    _, commit_content = read_object(local, default_ref_sha)
    tree_sha = commit_content[5:45].decode()  # Extract tree SHA from commit

    # Render the tree to the working directory
    render_tree(local, local, tree_sha)

def get_refs(url: str) -> Tuple[Dict[str, bool | str], List[Tuple[str, str]]]:
    """Fetch refs using Smart HTTP protocol."""
    url = f"{url}/info/refs?service=git-upload-pack"

    req = urllib.request.Request(url)
    refs, caps = [], {}
    with urllib.request.urlopen(req) as response:
        lines = response.read().split(b"\n")

    # parse capabilities
    cap_bytes = lines[1].split(b'\x00')[1]
    for cap in cap_bytes.split(b' '):
        if cap.startswith(b"symref=HEAD:"):
            caps["default_branch"] = cap.split(b":")[1].decode()
        else:
            caps[cap.decode()] = True

    # parse refs
    for line in lines[2:]:
        if line.startswith(b"0000"):
            break

        sha, ref_name = line.decode().split(" ")  # each ref line is formatted as: "<sha>\x00ref_name"
        refs.append((sha[4:], ref_name))  # remove the length prefix that git uses

    return caps, refs

def download_packfile(url: str, want_ref: str) -> bytes:
    """Download a packfile using Git protocol v2."""
    url = f"{url}/git-upload-pack"

    # Create the request body with proper packet format
    body = (
            b"0011command=fetch0001000fno-progress"
            + f"0032want {want_ref}\n".encode()
            + b"0009done\n0000"
    )

    headers = {
        "Content-Type": "application/x-git-upload-pack-request",
        "Git-Protocol": "version=2"
    }

    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req) as response:
        data = response.read()

    # Parse the response into lines
    pack_lines = []

    while data:
        # Read packet length (4 hex digits)
        line_len = int(data[:4], 16)
        if line_len == 0:
            break
        pack_lines.append(data[4:line_len])
        data = data[line_len:]

    # Combine all lines after the first one (skipping header)
    # and remove the packet type byte from each line
    return b"".join(l[1:] for l in pack_lines[1:])

def write_packfile(data: bytes, target_dir: str) -> None:
    """Parse and write a packfile to the target directory."""
    git_dir = os.path.join(target_dir, ".git")

    def next_size_type(bs: bytes) -> Tuple[str, int, bytes]:
        """Parse the type and size of the next object."""
        ty = (bs[0] & 0b01110000) >> 4
        type_map = {
            1: "commit",
            2: "tree",
            3: "blob",
            4: "tag",
            6: "ofs_delta",
            7: "ref_delta"
        }
        ty = type_map.get(ty, "unknown")

        size = bs[0] & 0b00001111
        i = 1
        shift = 4
        while bs[i - 1] & 0b10000000:
            size |= (bs[i] & 0b01111111) << shift
            shift += 7
            i += 1
        return ty, size, bs[i:]

    def next_size(bs: bytes) -> Tuple[int, bytes]:
        """Parse just the size field."""
        size = bs[0] & 0b01111111
        i = 1
        shift = 7
        while bs[i - 1] & 0b10000000:
            size |= (bs[i] & 0b01111111) << shift
            shift += 7
            i += 1
        return size, bs[i:]

    # Skip pack header and version (8 bytes)
    data = data[8:]

    # Read number of objects
    n_objects = struct.unpack("!I", data[:4])[0]
    data = data[4:]

    print(f"Processing {n_objects} objects")

    # First pass: collect all objects and their data
    objects = []  # List to store (type, content, base_sha) tuples
    remaining_data = data

    for _ in range(n_objects):
        obj_type, _, remaining_data = next_size_type(remaining_data)

        if obj_type in ["commit", "tree", "blob", "tag"]:
            # Direct object - just decompress
            decomp = zlib.decompressobj()
            content = decomp.decompress(remaining_data)
            remaining_data = decomp.unused_data
            objects.append((obj_type, content, None))

        elif obj_type == "ref_delta":
            # Reference delta object - store for second pass
            base_sha = remaining_data[:20].hex()
            remaining_data = remaining_data[20:]

            # Decompress delta data
            decomp = zlib.decompressobj()
            delta = decomp.decompress(remaining_data)
            remaining_data = decomp.unused_data

            objects.append(("ref_delta", delta, base_sha))

    # Second pass: process objects in order
    processed_objects = set()  # Keep track of processed objects

    def process_object(obj_data: Tuple[str, bytes, str | None]) -> None:
        obj_type, content, base_sha = obj_data

        if obj_type != "ref_delta":
            # Direct object
            store = f"{obj_type} {len(content)}\x00".encode() + content
            sha = hashlib.sha1(store).hexdigest()

            # Write to objects directory
            path = os.path.join(git_dir, "objects", sha[:2])
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, sha[2:]), "wb") as f:
                f.write(zlib.compress(store))

            processed_objects.add(sha)
            return sha

        else:
            # Delta object
            if base_sha not in processed_objects:
                # Find and process base object first
                for obj in objects:
                    if obj[0] != "ref_delta" and hashlib.sha1(
                            f"{obj[0]} {len(obj[1])}\x00".encode() + obj[1]).hexdigest() == base_sha:
                        process_object(obj)
                        break

            # Read base object
            with open(f"{git_dir}/objects/{base_sha[:2]}/{base_sha[2:]}", "rb") as f:
                base_content = zlib.decompress(f.read())
            base_type = base_content.split(b' ')[0].decode()
            base_content = base_content.split(b'\x00', 1)[1]

            # Skip size headers in delta
            delta = content
            _, delta = next_size(delta)  # base size
            _, delta = next_size(delta)  # target size

            # Apply delta instructions
            result = b""
            while delta:
                cmd = delta[0]
                if cmd & 0b10000000:  # Copy command
                    pos = 1
                    offset = 0
                    size = 0

                    # Read offset
                    for i in range(4):
                        if cmd & (1 << i):
                            offset |= delta[pos] << (i * 8)
                            pos += 1

                    # Read size
                    for i in range(3):
                        if cmd & (1 << (4 + i)):
                            size |= delta[pos] << (i * 8)
                            pos += 1

                    result += base_content[offset:offset + size]
                    delta = delta[pos:]
                else:  # Insert command
                    size = cmd
                    result += delta[1:size + 1]
                    delta = delta[size + 1:]

            # Store the resulting object
            store = f"{base_type} {len(result)}\x00".encode() + result
            sha = hashlib.sha1(store).hexdigest()

            path = os.path.join(git_dir, "objects", sha[:2])
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, sha[2:]), "wb") as f:
                f.write(zlib.compress(store))

            processed_objects.add(sha)
            return sha

    for obj in objects:
        process_object(obj)

def read_object(path: str, sha: str) -> Tuple[str, bytes]:
    """Read a Git object and return its type and content."""
    with open(f"{path}/.git/objects/{sha[:2]}/{sha[2:]}", "rb") as f:
        data = zlib.decompress(f.read())

    # Split into header and content
    null_pos = data.index(b'\x00')
    header = data[:null_pos]
    content = data[null_pos + 1:]

    # Parse type and size from header
    obj_type = header.split(b' ')[0].decode()
    return obj_type, content

def render_tree(repo_path: str, dir_path: str, sha: str):
    """
    Recursively render a Git tree object to the filesystem.
    """
    print(f"Rendering tree {sha} to {dir_path}")
    os.makedirs(dir_path, exist_ok=True)
    _, tree_content = read_object(repo_path, sha)

    # Process each entry in the tree
    while tree_content:
        # Split mode and remaining content
        mode, tree_content = tree_content.split(b' ', 1)
        # Split name and remaining content
        name, tree_content = tree_content.split(b'\x00', 1)
        # Get object SHA (next 20 bytes)
        entry_sha = tree_content[:20].hex()
        tree_content = tree_content[20:]

        # Create full path for this entry
        entry_path = os.path.join(dir_path, name.decode())

        # Handle based on mode
        if mode == b'40000':  # Directory
            # Recursively render subtree
            render_tree(repo_path, entry_path, entry_sha)
        elif mode == b'100644':  # Regular file
            # Read and write file content
            _, content = read_object(repo_path, entry_sha)
            with open(entry_path, 'wb') as f:
                f.write(content)
        else:
            raise RuntimeError(f"Unsupported mode: {mode}")


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.

    command = sys.argv[1]
    if command == "init":
        init()
    elif command == "cat-file":
        catfile()
    elif command == "hash-object":
        command_list = sys.argv
        result = hashobject(command_list)
        print(result)
    elif command == "ls-tree":
        lstree()
    elif command == "write-tree":
        result = wrtree()
        print(result)
    elif command == "commit-tree":
        result = cmtree()
        print(result)
    elif command == "clone":
        clone()
    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()