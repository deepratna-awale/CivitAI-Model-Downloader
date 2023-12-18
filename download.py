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

# implement pip as a subprocess:
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'parfive'])
import parfive
from parfive import Downloader

# Constants
CWD = Path.cwd()

def get_model_types(path):
    files = path.glob("*.csv")
    model_types = [path.stem for path in files if path.is_file()]
    return model_types


def is_non_zero_file(fpath):  # check if file exists and if it exists check is it empty
    return fpath.is_file() and fpath.stat().st_size > 0


def load_model(model_type):
    csv_path = Path(Path.cwd(), "CSVs", model_type + ".csv")

    main_path = Path(Path.cwd(), "sd")

    model_path = {
        "checkpoint": Path("stable-diffusion-webui", "models", "Stable-diffusion"),
        "lora": Path("stable-diffusion-webui", "models", "Lora"),
        "locon": Path("stable-diffusion-webui", "models", "Lora"),
        "lycoris": Path("stable-diffusion-webui", "models", "Lora"),
        "controlnet": Path("stable-diffusion-webui", "models", "ControlNet"),
        "hypernetwork": Path("stable-diffusion-webui", "models", "hypernetworks"),
        "vae": Path("stable-diffusion-webui", "models", "VAE"),
        "poses": Path("stable-diffusion-webui", "models", "Poses"),
        "other": Path("stable-diffusion-webui", "models", "Other"),
        "textualinversion": Path("stable-diffusion-webui", "Embeddings"),
        "upscaler": Path("stable-diffusion-webui", "models", "ESRGAN"),
        "aestheticgradient": Path("stable-diffusion-webui", r"extensions\stable-diffusion-webui-aesthetic-gradients\aesthetic_embeddings"),
        "motionmodule": Path("stable-diffusion-webui", r"extensions\sd-webui-animatediff\model")
        
    }
    try:
        sub_dir = model_path[model_type]
    except KeyError:
        sub_dir = model_path["other"]
        
    download_path = Path(main_path, sub_dir)
    if not is_non_zero_file(csv_path):
        print("File Empty!")
        return

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
        downloaderObj.enqueue_file(url, download_path)

    downloads = downloaderObj.download()

    return downloads


def main():
    csv_path = Path(Path.cwd(), "CSVs")
    models = get_model_types(csv_path)

    for model_type in models:
        print(f"Downloading {model_type.capitalize()} files.")
        downloads = load_model(model_type)
        
        if downloads.errors:
            print("The following files failed.")
            print(downloads.errors)


if __name__ == "__main__":
    main()
