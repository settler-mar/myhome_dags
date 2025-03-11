import os.path
import subprocess
import hashlib


def get_file_hash(filepath, algorithm="sha256", chunk_size=8192):
  if not os.path.exists(filepath):
    return None
  hasher = hashlib.new(algorithm)
  with open(filepath, "rb") as f:
    for chunk in iter(lambda: f.read(chunk_size), b""):
      hasher.update(chunk)
  return hasher.hexdigest()


def get_git_ls_files():
  result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
  return [(file, get_file_hash(file)) for file in result.stdout.splitlines()]


files = get_git_ls_files()

if not os.path.exists("file_list.txt"):
  with open("file_list.txt", "w") as f:
    for file, hash in files:
      f.write(f"{file} {hash}\n")
  quit()

with open("file_list.txt", "r") as f:
  new_files = [line.strip().split() for line in f]

new_files = dict(new_files)

changes = []
for file, hash in files:  # old files
  if file in new_files:
    if new_files[file] != hash:
      changes.append(f"u {file}")
  else:
    changes.append(f"d {file}")

for file in new_files:
  if file not in files:
    changes.append(f"c {file}")

with open("file_to_process.txt", "w") as f:
  for change in changes:
    f.write(f"{change}\n")
