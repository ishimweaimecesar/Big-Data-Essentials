Hugging Face Image Generator Package

Contents:
- generate_5000_huggingface_images.py

Required files (provide your own):
- products.json
- categories.json
- .env

Example .env:
HF_TOKEN=hf_your_huggingface_token_here
HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
HF_PROVIDER=auto

Install:
pip install -U huggingface_hub pillow python-dotenv

Run:
python generate_5000_huggingface_images.py --limit 5000
