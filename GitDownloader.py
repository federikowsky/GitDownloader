import os
import traceback
import aiohttp
import aiofiles
import asyncio
import json
import argparse
import colorama

class GitDownloader:
    def __init__(
            self, 
            git_permalink: str,
            git_path: str, 
            dwnld_dest: str, 
            file_list: list = None, 
            recursive: bool = True,
        ) -> None:
        
        self.__git_permalink = git_permalink
        self.__git_path = git_path
        self.__dwnld_dest = dwnld_dest
        self.__file_list = file_list
        self.__recursive = recursive
        self.__dir_tasks = []
        self.__file_tasks = []
        self.col = {"directory": colorama.Fore.RED, "file": colorama.Fore.MAGENTA}
        self.__session = None
        self.__sem = None

    async def download_folder(self, items: list) -> str | None:
        for item in items:
            item_url, item_name, item_type = item["path"], item["name"], item["contentType"]

            if item_type == 'directory' and self.__recursive:
                os.makedirs(os.path.join(dwnld_dest, item_name), exist_ok=True)
                print(f"{colorama.Fore.CYAN}[/] Following Dir: {item_url} {colorama.Fore.RESET}")
                self.__dir_tasks.append(asyncio.create_task(self.fetch_file(self.__git_permalink + item_url, dwnld_dest)))
            elif item_type == 'file' and (self.__file_list is None or item_name in self.__file_list):
                self.__file_tasks.append(asyncio.create_task(self.download_file(self.__git_permalink + item_url, os.path.join(dwnld_dest, item_name))))
            else:
                print(f"{self.col[item_type]}[!] Skipping {item_type.capitalize()}: {item_url} {colorama.Fore.RESET}")
        await asyncio.gather(*self.__file_tasks)

    async def download_file(self, url: str, destination: str) -> None:
        response = await self.fetch_file_data(url)
        data = json.loads(response)
        url_with_data = data["payload"]["blob"]["rawBlobUrl"]
        
        response_data = await self.fetch_file_data(url_with_data)
        data_content = response_data.encode('utf-8')

        async with aiofiles.open(destination, 'wb') as file:
            await file.write(data_content)
            print(f"{colorama.Fore.GREEN}[+] Downloaded File: {destination} {colorama.Fore.RESET}")


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

            await self.download_folder(items)
                                    
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                print(f"{colorama.Fore.YELLOW}[!] 404: url you're looking for may not exist or repo could be private {colorama.Fore.RESET}")
            elif e.status == 429:
                print(f"{colorama.Fore.YELLOW} [!!] Too many requests, retrying after {e.headers.get('Retry-After')} seconds. {colorama.Fore.RESET}")
                await asyncio.sleep(int(e.headers.get('Retry-After', 5)))
                self.__dir_tasks.append(asyncio.create_task(self.fetch_file(api_url, dwnld_dest)))
        # self.__dir_tasks.append(asyncio.create_task(self.fetch_file(self.__git_permalink + self.__git_path, self.__dwnld_dest)))
        await asyncio.gather(*self.__dir_tasks)        
        
    async def main(self):
        self.__git_permalink = self.__git_permalink.replace(self.__git_path, "")
        self.__session = aiohttp.ClientSession()
        self.__sem = asyncio.Semaphore(20)
        
        async with self.__session:
            await self.fetch_file(self.__git_permalink + self.__git_path, self.__dwnld_dest)
            # self.__dir_tasks.append(self.fetch_file(self.__git_permalink + self.__git_path, self.__dwnld_dest))
            # await asyncio.gather(*self.__dir_tasks)
            
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
    args = parser.parse_args()
    
    git_permalink = args.permalink
    git_path = args.path
    dwnld_dest = args.destination
    file_list = args.file_list
    recursive = args.recursive
    
    if not os.path.exists(dwnld_dest):
        os.mkdir(dwnld_dest, mode=0o775)
    
    d = GitDownloader(
        git_permalink=git_permalink,
        git_path=git_path,
        dwnld_dest=dwnld_dest,
        file_list=file_list,
        recursive=recursive,
    )
    
    d.run()
    
# exmaple:
# python GitDownloader.py -plink https://github.com/codebasics/py/tree/801ee0ee4d342fd22b89915dc0c4864250a0ec10/ML/3_gradient_descent -path ML/3_gradient_descent -dest 3_gradient_descent/tutorial -r 0
