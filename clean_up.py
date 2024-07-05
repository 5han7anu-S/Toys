############################################## Timing Code ##############################################

import time
from functools import wraps

def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds")
        return result
    return wrapper

############################################## Timing Code ##############################################

import os
import hashlib
import argparse
from collections import defaultdict

file_to_hash = {}
hash_to_files = defaultdict(list)

def get_file_paths(dir):
    file_paths = []

    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            absolute_path = os.path.abspath(os.path.join(dirpath, filename))
            file_paths.append(absolute_path)

    return file_paths

def hash_file(file_path, chunk_size=8192):
    f_hash = hashlib.md5()

    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(chunk_size), b''):
            f_hash.update(byte_block)
    
    return f_hash.hexdigest()


def display_collisions(collisions):
    if collisions:
        for hash, paths in collisions.items():
            print(f"\nThe following files share the same hash ({hash}), and have the same binary data.")
            for i, path in enumerate(paths):
                print(f"{i+1} - {path}")
    else:
        print("No hash collisions found.")


def delete_duplicates(collisions):
    for _, paths in collisions.items():
        if len(paths) > 1:
            paths.sort(key=lambda p: p.count(os.sep))  # Sort by the number of directory separators
            for path in paths[1:]:  # Keep the first one, delete the rest
                try:
                    os.remove(path)
                    print(f"Deleted: {path}")
                except Exception as e:
                    print(f"Error deleting {path}: {e}")


#@time_it
def clean_up(dir, show_collisions=False, delete=False):
    file_paths = get_file_paths(dir)

    for path in file_paths:
        file_hash = hash_file(path)
        file_to_hash[path] = file_hash
        hash_to_files[file_hash].append(path)
    
    collisions = {hash: paths for hash, paths in hash_to_files.items() if len(paths) > 1}
    
    if show_collisions:
        display_collisions(collisions)
    else:
        print (f"Duplicates were found for {len(collisions)} individual files\n")

    if delete:
        input ("Proceed to Delete? Hit Enter to Continue: ")
        if collisions:
            warning_message = """
            WARNING: Deleting duplicate files can be dangerous!

            - Essential files might be duplicated intentionally for accessibility.
            - Programs may rely on these files being in specific directories.

            - This tool will delete all duplicate instances of a file. Duplicates are defined as having the same
              binary data. Only one single instance will be kept. This is will the file with the shortest path
              from root (/)

            Please consider these risks before proceeding.
            """

            print(warning_message)

            if not show_collisions:
                while True:
                    show = input("Do you want to see all the files (absolute paths) which share the same binary data? (yes/no)? ").strip().lower()
                    if show in ["yes", "y", "no", "n"]:
                        show = show in ["yes", "y"]
                        break
                    else:
                        print("Please enter 'yes'/'y' or 'no'/'n'.")

                if show:
                    display_collisions(collisions)

            while True:
                confirm_delete = input("Do you know what you are doing (yes/no)? ").strip().lower()
                if confirm_delete in ["yes", "y", "no", "n"]:
                    confirm_delete = confirm_delete in ["yes", "y"]
                    break
                else:
                    print("Please enter 'yes'/'y' or 'no'/'n'.")

            if confirm_delete:
                delete_duplicates(collisions)
            else:
                print("Aborted deletion.")
        else:
            print ("Nothing to delete. No duplicate files found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up duplicate files in a directory.")
    parser.add_argument("directory", type=str, help="Directory to clean up")
    parser.add_argument("--show-duplicates", action="store_true", help="Show duplicate file paths")
    parser.add_argument("--delete", action="store_true", help="Delete duplicate files")

    args = parser.parse_args()

    clean_up(args.directory, show_collisions=args.show_duplicates, delete=args.delete)
