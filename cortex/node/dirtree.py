import os

def generate_tree(dir_path, prefix=""):
    tree = ""
    items = [item for item in os.listdir(dir_path) if item != 'node_modules']
    for index, item in enumerate(items):
        path = os.path.join(dir_path, item)
        connector = "├── " if index < len(items) - 1 else "└── "
        tree += f"{prefix}{connector}{item}\n"
        if os.path.isdir(path):
            tree += generate_tree(path, prefix + ("│   " if index < len(items) - 1 else "    "))
    return tree

# Specify the directory path
directory_path = "."

# Generate the directory tree
directory_tree = generate_tree(directory_path)

# Print the directory tree
print(directory_tree)
