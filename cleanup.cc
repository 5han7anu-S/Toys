#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <unordered_map>
#include <algorithm>
#include <chrono>
#include <thread>
#include <future>
#include <mutex>
#include <system_error>
#include <queue>
#include <openssl/evp.h>

// Namespace alias for cleaner code
namespace fs = std::filesystem;

// ---------------------------------------------------------
// Helper: Time execution (RAII style)
// ---------------------------------------------------------
class Timer {
    std::string name;
    std::chrono::high_resolution_clock::time_point start;
public:
    Timer(const std::string& func_name) : name(func_name), start(std::chrono::high_resolution_clock::now()) {}
    ~Timer() {
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;
        std::cout << "Function '" << name << "' executed in " << elapsed.count() << " seconds\n";
    }
};

// ---------------------------------------------------------
// Helper: Calculate MD5 Hash
// ---------------------------------------------------------
std::string hash_file(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return ""; // Permission denied or file missing

    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    const EVP_MD* md = EVP_md5();
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int md_len;

    EVP_DigestInit_ex(mdctx, md, NULL);

    char buffer[8192];
    while (file.read(buffer, sizeof(buffer))) {
        EVP_DigestUpdate(mdctx, buffer, file.gcount());
    }
    EVP_DigestUpdate(mdctx, buffer, file.gcount()); // Handle remaining bytes

    EVP_DigestFinal_ex(mdctx, hash, &md_len);
    EVP_MD_CTX_free(mdctx);

    std::stringstream ss;
    for (unsigned int i = 0; i < md_len; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)hash[i];
    }
    return ss.str();
}

// ---------------------------------------------------------
// Logic: Thread Pool for Parallel Hashing
// ---------------------------------------------------------
struct FileResult {
    fs::path path;
    std::string hash;
};

std::vector<FileResult> process_files_parallel(const std::vector<fs::path>& files) {
    unsigned int num_threads = std::thread::hardware_concurrency();
    if (num_threads == 0) num_threads = 4; // Fallback

    std::queue<fs::path> work_queue;
    for (const auto& f : files) work_queue.push(f);

    std::mutex queue_mutex;
    std::vector<FileResult> results;
    std::mutex results_mutex;
    std::vector<std::thread> workers;

    auto worker = [&]() {
        while (true) {
            fs::path p;
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                if (work_queue.empty()) return;
                p = work_queue.front();
                work_queue.pop();
            }
            
            // Hash without holding the lock (Parallel part)
            std::string h = hash_file(p);
            
            if (!h.empty()) {
                std::lock_guard<std::mutex> res_lock(results_mutex);
                results.push_back({p, h});
            }
        }
    };

    for (unsigned int i = 0; i < num_threads; ++i) {
        workers.emplace_back(worker);
    }

    for (auto& t : workers) {
        if (t.joinable()) t.join();
    }

    return results;
}

// ---------------------------------------------------------
// Logic: Core Functionality
// ---------------------------------------------------------


std::vector<fs::path> get_file_paths(const std::string& dir) {
    std::vector<fs::path> file_paths;
    
    // Check if the directory exists first
    std::error_code ec_dir_check;
    if (!fs::exists(dir, ec_dir_check) || !fs::is_directory(dir, ec_dir_check)) {
        std::cerr << "Error: Directory not found or inaccessible: " << dir << "\n";
        return file_paths;
    }

    // Start the recursive iteration
    // Use the error_code overload to prevent throwing an exception
    // when a permission issue is encountered.
    fs::recursive_directory_iterator it(dir, ec_dir_check);
    
    // Check for an initial error before looping
    if (ec_dir_check) {
        std::cerr << "Error initializing iterator for " << dir << ": " << ec_dir_check.message() << "\n";
        return file_paths;
    }
    
    // Create a default iterator for the end condition
    fs::recursive_directory_iterator end_it;

    try {
        for (; it != end_it; it.increment(ec_dir_check)) {
            // If the increment caused an error (e.g., Permission denied)
            if (ec_dir_check) {
                std::cerr << "Skipping inaccessible directory: " << it->path().string() << " (" << ec_dir_check.message() << ")\n";
                // Clear the error code and reset for the next increment
                ec_dir_check.clear(); 
                continue; 
            }

            // Standard file processing logic
            if (fs::is_regular_file(*it)) {
                file_paths.push_back(fs::absolute(it->path()));
            }
        }
    } catch (const fs::filesystem_error& e) {
        // This catch block is less likely to be hit with the error_code overload, 
        // but it's kept for general safety.
        std::cerr << "General Filesystem error during traversal: " << e.what() << "\n";
    }
    
    return file_paths;
}

void display_collisions(const std::unordered_map<std::string, std::vector<fs::path>>& collisions) {
    if (collisions.empty()) {
        std::cout << "No hash collisions found.\n";
        return;
    }
    for (const auto& [hash, paths] : collisions) {
        std::cout << "\nThe following files share the same hash (" << hash << "):\n";
        for (size_t i = 0; i < paths.size(); ++i) {
            std::cout << i + 1 << " - " << paths[i].string() << "\n";
        }
    }
}

void delete_duplicates(std::unordered_map<std::string, std::vector<fs::path>>& collisions) {
    for (auto& [hash, paths] : collisions) {
        if (paths.size() > 1) {
            // Sort by number of directory separators (depth), simplest/shortest path first
            std::sort(paths.begin(), paths.end(), [](const fs::path& a, const fs::path& b) {
                std::string sa = a.string();
                std::string sb = b.string();
                return std::count(sa.begin(), sa.end(), fs::path::preferred_separator) < 
                       std::count(sb.begin(), sb.end(), fs::path::preferred_separator);
            });

            // Keep the first one (index 0), delete the rest
            for (size_t i = 1; i < paths.size(); ++i) {
                try {
                    if (fs::remove(paths[i])) {
                        std::cout << "Deleted: " << paths[i] << "\n";
                    } else {
                        std::cerr << "Failed to delete: " << paths[i] << "\n";
                    }
                } catch (const fs::filesystem_error& e) {
                    std::cerr << "Error deleting " << paths[i] << ": " << e.what() << "\n";
                }
            }
        }
    }
}

// ---------------------------------------------------------
// Main Control
// ---------------------------------------------------------
void clean_up(const std::string& dir, bool show_collisions, bool delete_flag) {
    Timer timer("clean_up"); // Helper class replicates the python decorator

    std::cout << "Gathering file paths...\n";
    std::vector<fs::path> file_paths = get_file_paths(dir);
    
    std::cout << "Found " << file_paths.size() << " files. Hashing in parallel...\n";

    // Run Parallel Hashing
    std::vector<FileResult> results = process_files_parallel(file_paths);

    // Aggregate results
    std::unordered_map<std::string, std::vector<fs::path>> hash_to_files;
    for (const auto& res : results) {
        hash_to_files[res.hash].push_back(res.path);
    }

    // Filter collisions
    std::unordered_map<std::string, std::vector<fs::path>> collisions;
    for (const auto& entry : hash_to_files) {
        if (entry.second.size() > 1) {
            collisions[entry.first] = entry.second;
        }
    }

    if (show_collisions) {
        display_collisions(collisions);
    } else {
        std::cout << "Duplicates were found for " << collisions.size() << " individual files\n\n";
    }

    if (delete_flag) {
        if (collisions.empty()) {
            std::cout << "Nothing to delete. No duplicate files found\n";
            return;
        }

        std::cout << "Proceed to Delete? Hit Enter to Continue: ";
        std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // Wait for enter
        if (std::cin.peek() == '\n') std::cin.ignore(); 

        std::cout << "\n\tWARNING: Deleting duplicate files can be dangerous!\n"
                  << "\t- This tool will delete all duplicate instances.\n"
                  << "\t- Only the single instance with the shortest path will be kept.\n\n";

        if (!show_collisions) {
            std::cout << "Do you want to see all the files which share the same binary data? (yes/no): ";
            std::string resp;
            std::cin >> resp;
            if (resp == "yes" || resp == "y") {
                display_collisions(collisions);
            }
        }

        std::cout << "Do you know what you are doing (yes/no)? ";
        std::string confirm;
        std::cin >> confirm;

        if (confirm == "yes" || confirm == "y") {
            delete_duplicates(collisions);
        } else {
            std::cout << "Aborted deletion.\n";
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " <directory> [--show-duplicates] [--delete]\n";
        return 1;
    }

    std::string directory = argv[1];
    bool show_duplicates = false;
    bool delete_flag = false;

    for (int i = 2; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--show-duplicates") show_duplicates = true;
        else if (arg == "--delete") delete_flag = true;
    }

    clean_up(directory, show_duplicates, delete_flag);

    return 0;
}
