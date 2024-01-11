# GitDownloader

## Overview

GitDownloader is a Python script that allows you to download a subfolder from a GitHub repository with ease. It is particularly useful when you need to retrieve specific files or entire directories from a GitHub project without clone the entire repo. The script utilizes asynchronous programming to efficiently download files concurrently. Don't require any GitHub token or authentication.

## Usage

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/federikowsky/GitDownloader.git
   ```

2. Install dependencies:

   ```bash
   pip install -U asyncio aiohttp aiofiles colorama
   ```
   or
    ```bash
    pip install -r requirements.txt
    ```

### Command-Line Interface

Use the following command-line arguments to customize your download:

```bash
python GitDownloader.py --permalink <repository_permalink> --path <folder_path> [--destination <download_destination>] [--recursive <1_or_0>] [--file_list <file1 file2 ...>] [--max_requests <max_concurrent_requests>]

- `--permalink` (`-plink`): The permalink of the GitHub sub folder.
- `--path` (`-path`): The path of the sub folder to download.
- `--destination` (`-dst`): The destination folder path (default: ./gitdownload).
- `--recursive` (`-r`): 1 if you want to download the folder recursively, 0 otherwise (default: 1).
- `--file_list` (`-l`): The list of files to download (default: None).
- `--max_requests` (`-maxreq`): Max number of requests to send at the same time (default: 200).
```

### Example

```bash
python GitDownloader.py -plink https://github.com/username/repository/tree/commit_hash/path/to/folder -path path/to/folder --destination ./download_folder --recursive 1 --file_list file1.txt file2.txt --max_requests 50
```

### How to get permalink and path

1. Navigate to the desired folder within the repository.
2. Click on the three dots (...) to reveal additional options.
3. In the menu that appears, select the shortcuts to copy the permalink and path values."

### Prerequisites

- Python 3.7 or later
- Required Python packages (install using `pip install -r requirements.txt`):
- [Aiohttp](https://docs.aiohttp.org/en/stable/) library
- [Colorama](https://pypi.org/project/colorama/) library
- [Aiofile](https://pypi.org/project/aiofiles/) library

## License
This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Features

- Efficiently downloads files concurrently using asynchronous programming.
- Supports recursive downloading of subdirectories.
- Allows filtering of specific files using a file list.
- Provides a customizable number of concurrent download requests.
- No token or authentication required
