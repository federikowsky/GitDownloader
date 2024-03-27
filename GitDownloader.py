import os
import re
import json
import traceback
import argparse
import asyncio

import aiohttp
import aiofiles
import colorama


class GitDownloader:
    def __init__(
            self, 
            git_permalink: str,
            git_path: str, 
            dwnld_dest: str, 
            file_list: list, 
            recursive: bool ,
            symlink: bool,
            N: int,
        ) -> None:
        
        self.__git_permalink = git_permalink
        self.__git_path = git_path
        self.__dwnld_dest = dwnld_dest
        self.__file_list = file_list
        self.__recursive = recursive
        self.__symlink = symlink
        self.__colors = {"directory": "\33[38;5;172m", "submodule": "\33[38;5;39m", "symlink_file": "\33[38;5;131m", "file": colorama.Fore.MAGENTA, "symlink_directory": colorama.Fore.YELLOW}
        self.__session = None
        self.__sem = None
        self.__N = N

    async def download_folder(self, items: list, dwnld_dest: str) -> None:
        tasks = []
        for item in items:
            item_url, item_name, item_type = item["path"], item["name"], item["contentType"]

            if item_type == 'directory' and self.__recursive:
                item_path = os.path.join(dwnld_dest, item_name)
                os.makedirs(item_path, exist_ok=True)
                print(f"{colorama.Fore.CYAN}[/] Following Dir: {item_url} {colorama.Fore.RESET}")
                tasks.append(self.fetch_file(os.path.join(self.__git_permalink, item_url), item_path))
            elif (item_type == 'file' or ((item_type == 'symlink_directory' or item_type == "symlink_file") and self.__symlink)) and (self.__file_list is None or item_name in self.__file_list):
                tasks.append(self.download_file(os.path.join(self.__git_permalink, item_url), os.path.join(dwnld_dest, item_name)))
            else:
                print(f"{self.__colors[item_type]}[!] Skipping {item_type.capitalize()}: {item_url} {colorama.Fore.RESET}")
        await asyncio.gather(*tasks)

    async def download_file(self, url: str, destination: str) -> None:
        raw_url = url.replace("/tree/", "/raw/")
        data = await self.fetch_file_data(raw_url)
        
        async with aiofiles.open(destination, 'wb') as file:
            await file.write(data)
            print(f"{colorama.Fore.GREEN}[+] Downloaded File: {destination} {colorama.Fore.RESET}")

    async def fetch_file_data(self, url: str) -> bytes:
        async with self.__sem:
            async with self.__session.get(url) as response:
                response.raise_for_status()
                res = await response.content.read()
                return res

    async def fetch_file(self, api_url: str, dwnld_dest: str) -> None:
        regex = r'<script type="application/json" data-target="react-app.embeddedData">(.*?)</script>'
        try:
            response = await self.fetch_file_data(api_url)
            data = response.decode("utf-8")
            match = re.search(regex, data, re.DOTALL)
            
            items = json.loads(match.group(1))
            items = items["payload"]["tree"]["items"]

            await self.download_folder(items, dwnld_dest)
 
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                print(f"{colorama.Fore.RED}[!] 404: url you're looking for may not exist or repo could be private. {e.request_info.url} {colorama.Fore.RESET}")
            elif e.status == 429:
                print(f"{colorama.Fore.RED} [!!] Too many requests, retrying after {e.headers.get('Retry-After')} seconds. {colorama.Fore.RESET}")
                exit(1)
                
    async def main(self):
        self.__git_permalink = self.__git_permalink.replace(self.__git_path, "")
        self.__session = aiohttp.ClientSession()
        self.__sem = asyncio.Semaphore(self.__N)
        
        async with self.__session:
            await self.fetch_file(self.__git_permalink + self.__git_path, self.__dwnld_dest)
            
    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
            exit(127)
        except Exception as e:
            print(f"{traceback.format_exc()}\n\nError: {type(e).__name__}\nMessage: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download a folder from a GitHub repository.')
    parser.add_argument('--permalink', "-pl", required=True, type=str, help='The permalink of the GitHub repository.')
    parser.add_argument('--path', '-p', required=True, type=str, help='The path of the folder to download.')
    parser.add_argument('--destination', '-dst', default='./gitdownload', type=str, help='The destination folder.')
    parser.add_argument('--recursive', '-r', type=int, default=1, help='1 if you want to download the folder recursively, 0 otherwise.')
    parser.add_argument('--file_list', '-l', type=str, default=None, nargs='+', help='The list of files to download.')
    parser.add_argument('--symlink', '-sml', type=int, default=1, help='1 if you want to follow the symlink, 0 otherwise.')
    parser.add_argument('--max_requests', '-mr', type=int, default=100, help='max number of requests to send at the same time.')
    args = parser.parse_args()
    
    git_permalink = args.permalink
    git_path = args.path
    dwnld_dest = args.destination
    file_list = args.file_list
    recursive = args.recursive
    requests = args.max_requests
    symlink = args.symlink
    
    if not os.path.exists(dwnld_dest):
        os.mkdir(dwnld_dest, mode=0o775)
    
    d = GitDownloader(
        git_permalink=git_permalink,
        git_path=git_path,
        dwnld_dest=dwnld_dest,
        file_list=file_list,
        recursive=recursive,
        symlink=symlink,
        N=requests,
    )
    
    d.run()
