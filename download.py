import requests
import asyncio
import requests
import time
import csv
import pathlib
from pathlib import Path
import sys
from multiprocessing import Pool, cpu_count
from functools import partial
from io import BytesIO
import subprocess
import os


ROOT_DIR = pathlib.Path(__file__).parent.resolve()


# implement pip as a subprocess:
subprocess.check_call([sys.executable, "-m", "pip", "install", "parfive"])
os.system("cls" if os.name == "nt" else "clear")

import parfive
from parfive import Downloader


def get_model_types(path):
    files = path.glob("*.csv")
    model_types = [path.stem for path in files if path.is_file()]
    return model_types


def is_non_zero_file(fpath):  # check if file exists and if it exists check is it empty
    return fpath.is_file() and fpath.stat().st_size > 0


def download_models(model_type, main_path):
    csv_path = Path(ROOT_DIR, "CSVs", model_type + ".csv")

    model_path = {
        "checkpoint": Path("models", "Stable-diffusion"),
        "lora": Path("models", "Lora"),
        "locon": Path("models", "Lora"),
        "lycoris": Path("models", "Lora"),
        "controlnet": Path("models", "ControlNet"),
        "hypernetwork": Path("models", "hypernetworks"),
        "vae": Path("models", "VAE"),
        "poses": Path("models", "Poses"),
        "other": Path("models", "Other"),
        "textualinversion": Path("Embeddings"),
        "upscaler": Path("models", "ESRGAN"),
        "aestheticgradient": Path(
            r"extensions\stable-diffusion-webui-aesthetic-gradients\aesthetic_embeddings"
        ),
        "motionmodule": Path(r"extensions\sd-webui-animatediff\model"),
    }

    try:
        sub_dir = model_path[model_type]
    except KeyError:
        sub_dir = model_path["other"]

    download_path = Path(main_path, sub_dir)

    Path(download_path).mkdir(parents=True, exist_ok=True)

    if not is_non_zero_file(csv_path):
        print("File Empty!")
        return []

    model_names = []
    model_urls = []

    with open(csv_path, "r", encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")

        for row in csv_reader:
            index, model_id, model_name, url = row
            model_names.append(model_name)
            model_urls.append(url)

        downloaderObj = Downloader()

        for model_name, url in zip(model_names, model_urls):
            if model_name and url:
                downloaderObj.enqueue_file(url, download_path)

        downloads = downloaderObj.download()

    return downloads


def main():
    csv_path = Path(ROOT_DIR.absolute(), "CSVs")
    models = get_model_types(csv_path)
    models.remove("template")

    choice = int(
        input(
            "Is this Runpod or Other/Local system?\n\
        [1] Runpod\n\
        [2] Other/Local System\n>"
        )
    )

    match choice:
        case 1:
            MAIN_PATH = Path(
                ROOT_DIR.parent.absolute(), "sd", "stable-diffusion-webui"
            ).resolve()

            if Path(MAIN_PATH, "webui.py").is_file():
                print("Found Stable Diffusion Directory")
                for model_type in models:
                    print(f"Downloading {model_type.capitalize()} files.")
                    downloads = download_models(model_type, MAIN_PATH)

                    if downloads.errors:
                        print("The following files failed.")
                        print(downloads.errors)
            else:
                print(
                    "Invalid Path. The stable diffusion base directory must contain 'webui.py' to be accepted."
                )

        case 2:
            MAIN_PATH = Path(input("Input your Stable Diffusion Path: "))

            if Path(MAIN_PATH, "webui.py").is_file():
                print("Path Accepted.")
                for model_type in models:
                    print(f"Downloading {model_type.capitalize()} files.")
                    downloads = download_models(model_type, MAIN_PATH)

                    if downloads.errors:
                        print("The following files failed.")
                        print(downloads.errors)
            else:
                print(
                    "Invalid Path. The stable diffusion base directory must contain 'webui.py' to be accepted."
                )

        case _:
            print("Invalid Option.")
            input("Please rerun the script.\n Press Return to exit.")


if __name__ == "__main__":
    main()
