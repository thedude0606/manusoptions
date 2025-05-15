# fix_streaming_manager.py
file_path = "/home/ubuntu/manusoptions_project/manusoptions/dashboard_utils/streaming_manager.py"
problem_line_content = "(Content truncated due to size limit. Use line ranges to read in chunks)"
fixed = False

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    line_removed_at = -1
    original_line_numbers_of_removed_lines = []

    for i, line in enumerate(lines):
        # Check if the stripped line exactly matches the problematic content
        if line.strip() == problem_line_content:
            original_line_numbers_of_removed_lines.append(i + 1) # 1-indexed for reporting
            fixed = True
            continue # Skip adding this line to new_lines
        new_lines.append(line)

    if fixed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Successfully removed occurrences of the problematic line from {file_path}.")
        print(f"Problematic line was found and removed at original line number(s): {original_line_numbers_of_removed_lines}")
    else:
        print(f"The problematic line '{problem_line_content}' was not found as a standalone stripped line in {file_path}. No changes made.")
        # For debugging, let's print the content of line 287 if the file is long enough
        if len(lines) >= 287:
            print(f"Content of original line 287 (0-indexed {286}): {lines[286].strip()}")
        elif len(lines) > 0:
            print(f"File has only {len(lines)} lines, which is less than 287. Showing last few lines:")
            for i in range(max(0, len(lines)-5), len(lines)):
                print(f"L{i+1}: {lines[i].strip()}")
        else:
            print("File is empty.")

except FileNotFoundError:
    print(f"Error: The file {file_path} was not found.")
except Exception as e:
    print(f"Error processing file: {e}")

