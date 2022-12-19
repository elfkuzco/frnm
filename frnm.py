#!/usr/bin/python3

import argparse
import re
import os
import sys
import textwrap
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format=" %(asctime)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.disable(logging.CRITICAL)

EXCLUDED_CHARS = re.compile(r"[^-._0-9a-zA-Z]")


class FileRenameError(Exception):
    pass


def generate_new_pathname(file_path, char):
    """
    file_path: absolute filepath to the file/directory
    char: the substitution character.
    Returns a new name for the basename if the new name is not made up
    of `char` only.
    """
    _, old_name = os.path.split(file_path)
    if os.path.isfile(file_path):
        root, extension = os.path.splitext(old_name)
        new_root = EXCLUDED_CHARS.sub(char, root).strip(char)
        # Ensure that new name is not just totally made up of `char`
        name_components = new_root.split(char)
        name_components = list(
            filter(lambda component: component != "", name_components)
        )
        if len(name_components) < 2:
            return old_name
        new_root = char.join(name_components)
        return new_root + extension
    else:  # it's a directory
        new_name = EXCLUDED_CHARS.sub(char, old_name).strip(char)
        # Ensure that new name is not just totally made up of `char`
        name_components = new_name.split(char)
        name_components = list(
            filter(lambda component: component != "", name_components)
        )
        if len(name_components) < 2:
            return old_name
        return char.join(name_components)


def sanitize_file_name(file_path, char, verbose, suppress_errors):
    """
    file_path: Absolute path to file/directory.
    char: The character to be used as the substitution character.
    verbose: Boolean indicating whether to print successful rename of
            each file.
    suppress_errors: Boolean indicating whether to raise any errors.
    """

    dirname, old_name = os.path.split(file_path)
    new_name = generate_new_pathname(file_path, char)
    logging.info(f"New name for {old_name} => {new_name}")
    # Avoid renaming a sibling which already bears this new name
    # Filter out the original file itself
    siblings = os.listdir(dirname)
    siblings.remove(old_name)

    if new_name in siblings:
        if not suppress_errors:
            raise FileRenameError(f"File {new_name} already exists.")
    else:
        if new_name != old_name:
            src = os.path.join(dirname, old_name)
            dest = os.path.join(dirname, new_name)
            os.replace(src, dest)
            if verbose:
                print("{} ===> {}".format(src, dest))


def get_children(directory):
    """
    Returns a list of all the descendants of a directory in a topdown fashion
    i.e with the deepest child first.
    """
    children = []
    for dirpath, subFolders, filenames in os.walk(directory, topdown=False):
        for filename in filenames:
            children.append(os.path.join(dirpath, filename))
        for subFolder in subFolders:
            children.append(os.path.join(dirpath, subFolder))

    return children


def rename_file(char, *files, recursive=False, verbose=True, suppress_errors=False):
    """
    char: The substitution character.
    files: pathname(s) (relative or absolute) of files to be renamed.
    recursive: Boolean. If True, recursively rename directory and
                    descendants, else, rename directory only.
    verbose: Boolean indicating whether to print successful rename of
                    each file to screen.
    suppress_errors: Boolean. If True, suppress errors encountered and exit program.
                    Raise them otherwise.
    """

    if len(char) != 1:
        if not suppress_errors:
            raise ValueError("{char} must be a single character.".format(char=char))
        sys.exit(1)

    if EXCLUDED_CHARS.match(char):
        if not suppress_errors:
            raise ValueError(
                (
                    "Special character {char} cannot be used as a replacement character."
                    "\nAllowed replacement characters include -._0-9a-zA-Z"
                ).format(char=char)
            )
        sys.exit(1)

    # get the canonical path of the specified filenames
    resolved_paths = [os.path.realpath(file) for file in files]

    # check to ensure that file(s) actually exists
    for path in resolved_paths:
        if not os.path.exists(path):
            if not suppress_errors:
                raise FileNotFoundError(path)
            sys.exit(1)

    for path in resolved_paths:
        if os.path.isfile(path):
            sanitize_file_name(path, char, verbose, suppress_errors)
        elif os.path.isdir(path):
            # If the path is a directory and the recursive
            # flag is on, rename the deepest child first before the
            # parent path as renaming the parent path first would change the
            # real path of the child
            if recursive:
                children = get_children(path)
                for child in children:
                    sanitize_file_name(child, char, verbose, suppress_errors)
            sanitize_file_name(path, char, verbose, suppress_errors)
        else:
            # Not a regular file or directory
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
A utility Python program that renames files and folders by replacing spaces and other
unconventional characters in filenames to better filenames using a substitution
character. The characters considered to be "conventional" include: -._0-9a-zA-Z.
Any character(s) not in the set will be replaced by the substiution character.
\nfrnm will not perform the renaming of a file if:
    - the file's name is deemed standard, i.e it does not contain any of the excluded
      characters.
    - the basename of the file (stripped of the extension) is completely made
      up of the excluded characters.
"""
        ),
    )

    parser.add_argument(
        "-s",
        "--suppress-errors",
        action="store_true",
        help="Suppress exceptions and errors.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="""Do not display output rename operation of file(s).""",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="""Rename in a recursive fashion, going as deep as possible for folders.""",
    )
    parser.add_argument("-c", "--char", default="_", help="The substitution character.")
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILES",
        help="""Pathnames of files/folders to be renamed""",
    )

    args = parser.parse_args()

    rename_file(
        args.char,
        *args.files,
        recursive=args.recursive,
        verbose=not (args.quiet),
        suppress_errors=args.suppress_errors,
    )
