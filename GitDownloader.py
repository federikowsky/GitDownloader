import os
import json
import traceback
import argparse

import aiohttp
import aiofiles
import asyncio
import colorama


class GitDownloader:
    def __init__(
            self, 
            git_permalink: str,
            git_path: str, 
            dwnld_dest: str, 
            file_list: list, 
            recursive: bool ,
            N: int,
        ) -> None:
        
        self.__git_permalink = git_permalink
        self.__git_path = git_path
        self.__dwnld_dest = dwnld_dest
        self.__file_list = file_list
        self.__recursive = recursive
        self.__colors = {"directory": colorama.Fore.RED, "file": colorama.Fore.MAGENTA}
        self.__session = None
        self.__sem = None
        self.N = N

    async def download_folder(self, items: list, dwnld_dest: str) -> None:
        tasks = []
        for item in items:
            item_url, item_name, item_type = item["path"], item["name"], item["contentType"]

            if item_type == 'directory' and self.__recursive:
                item_path = os.path.join(dwnld_dest, item_name)
                os.makedirs(item_path, exist_ok=True)
                print(f"{colorama.Fore.CYAN}[/] Following Dir: {item_url} {colorama.Fore.RESET}")
                tasks.append(self.fetch_file(self.__git_permalink + item_url, item_path))
            elif item_type == 'file' and (self.__file_list is None or item_name in self.__file_list):
                tasks.append(self.download_file(self.__git_permalink + item_url, os.path.join(dwnld_dest, item_name)))
            else:
                print(f"{self.__colors[item_type]}[!] Skipping {item_type.capitalize()}: {item_url} {colorama.Fore.RESET}")
        await asyncio.gather(*tasks)

    async def download_file(self, url: str, destination: str) -> None:
        url_with_data = url.replace("/tree/", "/raw/")
        data_content = await self.fetch_file_raw_data(url_with_data)
        
        async with aiofiles.open(destination, 'wb') as file:
            await file.write(data_content)
            print(f"{colorama.Fore.GREEN}[+] Downloaded File: {destination} {colorama.Fore.RESET}")

    async def fetch_file_raw_data(self, url: str) -> aiohttp.ClientResponse:
        async with self.__sem:
            async with self.__session.get(url) as response:
                response.raise_for_status()
                res = await response.content.read()
                return res
            
    async def fetch_file_data(self, url: str) -> aiohttp.ClientResponse:
        async with self.__sem:
            async with self.__session.get(url) as response:
                response.raise_for_status()
                res = await response.text()
                return res

    async def fetch_file(self, api_url: str, dwnld_dest: str) -> None:
        try:
            response = await self.fetch_file_data(api_url)
            items = json.loads(response)
            items = items["payload"]["tree"]["items"]

            await self.download_folder(items, dwnld_dest)

        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                print(f"{colorama.Fore.YELLOW}[!] 404: url you're looking for may not exist or repo could be private. {e.request_info.url} {colorama.Fore.RESET}")
            elif e.status == 429:
                print(f"{colorama.Fore.YELLOW} [!!] Too many requests, retrying after {e.headers.get('Retry-After')} seconds. {colorama.Fore.RESET}")
                exit(1)
                
    async def main(self):
        self.__git_permalink = self.__git_permalink.replace(self.__git_path, "")
        self.__session = aiohttp.ClientSession()
        self.__sem = asyncio.Semaphore(self.N)
        
        async with self.__session:
            await self.fetch_file(self.__git_permalink + self.__git_path, self.__dwnld_dest)
            
    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            exit(127)
        except Exception as e:
            print(f"{traceback.format_exc()}\n\nError: {type(e).__name__}\nMessage: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download a folder from a GitHub repository.')
    parser.add_argument('--permalink', "-plink", required=True, type=str, help='The permalink of the GitHub repository.')
    parser.add_argument('--path', '-path', required=True, type=str, help='The path of the folder to download.')
    parser.add_argument('--destination', '-dst', default='./gitdownload', type=str, help='The destination folder.')
    parser.add_argument('--recursive', '-r', type=int, default=1, help='1 if you want to download the folder recursively, 0 otherwise.')
    parser.add_argument('--file_list', '-l', type=str, default=None, nargs='+', help='The list of files to download.')
    parser.add_argument('--max_requests', '-maxreq', type=int, default=200, help='max number of requests to send at the same time.')
    args = parser.parse_args()
    
    git_permalink = args.permalink
    git_path = args.path
    dwnld_dest = args.destination
    file_list = args.file_list
    recursive = args.recursive
    requests = args.max_requests
    
    if not os.path.exists(dwnld_dest):
        os.mkdir(dwnld_dest, mode=0o775)
    
    d = GitDownloader(
        git_permalink=git_permalink,
        git_path=git_path,
        dwnld_dest=dwnld_dest,
        file_list=file_list,
        recursive=recursive,
        N=requests,
    )
    
    d.run()
