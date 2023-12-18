# CivitAI Batch Model Downloader
The base of the notebook is from @github/TheLastBen Stable Diffusion Runpod Notebook[^1].

> [!IMPORTANT]
> Git is Required! Please install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

> [!NOTE]
> If you are running this on Runpod, git should already  be installed!

# Requirements
- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

- [Python 3 and pip](https://www.python.org/downloads/)

- [Parfive python library](https://pypi.org/project/parfive/) Automatically installed by `download.py`.



# Installation

## I. On Runpod

1. Select the RunPod Fast Stable Diffusion Image from Runpod Templates and Deploy it.

2. Make adjustments to your Disk Volume if required from **Customize Deployment**.

![Select RunPod Fast Stable Diffusion Image on runpod](<src/common/RunpodImageSelection.png>)


3. Connect to Jupyter Lab.

![Connect to Jupyter Lab](<src/common/ConnectToJupyterNotebook.png>)

4. Open a terminal from launcher. Clone this repo using

```sh
git clone deepratnaawale/CivitAIBatchModelDownloader
```
5. Copy the contents of downloaded repo to the main folder. Use the following p

```sh
cp -vaR CivitAIBatchModelDownloader/.. && rmdir CivitAIBatchModelDownloader/
```

6. Use downloader to download files from the csvs.
```sh
python download.py
```

> [!NOTE]
> It will Automatically download content from every CSV in the [CSVs Directory](<CSVs/>) to the default location.




## II. Local Install

1. Open a terminal from launcher. Clone this repo using

```sh
git clone deepratnaawale/CivitAIBatchModelDownloader
```

2. Use downloader to download files from the csvs.
```sh
python download.py
```

3. If needed, you can edit the default paths in the `download.py` file.
   
```python
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
```
The format is 
```python
model_type: Path(path/to/download/model/to/)
```
Don't forget to add a `,` if your model path isn't the last one.


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
