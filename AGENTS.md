* Don't use the os library to interact with the file system. Instead, use `bashshim.filesystem`.
    - The following functions are in the FileSystem class  
        - exists(path) - Returns if a file exists.  
        - mkdir(path, exist_ok, parents) - Creates a directory at the path. Same params as pathlib's mkdir.  
        - rmdir(path) - Remove a directory.  
        - listdir(path) - method returns a list of the names of the entries (files and directories) in the directory given by path.  
        - open(path, mode, encoding) - opens the file at the given path with the specified mode (default is read mode, 'r') and optional encoding. It returns a file object.  
        - read_text(path) - reads the entire contents of the file at the given path and returns it as a string.  
        - write_text(path, data) - writes the string data to the file at the given path, overwriting any existing content.  
        - touch(path, exist_ok=True) - creates a new empty file at the given path, or updates the modification time if it exists. If exist_ok is True, no error is raised if the file already exists.  
        - remove(path) - deletes the file at the given path.  
        - stat(path) - returns a stat result object containing information about the file or directory at the given path.  
        - is_file(path) - returns True if the path points to a regular file.  
        - is_dir(path) - returns True if the path points to a directory.  
        - append_text(path, data) - appends the string data to the end of the file at the given path. If the file does not exist, it is created.  

**Note:**  
Do not use `os` functions like `os.listdir`, `os.path.exists`, or the built-in `open` directly. Always use the methods provided by the `FileSystem` class for file and directory operations.