# CivitAI Batch Model Downloader
One click Multi-thread download solution for all Civit-Ai models.

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
![Connect to Jupyter Lab Instance](<src/common/ConnectToJupyterNotebook.png>)

4. Open a terminal from launcher. Clone this repo and copy the contents of downloaded repo to the main folder.

```sh
git clone https://github.com/deepratnaawale/CivitAIBatchModelDownloader.git
```
5. Done!

## II. Local Install

1. Open a terminal from launcher. Clone this repo using

```sh
git clone https://github.com/deepratnaawale/CivitAIBatchModelDownloader.git
```
2. Done!


# Using the Downloader
> [!NOTE]
> The Downloader will Automatically download content from every CSV in the [CSVs Directory](<CSVs/>) to the default download location.

1. Goto CivitAIBatchModelDownloader directory 
```sh
cd CivitAIBatchModelDownloader/
```

2. Use downloader to download files from the csvs by typing the following in the terminal.
```sh
python download.py
```
3. Choose the option you want to use: 1 for Runpod, and 2 for any other systems. DO NOT TYPE THE BRACKETS, just the number.


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
Don't forget to add the a `,` if your model isn't the last one. Do not use plural in dict key, i.e. `lora` NOT `loras`, **lowercase necessary!**


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

