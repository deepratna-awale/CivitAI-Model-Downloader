import os
from IPython.display import clear_output
from subprocess import call, getoutput, Popen, run
import time
import ipywidgets as widgets
import requests
import sys
import fileinput
from torch.hub import download_url_to_file
from urllib.parse import urlparse, parse_qs, unquote
import re
import six

from urllib.request import urlopen, Request
import tempfile
from tqdm import tqdm


def Deps(force_reinstall):

	if not force_reinstall and os.path.exists('/usr/local/lib/python3.10/dist-packages/safetensors'):
		ntbks()
		print('[1;32mModules and notebooks updated, dependencies already installed')
		os.environ['TORCH_HOME'] = '/workspace/cache/torch'
		os.environ['PYTHONWARNINGS'] = 'ignore'
	else:
		call('pip install --root-user-action=ignore --disable-pip-version-check --no-deps -qq gdown PyWavelets numpy==1.23.5 accelerate==0.12.0 --force-reinstall',
			shell=True, stdout=open('/dev/null', 'w'))
		ntbks()
		if os.path.exists('deps'):
			call("rm -r deps", shell=True)
		if os.path.exists('diffusers'):
			call("rm -r diffusers", shell=True)
		call('mkdir deps', shell=True)
		if not os.path.exists('cache'):
			call('mkdir cache', shell=True)
		os.chdir('deps')
		dwn("https://huggingface.co/TheLastBen/dependencies/resolve/main/rnpddeps-t2.tar.zst",
			"/workspace/deps/rnpddeps-t2.tar.zst", "Installing dependencies")
		call('tar -C / --zstd -xf rnpddeps-t2.tar.zst',
			shell=True, stdout=open('/dev/null', 'w'))
		call("sed -i 's@~/.cache@/workspace/cache@' /usr/local/lib/python3.10/dist-packages/transformers/utils/hub.py", shell=True)
		os.chdir('/workspace')
		call("git clone --depth 1 -q --branch main https://github.com/TheLastBen/diffusers",
			shell=True, stdout=open('/dev/null', 'w'))
		call('pip install --root-user-action=ignore --disable-pip-version-check -qq gradio==3.41.2',
			shell=True, stdout=open('/dev/null', 'w'))
		call("rm -r deps", shell=True)
		os.chdir('/workspace')
		os.environ['TORCH_HOME'] = '/workspace/cache/torch'
		os.environ['PYTHONWARNINGS'] = 'ignore'
		call("sed -i 's@text = _formatwarnmsg(msg)@text =\"\"@g' /usr/lib/python3.10/warnings.py", shell=True)
		clear_output()

		done()


def dwn(url, dst, msg):
	file_size = None
	req = Request(url, headers={"User-Agent": "torch.hub"})
	u = urlopen(req)
	meta = u.info()
	if hasattr(meta, 'getheaders'):
		content_length = meta.getheaders("Content-Length")
	else:
		content_length = meta.get_all("Content-Length")
	if content_length is not None and len(content_length) > 0:
		file_size = int(content_length[0])

	with tqdm(total=file_size, disable=False, mininterval=0.5,
			bar_format=msg+' |{bar:20}| {percentage:3.0f}%') as pbar:
		with open(dst, "wb") as f:
			while True:
				buffer = u.read(8192)
				if len(buffer) == 0:
					break
				f.write(buffer)
				pbar.update(len(buffer))
			f.close()


def ntbks():

	os.chdir('/workspace')
	if not os.path.exists('Latest_Notebooks'):
		call('mkdir Latest_Notebooks', shell=True)
	else:
		call('rm -r Latest_Notebooks', shell=True)
		call('mkdir Latest_Notebooks', shell=True)
	os.chdir('/workspace/Latest_Notebooks')
	call('wget -q -i https://huggingface.co/datasets/TheLastBen/RNPD/raw/main/Notebooks.txt', shell=True)
	call('rm Notebooks.txt', shell=True)
	os.chdir('/workspace')


def repo(Huggingface_token_optional):

	from slugify import slugify
	from huggingface_hub import HfApi, CommitOperationAdd, create_repo

	os.chdir('/workspace')
	if Huggingface_token_optional != "":
		username = HfApi().whoami(Huggingface_token_optional)["name"]
		backup = f"https://huggingface.co/datasets/{username}/fast-stable-diffusion/resolve/main/sd_backup_rnpd.tar.zst"
		headers = {"Authorization": f"Bearer {Huggingface_token_optional}"}
		response = requests.head(backup, headers=headers)
		if response.status_code == 302:
			print('[1;33mRestoring the SD folder...')
			open('/workspace/sd_backup_rnpd.tar.zst',
				'wb').write(requests.get(backup, headers=headers).content)
			call('tar --zstd -xf sd_backup_rnpd.tar.zst', shell=True)
			call('rm sd_backup_rnpd.tar.zst', shell=True)
		else:
			print('[1;33mBackup not found, using a fresh/existing repo...')
			time.sleep(2)
			if not os.path.exists('/workspace/sd/stablediffusiond'):	# reset later
				call('wget -q -O sd_mrep.tar.zst https://huggingface.co/TheLastBen/dependencies/resolve/main/sd_mrep.tar.zst', shell=True)
				call('tar --zstd -xf sd_mrep.tar.zst', shell=True)
				call('rm sd_mrep.tar.zst', shell=True)
			os.chdir('/workspace/sd')
			if not os.path.exists('stable-diffusion-webui'):
				call('git clone -q --depth 1 --branch master https://github.com/AUTOMATIC1111/stable-diffusion-webui', shell=True)

	else:
		print('[1;33mInstalling/Updating the repo...')
		os.chdir('/workspace')
		if not os.path.exists('/workspace/sd/stablediffusiond'):	# reset later
			call('wget -q -O sd_mrep.tar.zst https://huggingface.co/TheLastBen/dependencies/resolve/main/sd_mrep.tar.zst', shell=True)
			call('tar --zstd -xf sd_mrep.tar.zst', shell=True)
			call('rm sd_mrep.tar.zst', shell=True)

		os.chdir('/workspace/sd')
		if not os.path.exists('stable-diffusion-webui'):
			call('git clone -q --depth 1 --branch master https://github.com/AUTOMATIC1111/stable-diffusion-webui', shell=True)

	os.chdir('/workspace/sd/stable-diffusion-webui/')
	call('git reset --hard', shell=True)
	print('[1;32m')
	call('git pull', shell=True)
	os.chdir('/workspace')
	clear_output()
	done()


def mdl(Original_Model_Version, Path_to_MODEL, MODEL_LINK):

	import gdown

	src = getsrc(MODEL_LINK)

	if not os.path.exists('/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/SDv1-5.ckpt'):
		call('ln -s /workspace/auto-models/* /workspace/sd/stable-diffusion-webui/models/Stable-diffusion', shell=True)

	if Path_to_MODEL != '':
		if os.path.exists(str(Path_to_MODEL)):
			print('[1;32mUsing the custom model')
			model = Path_to_MODEL
		else:
			print('[1;31mWrong path, check that the path to the model is correct')

	elif MODEL_LINK != "":

		if src == 'civitai':
			modelname = get_name(MODEL_LINK, False)
			model = f'/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/{modelname}'
			if not os.path.exists(model):
				dwn(MODEL_LINK, model, 'Downloading the custom model')
				clear_output()
			else:
				print('[1;33mModel already exists')
		elif src == 'gdrive':
			modelname = get_name(MODEL_LINK, True)
			model = f'/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/{modelname}'
			if not os.path.exists(model):
				gdown.download(url=MODEL_LINK, output=model,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')
		else:
			modelname = os.path.basename(MODEL_LINK)
			model = f'/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/{modelname}'
			if not os.path.exists(model):
				gdown.download(url=MODEL_LINK, output=model,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')

		if os.path.exists(model) and os.path.getsize(model) > 1810671599:
			print('[1;32mModel downloaded, using the custom model.')
		else:
			call('rm '+model, shell=True, stdout=open('/dev/null', 'w'),
				stderr=open('/dev/null', 'w'))
			print('[1;31mWrong link, check that the link is valid')

	else:
		if Original_Model_Version == "v1.5":
			model = "/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/SDv1-5.ckpt"
			print('[1;32mUsing the original V1.5 model')
		elif Original_Model_Version == "v2-512":
			model = '/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/SDv2-512.ckpt'
			if not os.path.exists('/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/SDv2-512.ckpt'):
				print('[1;33mDownloading the V2-512 model...')
				call('gdown -O '+model+' https://huggingface.co/stabilityai/stable-diffusion-2-1-base/resolve/main/v2-1_512-nonema-pruned.ckpt', shell=True)
				clear_output()
			print('[1;32mUsing the original V2-512 model')
		elif Original_Model_Version == "v2-768":
			model = "/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/SDv2-768.ckpt"
			print('[1;32mUsing the original V2-768 model')
		elif Original_Model_Version == "SDXL":
			model = "/workspace/sd/stable-diffusion-webui/models/Stable-diffusion/sd_xl_base_1.0.safetensors"
			print('[1;32mUsing the original SDXL model')

		else:
			model = "/workspace/sd/stable-diffusion-webui/models/Stable-diffusion"
			print('[1;31mWrong model version, try again')
	try:
		model
	except:
		model = "/workspace/sd/stable-diffusion-webui/models/Stable-diffusion"

	return model


def CNet(ControlNet_Model, ControlNet_XL_Model, CN_LINK):

	def download(url, model_dir):

		filename = os.path.basename(urlparse(url).path)
		pth = os.path.abspath(os.path.join(model_dir, filename))
		if not os.path.exists(pth):
			print('Downloading: '+os.path.basename(url))
			download_url_to_file(url, pth, hash_prefix=None, progress=True)
		else:
			print(f"[1;32mThe model {filename} already exists[0m")

	wrngv1 = False
	os.chdir('/workspace/sd/stable-diffusion-webui/extensions')
	if not os.path.exists("sd-webui-controlnet"):
		call('git clone https://github.com/Mikubill/sd-webui-controlnet.git', shell=True)
		os.chdir('/workspace')
	else:
		os.chdir('sd-webui-controlnet')
		call('git reset --hard', shell=True,
			stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))
		call('git pull', shell=True, stdout=open(
			'/dev/null', 'w'), stderr=open('/dev/null', 'w'))
		os.chdir('/workspace')

	mdldir = "/workspace/sd/stable-diffusion-webui/extensions/sd-webui-controlnet/models"
	for filename in os.listdir(mdldir):
		if "_sd14v1" in filename:
			renamed = re.sub("_sd14v1", "-fp16", filename)
			os.rename(os.path.join(mdldir, filename),
					os.path.join(mdldir, renamed))

	call('wget -q -O CN_models.txt https://github.com/TheLastBen/fast-stable-diffusion/raw/main/AUTOMATIC1111_files/CN_models.txt', shell=True)
	call('wget -q -O CN_models_XL.txt https://github.com/TheLastBen/fast-stable-diffusion/raw/main/AUTOMATIC1111_files/CN_models_XL.txt', shell=True)

	with open("CN_models.txt", 'r') as f:
		mdllnk = f.read().splitlines()

	with open("CN_models_XL.txt", 'r') as d:
		mdllnk_XL = d.read().splitlines()
		
	call('rm CN_models.txt CN_models_XL.txt', shell=True)

	os.chdir('/workspace')

	if ControlNet_Model == "All" or ControlNet_Model == "all":
		for lnk in mdllnk:
			download(lnk, mdldir)
		clear_output()

	elif ControlNet_Model == "15":
		mdllnk = list(filter(lambda x: 't2i' in x, mdllnk))
		for lnk in mdllnk:
			download(lnk, mdldir)
		clear_output()

	elif ControlNet_Model.isdigit() and int(ControlNet_Model)-1 < 14 and int(ControlNet_Model) > 0:
		download(mdllnk[int(ControlNet_Model)-1], mdldir)
		clear_output()

	elif ControlNet_Model == "none":
		pass
		clear_output()

	else:
		print('[1;31mWrong ControlNet V1 choice, try again')
		wrngv1 = True

	if ControlNet_XL_Model == "All" or ControlNet_XL_Model == "all":
		for lnk_XL in mdllnk_XL:
			download(lnk_XL, mdldir)
		if not wrngv1:
			clear_output()
		done()

	elif ControlNet_XL_Model.isdigit() and int(ControlNet_XL_Model)-1 < 5:
		download(mdllnk_XL[int(ControlNet_XL_Model)-1], mdldir)
		if not wrngv1:
			clear_output()
		done()

	elif ControlNet_XL_Model == "none":
		pass
		if not wrngv1:
			clear_output()
		done()

	else:
		print('[1;31mWrong ControlNet XL choice, try again')
##################################
	if CN_LINK != "":
		src = getsrc(CN_LINK)
		if src == 'civitai':
			modelname = get_name(CN_LINK, False)
			model = f'/workspace/sd/stable-diffusion-webui/extensions/sd-webui-controlnet/models/{modelname}'
			if not os.path.exists(model):
				dwn(CN_LINK, model, 'Downloading the custom control-net model')
				clear_output()
			else:
				print('[1;33mModel already exists')

		elif src == 'gdrive':
			modelname = get_name(CN_LINK, True)
			model = f'/workspace/sd/stable-diffusion-webui/extensions/sd-webui-controlnet/models/{modelname}'
			if not os.path.exists(model):
				gdown.download(url=CN_LINK, output=model,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')
		else:
			modelname = os.path.basename(CN_LINK)
			model = f'/workspace/sd/stable-diffusion-webui/extensions/sd-webui-controlnet/models/{modelname}'
			if not os.path.exists(model):
				gdown.download(url=CN_LINK, output=model,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')

		if os.path.exists(model):
			print('[1;32mModel downloaded.')
		else:
			call('rm '+model, shell=True, stdout=open('/dev/null', 'w'),
				stderr=open('/dev/null', 'w'))
			print('[1;31mWrong link, check that the link is valid')


def loradwn(LoRA_LINK):

	import gdown

	if LoRA_LINK == '':
		print('[1;33mNothing to do')
	else:
		os.makedirs(
			'/workspace/sd/stable-diffusion-webui/models/Lora', exist_ok=True)

		src = getsrc(LoRA_LINK)

		if src == 'civitai':
			modelname = get_name(LoRA_LINK, False)
			loramodel = f'/workspace/sd/stable-diffusion-webui/models/Lora/{modelname}'
			if not os.path.exists(loramodel):
				dwn(LoRA_LINK, loramodel, 'Downloading the LoRA model')
				clear_output()
			else:
				print('[1;33mModel already exists')
		elif src == 'gdrive':
			modelname = get_name(LoRA_LINK, True)
			loramodel = f'/workspace/sd/stable-diffusion-webui/models/Lora/{modelname}'
			if not os.path.exists(loramodel):
				gdown.download(url=LoRA_LINK, output=loramodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')
		else:
			modelname = os.path.basename(LoRA_LINK)
			loramodel = f'/workspace/sd/stable-diffusion-webui/models/Lora/{modelname}'
			if not os.path.exists(loramodel):
				gdown.download(url=LoRA_LINK, output=loramodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')

		if os.path.exists(loramodel):
			print('[1;32mLoRA downloaded')
		else:
			print('[1;31mWrong link, check that the link is valid')


def tidwn(TI_LINK):

	import gdown

	if TI_LINK == '':
		print('[1;33mNothing to do')
	else:
		os.makedirs(
			'/workspace/sd/stable-diffusion-webui/models/embeddings', exist_ok=True)

		src = getsrc(TI_LINK)

		if src == 'civitai':
			modelname = get_name(TI_LINK, False)
			timodel = f'/workspace/sd/stable-diffusion-webui/models/embeddings/{modelname}'
			if not os.path.exists(timodel):
				dwn(TI_LINK, timodel, 'Downloading the TI model')
				clear_output()
			else:
				print('[1;33mModel already exists')
		elif src == 'gdrive':
			modelname = get_name(TI_LINK, True)
			timodel = f'/workspace/sd/stable-diffusion-webui/models/embeddings/{modelname}'
			if not os.path.exists(timodel):
				gdown.download(url=TI_LINK, output=timodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')
		else:
			modelname = os.path.basename(TI_LINK)
			timodel = f'/workspace/sd/stable-diffusion-webui/models/embeddings/{modelname}'
			if not os.path.exists(timodel):
				gdown.download(url=TI_LINK, output=timodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')

		if os.path.exists(timodel):
			print('[1;32mTI downloaded')
		else:
			print('[1;31mWrong link, check that the link is valid')


def hyperdwn(HYPER_LINK):

	import gdown

	if HYPER_LINK == '':
		print('[1;33mNothing to do')
	else:
		os.makedirs(
			'/workspace/sd/stable-diffusion-webui/models/hypernetworks', exist_ok=True)

		src = getsrc(HYPER_LINK)

		if src == 'civitai':
			modelname = get_name(HYPER_LINK, False)
			hypermodel = f'/workspace/sd/stable-diffusion-webui/models/hypernetworks/{modelname}'
			if not os.path.exists(hypermodel):
				dwn(HYPER_LINK, hypermodel, 'Downloading the hyper model')
				clear_output()
			else:
				print('[1;33mModel already exists')
		elif src == 'gdrive':
			modelname = get_name(HYPER_LINK, True)
			hypermodel = f'/workspace/sd/stable-diffusion-webui/models/hypernetworks/{modelname}'
			if not os.path.exists(hypermodel):
				gdown.download(url=HYPER_LINK, output=hypermodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')
		else:
			modelname = os.path.basename(HYPER_LINK)
			hypermodel = f'/workspace/sd/stable-diffusion-webui/models/hypernetworks/{modelname}'
			if not os.path.exists(hypermodel):
				gdown.download(url=HYPER_LINK, output=hypermodel,
								quiet=False, fuzzy=True)
				clear_output()
			else:
				print('[1;33mModel already exists')

		if os.path.exists(hypermodel):
			print('[1;32mhyper downloaded')
		else:
			print('[1;31mWrong link, check that the link is valid')


def sd(User, Password, model):

	import gradio

	gradio.close_all()

	auth = f"--gradio-auth {User}:{Password}"
	if User == "" or Password == "":
		auth = ""

	call('wget -q -O /usr/local/lib/python3.10/dist-packages/gradio/blocks.py https://raw.githubusercontent.com/TheLastBen/fast-stable-diffusion/main/AUTOMATIC1111_files/blocks.py', shell=True)

	os.chdir('/workspace/sd/stable-diffusion-webui/modules')

	call(
		"sed -i 's@possible_sd_paths =.*@possible_sd_paths = [\"/workspace/sd/stablediffusion\"]@' /workspace/sd/stable-diffusion-webui/modules/paths.py", shell=True)
	call("sed -i 's@\.\.\/@src/@g' /workspace/sd/stable-diffusion-webui/modules/paths.py", shell=True)
	call("sed -i 's@src\/generative-models@generative-models@g' /workspace/sd/stable-diffusion-webui/modules/paths.py", shell=True)

	call("sed -i 's@\[\"sd_model_checkpoint\"\]@\[\"sd_model_checkpoint\", \"sd_vae\", \"CLIP_stop_at_last_layers\", \"inpainting_mask_weight\", \"initial_noise_multiplier\"\]@g' /workspace/sd/stable-diffusion-webui/modules/shared.py", shell=True)

	call("sed -i 's@print(\"No module.*@@' /workspace/sd/stablediffusion/ldm/modules/diffusionmodules/model.py", shell=True)
	os.chdir('/workspace/sd/stable-diffusion-webui')
	clear_output()

	podid = os.environ.get('RUNPOD_POD_ID')
	localurl = f"{podid}-3001.proxy.runpod.net"

	for line in fileinput.input('/usr/local/lib/python3.10/dist-packages/gradio/blocks.py', inplace=True):
		if line.strip().startswith('self.server_name ='):
			line = f'						self.server_name = "{localurl}"\n'
		if line.strip().startswith('self.protocol = "https"'):
			line = '						self.protocol = "https"\n'
		if line.strip().startswith('if self.local_url.startswith("https") or self.is_colab'):
			line = ''
		if line.strip().startswith('else "http"'):
			line = ''
		sys.stdout.write(line)

	if model == "":
		mdlpth = ""
	else:
		if os.path.isfile(model):
			mdlpth = "--ckpt "+model
		else:
			mdlpth = "--ckpt-dir "+model

	configf = "--disable-console-progressbars --no-half-vae --disable-safe-unpickle --api --no-download-sd-model --opt-sdp-attention --enable-insecure-extension-access	--skip-version-check --listen --port 3000 "+auth+" "+mdlpth

	return configf


def save(Huggingface_Write_token):

	from slugify import slugify
	from huggingface_hub import HfApi, CommitOperationAdd, create_repo

	if Huggingface_Write_token == "":
		print('[1;31mA huggingface write token is required')

	else:
		os.chdir('/workspace')

		if os.path.exists('sd'):

			call('tar --exclude="stable-diffusion-webui/models/*/*" --exclude="sd-webui-controlnet/models/*" --zstd -cf sd_backup_rnpd.tar.zst sd', shell=True)
			api = HfApi()
			username = api.whoami(token=Huggingface_Write_token)["name"]

			repo_id = f"{username}/{slugify('fast-stable-diffusion')}"

			print("[1;32mBacking up...")

			operations = [CommitOperationAdd(
				path_in_repo="sd_backup_rnpd.tar.zst", path_or_fileobj="/workspace/sd_backup_rnpd.tar.zst")]

			create_repo(repo_id, private=True, token=Huggingface_Write_token,
						exist_ok=True, repo_type="dataset")

			api.create_commit(
				repo_id=repo_id,
				repo_type="dataset",
				operations=operations,
				commit_message="SD folder Backup",
				token=Huggingface_Write_token
			)

			call('rm sd_backup_rnpd.tar.zst', shell=True)
			clear_output()

			done()

		else:
			print('[1;33mNothing to backup')


def getsrc(url):

	parsed_url = urlparse(url)

	if parsed_url.netloc == 'civitai.com':
		src = 'civitai'
	elif parsed_url.netloc == 'drive.google.com':
		src = 'gdrive'
	elif parsed_url.netloc == 'huggingface.co':
		src = 'huggingface'
	else:
		src = 'others'
	return src


def get_name(url, gdrive):

	from gdown.download import get_url_from_gdrive_confirmation

	if not gdrive:
		response = requests.get(url, allow_redirects=False)
		if "Location" in response.headers:
			redirected_url = response.headers["Location"]
			quer = parse_qs(urlparse(redirected_url).query)
			if "response-content-disposition" in quer:
				disp_val = quer["response-content-disposition"][0].split(";")
				for vals in disp_val:
					if vals.strip().startswith("filename="):
						filenm = unquote(vals.split("=", 1)[1].strip())
						return filenm.replace("\"", "")
	else:
		headers = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"}
		lnk = "https://drive.google.com/uc?id={id}&export=download".format(
			id=url[url.find("/d/")+3:url.find("/view")])
		res = requests.session().get(lnk, headers=headers, stream=True, verify=True)
		res = requests.session().get(get_url_from_gdrive_confirmation(
			res.text), headers=headers, stream=True, verify=True)
		content_disposition = six.moves.urllib_parse.unquote(
			res.headers["Content-Disposition"])
		filenm = re.search(r"filename\*=UTF-8''(.*)",
							content_disposition).groups()[0].replace(os.path.sep, "_")
		return filenm


def done():
	done = widgets.Button(
		description='Done!',
		disabled=True,
		button_style='success',
		tooltip='',
		icon='check'
	)
	display(done)
