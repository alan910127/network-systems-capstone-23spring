from __future__ import annotations

import glob
import os
import threading
import xml.etree.ElementTree as ET

from my import http_2_0_client


def write_file_from_response(file_path: str, response: http_2_0_client.Response):
    if response:
        print(f"{file_path} begin")
        with open(file_path, "wb") as f:
            while True:
                content = response.get_stream_content()
                if content is None:
                    break
                f.write(content)
        print(f"{file_path} end")
    else:
        print("no response")
        
if __name__ == '__main__':
    client = http_2_0_client.HTTPClient()

    target_path = "../../target"
    response = client.get(url="http://127.0.0.1:8080/")
    file_list = []
    if response:
        headers = response.get_headers()
        if headers['content-type'] == 'text/html': # type: ignore
            body = response.get_full_body()
            root = ET.fromstring(body.decode()) # type: ignore
            links = root.findall('.//a')
            file_list: list[str | None] = []
            for link in links:
                file_list.append(link.text)

    for file in glob.glob(os.path.join(target_path, '*.txt')):
        os.remove(file)

    th_list: list[threading.Thread] = []
    for file in file_list:
        response = client.get(f"http://127.0.0.1:8080/static/{file}")
        th = threading.Thread(
            target=write_file_from_response, 
            args=[f"{target_path}/{file}", response],
        )
        th_list.append(th)
        th.start()
        
    for th in th_list:
        th.join()
