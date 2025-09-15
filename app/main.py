# pylint: disable=invalid-name,missing-module-docstring
# pylint: disable=missing-function-docstring

import argparse
import collections
import os
import sys
import time

from app import repo
from app.utils import initRepo
from app.utils import writeGitObj, readGitObj

TreeObj = collections.namedtuple('TreeObj', ['mode', 'hash', 'name'])

def initCmd():
    initRepo()
    print("Initialized git directory")

def catFile(filePath, verbose=False):
    _, blobData = readGitObj(filePath)
    if verbose:
        print(blobData.decode(errors='replace'), end='')

def hashObj(filePath, verbose=False):
    fileContent = None
    with open(filePath, 'r') as f:
        fileContent = f.read()

    objHash = writeGitObj(fileContent.encode(), 'blob')
    if verbose:
        print(objHash)
    return objHash

def lstree(treeHash):
    tree = []

    _, treeData = readGitObj(treeHash)
    while treeData:
        treeData = treeData.split(b' ', 1)[-1] # strip mode
        name, treeData = treeData.split(b'\x00', 1)
        treeData = treeData[20:] # strip sha1
        tree.append(name.decode())

    for fileName in tree:
        print(fileName)

def writeTree(rootPath=None, verbose=False):
    blobs = []
    for fileName in os.listdir(rootPath):
        if fileName == '.git':
            continue

        filePath = os.path.join(rootPath or "", fileName)
        if os.path.isdir(filePath):
            sha1 = writeTree(filePath)
            mode = 0x4000 | os.stat(filePath).st_mode
        else:
            sha1 = hashObj(filePath)
            mode = 0x8000 | os.stat(filePath).st_mode
        blobs.append(TreeObj(name=fileName, hash=sha1, mode=mode))

    content = b""
    blobs.sort(key=lambda b: b.name)
    for obj in blobs:
        content += b"%o %s\x00%s" % (obj.mode,
                                     obj.name.encode(),
                                     bytes.fromhex(obj.hash))

    treeHash = writeGitObj(content, "tree")
    if verbose:
        print(treeHash)
    return treeHash

def commit(treeRef, parentRef, message):
    content = b"tree %s\n" % treeRef.encode()
    content += b"parent %s\n" % parentRef.encode()
    content += b"author John Doe <john.doe@codecrafter.io> %d %s\n" % (
        time.time(), time.strftime("%z").encode())
    content += b"comitter John Doe <john.doe@codecrafter.io> %d %s\n" % (
        time.time(), time.strftime("%z").encode())
    content += b"\n"
    content += b"%s\n" % message.encode()

    commitHash = writeGitObj(content, "commit")
    print(commitHash)

def clone(url, directory):
    if not os.path.exists(directory):
        os.mkdir(directory)
    repo.clone(url, directory)

def main():
    parser = argparse.ArgumentParser()
    cmdParser = parser.add_subparsers(dest='cmd')

    # init parser
    cmdParser.add_parser('init', help='initialize repository')

    # cat-file parser
    catFileParser = cmdParser.add_parser('cat-file', help='print a given blob')
    catFileParser.add_argument('-p', help='pretty-print object',
                               action='store_true', default=False)
    catFileParser.add_argument('blob', help='blob to print',
                               action='store', type=str)

    # hash-object
    hashObjParser = cmdParser.add_parser('hash-object', help='create a blob')
    hashObjParser.add_argument('-w', help='write object in database',
                               action='store_true', default=False)
    hashObjParser.add_argument('file', help='file to store', action='store',
                               type=str)

    # ls-tree
    lsTreeParser = cmdParser.add_parser('ls-tree', help='list tree')
    lsTreeParser.add_argument('--name-only', help='list only filenames',
                              action='store_true', default=False)
    lsTreeParser.add_argument('tree', help='tree hash', type=str)

    # write-tree
    cmdParser.add_parser('write-tree', help='write tree')

    # commit-tree
    commitParser = cmdParser.add_parser('commit-tree', help='commit')
    commitParser.add_argument('tree', help='tree sha', type=str)
    commitParser.add_argument('-p', help='parent commit', dest='parent',
                              type=str, action='store')
    commitParser.add_argument('-m', help='message', dest='msg',
                              type=str, action='store')

    # clone
    cloneParser = cmdParser.add_parser('clone', help='clone repo')
    cloneParser.add_argument('url', help='repo url', type=str, action='store')
    cloneParser.add_argument('dir', help='directory', type=str, action='store')

    args = parser.parse_args()
    if args.cmd == 'init':
        initCmd()
    elif args.cmd == 'cat-file':
        catFile(args.blob, verbose=True)
    elif args.cmd == 'hash-object':
        hashObj(args.file, verbose=True)
    elif args.cmd == 'ls-tree':
        lstree(args.tree)
    elif args.cmd == 'write-tree':
        writeTree(verbose=True)
    elif args.cmd == 'commit-tree':
        commit(args.tree, args.parent, args.msg)
    elif args.cmd == 'clone':
        clone(args.url, args.dir)
    else:
        parser.print_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()