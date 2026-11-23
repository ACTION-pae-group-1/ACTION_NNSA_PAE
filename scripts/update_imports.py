import os

root_dir = "src/bls_mcp"
old_module = "bls_escalation_mcp"
new_module = "bls_mcp"

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_module in content:
                new_content = content.replace(old_module, new_module)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {file_path}")
