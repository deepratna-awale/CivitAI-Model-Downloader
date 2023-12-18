# CivitAI Batch Model Downloader
The base of the notebook is from @github/TheLastBen Stable Diffusion Runpod Notebook[^1].


# Requirements
- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

- [Python 3 and pip](https://www.python.org/downloads/)

- [Parfive python library](https://pypi.org/project/parfive/) Automatically installed by `download.py`.


# Installation

## I. On Runpod

1. Select the RunPod Fast Stable Diffusion Image from Runpod Templates and Deploy it.

2. Adjust your Disk Volume if required from **Customize Deployment**.

![Select RunPod Fast Stable Diffusion Image on runpod](<src/common/RunpodImageSelection.png>)

3. Connect to Jupyter Lab.

![Connect to Jupyter Lab](<src/common/ConnectToJupyterNotebook.png>)


4. Open a terminal from launcher. Clone this repo and copy the contents of downloaded repo to the main folder.

```sh
git clone https://github.com/deepratnaawale/CivitAIBatchModelDownloader.git 
```
```sh
mv CivitAIBatchModelDownloader/* ..
```
```sh
rmdir CivitAIBatchModelDownloader/
```

5. Use downloader to download files from the csvs.
```sh
python download.py
```

> [!NOTE]
> The Downloader will Automatically download content from every CSV in the [CSVs Directory](<CSVs/>) to the default download location.


## II. Local Install

1. Open a terminal from launcher. Clone this repo using

```sh
git clone https://github.com/deepratnaawale/CivitAIBatchModelDownloader.git
```

> [!WARNING]
>  If you want to use the downloader locally, you need to change the following:
1. Open `download.py` and search for `main_path` and change that line to:

```python
main_path = Path("path/containing/stablediffusion/")
```
Please replace the path in quotes with actual directory of `Stable Diffusion`.
Please note that the `SD Directory` is the one with `webui.py` in it.

1. Use downloader to download files from the csvs. Please read the Tweaks section!
```sh
python download.py 
```


# Tweaks

1. If needed, you can edit the default paths in the `download.py` file.
   
```python
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
        "aestheticgradient": Path(r"extensions\stable-diffusion-webui-aesthetic-gradients\aesthetic_embeddings"),
        "motionmodule": Path(r"extensions\sd-webui-animatediff\model")
        
    }
```
The format is 
```python
model_type: Path(path/to/download/model/to/)
```
Don't forget to add the a `,` if your model isn't the last one. do not use plural in dict key, i.e. `lora` NOT `loras`, **lowercase necessary!**


# CSV Structure

> [!CAUTION]
> All your models should be in their respective csvs.
> Ex: `checkpoint.csv` should have all checkpoint models.

- All your CSVs are should be the following format

Sr.no | Model ID| Model Name | Model URL
--- | --- | --- | ---
1 | 4201 | Realistic Vision V4.0 | https://civitai.com/api/download/models/114367
2 | ... | ... | ... 
3 | ... | ... | ... 

> [!HINT]
> You can automatically create these CSVs using my [CivitAI-DownloadLink-Extractor](https://github.com/deepratnaawale/CivitAI-DownloadLink-Extractor) repository.


# Credits

[^1]: [The Last Ben Fast Stable Diffusion Runpod](https://github.com/TheLastBen/fast-stable-diffusion)
