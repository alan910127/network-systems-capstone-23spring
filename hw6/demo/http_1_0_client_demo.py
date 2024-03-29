from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET

from my import http_1_0_client

if __name__ == "__main__":
    client = http_1_0_client.HTTPClient()

    target_path = "../../target"
    response = client.get(url="http://127.0.0.1:8080/")
    file_list = []
    if response and response.headers["content-type"] == "text/html":
        root = ET.fromstring(response.get_full_body().decode()) # type: ignore
        links = root.findall(".//a")
        file_list: list[str | None] = []
        for link in links:
            file_list.append(link.text)

    for file in glob.glob(os.path.join(target_path, "*.txt")):
        os.remove(file)

    for file in file_list:
        response = client.get(f"http://127.0.0.1:8080/static/{file}", stream=True)
        file_path = f"{target_path}/{file}"
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
