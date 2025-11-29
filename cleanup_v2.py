import os
import hashlib
import argparse
import time
from collections import defaultdict
from functools import wraps
from concurrent.futures import ProcessPoolExecutor

############################################## Timing Code ##############################################

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

############################################## Core Logic ##############################################

file_to_hash = {}
hash_to_files = defaultdict(list)

def get_file_paths(directory):
    file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            absolute_path = os.path.abspath(os.path.join(dirpath, filename))
            file_paths.append(absolute_path)
    return file_paths

def process_file(file_path, chunk_size=8192):
    """
    Worker function to be run in parallel.
    Returns a tuple: (file_path, hash_string)
    """
    try:
        f_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(chunk_size), b''):
                f_hash.update(byte_block)
        return file_path, f_hash.hexdigest()
    except (OSError, PermissionError):
        # Return None for the hash if the file cannot be read
        return file_path, None

def display_collisions(collisions):
    if collisions:
        for f_hash, paths in collisions.items():
            print(f"\nThe following files share the same hash ({f_hash}), and have the same binary data.")
            for i, path in enumerate(paths):
                print(f"{i+1} - {path}")
    else:
        print("No hash collisions found.")

def delete_duplicates(collisions):
    for _, paths in collisions.items():
        if len(paths) > 1:
            # Sort by the number of directory separators (keep shortest path)
            paths.sort(key=lambda p: p.count(os.sep))
            
            # Keep the first one, delete the rest
            for path in paths[1:]:
                try:
                    os.remove(path)
                    print(f"Deleted: {path}")
                except Exception as e:
                    print(f"Error deleting {path}: {e}")

@time_it
def clean_up(directory, show_collisions=False, delete=False):
    print("Gathering file paths...")
    file_paths = get_file_paths(directory)
    print(f"Found {len(file_paths)} files. Hashing in parallel...")

    # PARALLEL EXECUTION START
    # We use ProcessPoolExecutor to utilize multiple CPU cores
    with ProcessPoolExecutor() as executor:
        # map returns an iterator of results in the order calls were started
        results = executor.map(process_file, file_paths)

        for path, file_hash in results:
            if file_hash: # Only proceed if hash was successfully calculated
                file_to_hash[path] = file_hash
                hash_to_files[file_hash].append(path)
    # PARALLEL EXECUTION END
    
    collisions = {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}
    
    if show_collisions:
        display_collisions(collisions)
    else:
        print(f"Duplicates were found for {len(collisions)} individual files\n")

    if delete:
        # Note: input() handles Ctrl+C gracefully usually, but be aware 
        # that stopping a script mid-execution requires care.
        try:
            input("Proceed to Delete? Hit Enter to Continue (Ctrl+C to abort): ")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return

        if collisions:
            warning_message = """
            WARNING: Deleting duplicate files can be dangerous!

            - Essential files might be duplicated intentionally for accessibility.
            - Programs may rely on these files being in specific directories.

            - This tool will delete all duplicate instances of a file. Duplicates are defined as having the same
              binary data. Only one single instance will be kept. This will be the file with the shortest path
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
            print("Nothing to delete. No duplicate files found")

if __name__ == "__main__":
    # Multiprocessing requires the main execution to be guarded by if __name__ == "__main__"
    # to prevent recursive process spawning on Windows.
    parser = argparse.ArgumentParser(description="Clean up duplicate files in a directory.")
    parser.add_argument("directory", type=str, help="Directory to clean up")
    parser.add_argument("--show-duplicates", action="store_true", help="Show duplicate file paths")
    parser.add_argument("--delete", action="store_true", help="Delete duplicate files")

    args = parser.parse_args()

    clean_up(args.directory, show_collisions=args.show_duplicates, delete=args.delete)