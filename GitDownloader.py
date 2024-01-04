import os
import aiohttp
import aiofiles
import asyncio
import json
import argparse

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

    async def download_folder_contents(self, repo: str, folder_path: str, dwnld_dest: str, session: aiohttp.ClientSession):
        api_url = f"{repo + folder_path}"

        async with session.get(api_url) as response:
            response.raise_for_status()
            response_content = await response.content.read()
            items = json.loads(response_content.decode('utf-8'))
            items = items["payload"]["tree"]["items"]

            tasks = []
            for item in items:
                item_url = item["path"]
                item_name = item["name"]
                item_type = item["contentType"]

                if item_type == 'directory' and self.__recursive:
                    item_path = os.path.join(dwnld_dest, item_name)
                    os.makedirs(item_path, exist_ok=True)
                    tasks.append(self.download_folder_contents(repo, item_url, item_path, session))

                if item_type == 'file':
                    if self.__file_list != None and item_name not in self.__file_list:
                        continue
                    else:
                        tasks.append(self.download_file(repo + item_url, os.path.join(dwnld_dest, item_name), session))

            await asyncio.gather(*tasks)

    async def download_file(self, url: str, destination: str, session: aiohttp.ClientSession):
        async with session.get(url) as response:
            response.raise_for_status()
            response_content = await response.content.read()
            data = json.loads(response_content.decode('utf-8'))
            url_with_data = data["payload"]["blob"]["rawBlobUrl"]

            async with session.get(url_with_data) as response_data:
                response_data.raise_for_status()
                data_content = await response_data.read()

                async with aiofiles.open(destination, 'wb') as file:
                    await file.write(data_content)

    async def main(self):
        self.__git_permalink = self.__git_permalink.replace(self.__git_path, "")

        async with aiohttp.ClientSession() as session:
            await self.download_folder_contents(self.__git_permalink, self.__git_path, self.__dwnld_dest, session)
            
    def run(self):
        asyncio.run(self.main())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download a folder from a GitHub repository.')
    parser.add_argument('--permalink', "-plink", required=True, type=str, help='The permalink of the GitHub repository.')
    parser.add_argument('--path', '-path', required=True, type=str, help='The path of the folder to download.')
    parser.add_argument('--destination', '-dest', default='.', type=str, help='The destination folder.')
    parser.add_argument('--recursive', '-r', type=int, default=1, help='1 if you want to download the folder recursively, 0 otherwise.')
    parser.add_argument('--file_list', '-l', type=str, default=None, nargs='+', help='The list of files to download.')
    args = parser.parse_args()
    
    git_permalink = args.permalink
    git_path = args.path
    dwnld_dest = args.destination
    file_list = args.file_list
    recursive = args.recursive
    
    if os.path.exists(dwnld_dest) and not os.path.isdir(dwnld_dest):
        raise Exception("Download destination is not a directory.")
    elif not os.path.exists(dwnld_dest):
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
