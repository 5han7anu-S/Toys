import os
import random
import string
import argparse

def generate_random_text(length):
    letters = string.ascii_letters + string.digits + string.punctuation + ' '
    return ''.join(random.choice(letters) for _ in range(length))

def generate_random_name(length=8):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def generate_file_paths(base_path, num_dirs, num_files_per_dir, depth, current_depth=0):
    file_paths = []
    if current_depth >= depth:
        return file_paths

    for _ in range(num_dirs):
        dir_name = generate_random_name()
        dir_path = os.path.join(base_path, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        for _ in range(num_files_per_dir):
            file_name = generate_random_name() + random.choice(['.mov', '.mp4', '.pdf', '.jpg', '.png', '.c', '.cpp', '.js', '.rs', '.sv', '.docx', '.ppt'])
            file_paths.append(os.path.join(dir_path, file_name))
        
        file_paths.extend(generate_file_paths(dir_path, num_dirs, num_files_per_dir, depth, current_depth + 1))
    
    return file_paths

import math

def populate_files(file_paths, text_length, duplicate_percentage, num_files_per_dir):
    total_files = len(file_paths)
    num_duplicates = int(total_files * duplicate_percentage / 100)
    duplicate_count = num_duplicates // num_files_per_dir

    random.shuffle(file_paths)
    
    unique_files = total_files - num_duplicates
    files_since_last_duplicate = 0

    duplicate_content_list = [generate_random_text(text_length) for _ in range(duplicate_count)]
    duplicate_index = 0

    for i, file_path in enumerate(file_paths):
        with open(file_path, 'w') as file:
            if files_since_last_duplicate < num_files_per_dir and duplicate_index < duplicate_count:
                if files_since_last_duplicate == 0:
                    current_duplicate_content = duplicate_content_list[duplicate_index]
                    duplicate_index += 1
                file.write(current_duplicate_content)
                files_since_last_duplicate += 1
                if files_since_last_duplicate == num_files_per_dir:
                    files_since_last_duplicate = 0
            else:
                file.write(generate_random_text(text_length))
                files_since_last_duplicate = 0 if duplicate_index < duplicate_count else files_since_last_duplicate + 1




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate directories and files with random text.")
    parser.add_argument('root_dir', type=str, help="Root directory where directories and files will be generated")

    args = parser.parse_args()

    # Configuration parameters
    num_dirs = 2  # Number of subdirectories to create in each directory
    num_files_per_dir = 10  # Number of files per directory
    text_length = 100  # Length of random text in each file
    depth = 5  # Depth of the directory structure
    duplicate_percentage = 20  # Percentage of files that should have duplicate content

    # Generate file paths
    file_paths = generate_file_paths(args.root_dir, num_dirs, num_files_per_dir, depth)
    # Populate files with random and duplicate content

    populate_files(file_paths, text_length, duplicate_percentage, num_files_per_dir)

    print(f"Generated directory structure in {args.root_dir} with depth {depth}.")
