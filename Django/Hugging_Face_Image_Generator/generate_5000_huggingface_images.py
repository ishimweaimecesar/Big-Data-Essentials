"""
Batch product-image generator using Hugging Face InferenceClient.

The script generates up to 5,000 product images, resumes safely when images
already exist, retries temporary failures, records a CSV manifest, and can
package the results into a ZIP archive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import random
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


PHYSICAL_PRODUCT_TYPES = [
    "premium wireless headphones",
    "modern Wi-Fi router",
    "compact Bluetooth speaker",
    "high-end laptop computer",
    "ergonomic office chair",
    "professional mirrorless camera",
    "smartwatch",
    "mechanical gaming keyboard",
    "portable power bank",
    "multifunction printer",
    "rugged protective equipment case",
    "cordless power-tool kit",
    "adjustable fitness bench",
    "travel backpack",
    "desktop monitor",
    "modern smartphone",
    "high-performance graphics card",
    "home security camera",
    "wireless computer mouse",
    "tablet computer",
    "USB-C docking station",
    "network storage device",
    "studio microphone",
    "smart-home hub",
    "portable projector",
    "electric desk lamp",
    "kitchen countertop appliance",
    "modern storage cabinet",
    "outdoor utility device",
    "premium consumer-electronics accessory",
]


def stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_lookups(
    categories: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    category_lookup = {c["category_id"]: c for c in categories}
    subcategory_lookup: dict[str, dict[str, Any]] = {}

    for category in categories:
        for subcategory in category.get("subcategories", []):
            subcategory_lookup[subcategory["subcategory_id"]] = subcategory

    return category_lookup, subcategory_lookup


def infer_product_type(product: dict[str, Any]) -> str:
    """
    Your JSON product/category names are synthetic business phrases rather than
    literal physical products. This creates a stable physical-product mapping.

    All products within a category remain visually related, while product IDs
    add variation.
    """
    category_id = product.get("category_id", "unknown")
    category_base = stable_index(category_id, len(PHYSICAL_PRODUCT_TYPES))
    variation = stable_index(product["product_id"], 7)

    return PHYSICAL_PRODUCT_TYPES[
        (category_base + variation) % len(PHYSICAL_PRODUCT_TYPES)
    ]


def build_prompt(
    product: dict[str, Any],
    category_name: str,
    subcategory_name: str,
) -> str:
    product_type = infer_product_type(product)
    seed = stable_index(product["product_id"], 100_000)

    finishes = [
        "matte black",
        "brushed aluminum",
        "soft white",
        "graphite gray",
        "deep navy",
        "warm beige",
        "forest green",
        "metallic silver",
        "charcoal",
        "midnight blue",
    ]

    accents = [
        "subtle orange accents",
        "minimal blue accents",
        "small gold details",
        "clean silver details",
        "subtle red accents",
        "tonal monochrome details",
    ]

    finish = finishes[seed % len(finishes)]
    accent = accents[(seed // 7) % len(accents)]

    return f"""
Create a photorealistic commercial e-commerce catalog photograph of one
{product_type}.

The image represents this synthetic catalog entry:
Product ID: {product["product_id"]}
Product name: {product["name"]}
Category: {category_name}
Subcategory: {subcategory_name}

Product design:
- {finish} finish
- {accent}
- premium realistic materials
- credible manufacturing details
- believable controls, ports, seams, fasteners and textures
- realistic proportions
- unique design, but physically plausible

Composition:
- exactly one main product
- centered
- three-quarter front view
- fully visible
- no cropped edges
- white seamless studio background
- soft natural floor shadow
- professional softbox lighting
- crisp focus
- realistic reflections
- premium online-store catalog style

Do not include people, hands, text, labels, logos, trademarks, watermark,
price tag, packaging text, user-interface overlays, collages, duplicated
products, floating components or surreal geometry.
""".strip()


def generate_image_bytes(
    client: InferenceClient,
    *,
    model: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    guidance_scale: float,
    num_inference_steps: int,
) -> bytes:
    """Generate one image through Hugging Face and return PNG bytes."""
    image = client.text_to_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model,
        width=width,
        height=height,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def append_csv(
    path: Path,
    fieldnames: list[str],
    row: dict[str, Any],
) -> None:
    exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow(row)


def create_zip(
    image_directory: Path,
    manifest_path: Path,
    zip_path: Path,
) -> None:
    logging.info("Creating ZIP: %s", zip_path)

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for image_path in sorted(image_directory.iterdir()):
            if image_path.is_file() and not image_path.name.endswith(".part"):
                archive.write(
                    image_path,
                    arcname=f"images/{image_path.name}",
                )

        if manifest_path.exists():
            archive.write(manifest_path, arcname="manifest.csv")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate up to 5,000 product images with Hugging Face."
    )

    parser.add_argument("--products", default="products.json")
    parser.add_argument("--categories", default="categories.json")
    parser.add_argument("--output-dir", default="generated_images")
    parser.add_argument("--manifest", default="manifest.csv")
    parser.add_argument("--failures", default="failures.csv")
    parser.add_argument(
        "--zip-path",
        default="ecommerce_product_images_all_5000.zip",
    )

    # Replace this model with the image model supported by your provider.
    parser.add_argument(
        "--model",
        default=os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell"),
    )

    parser.add_argument("--provider", default=os.getenv("HF_PROVIDER", "auto"))
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--guidance-scale", type=float, default=3.5)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--negative-prompt",
        default=(
            "people, hands, text, labels, logos, trademarks, watermark, "
            "price tag, packaging text, UI overlay, collage, duplicate product, "
            "cropped product, blurry, low quality, surreal geometry"
        ),
    )
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-zip", action="store_true")

    return parser.parse_args()


def main() -> None:
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    arguments = parse_arguments()

    api_key = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not api_key:
        raise SystemExit(
            "HF_TOKEN is missing. Put HF_TOKEN=hf_... in your `.env` file."
        )

    products_path = Path(arguments.products)
    categories_path = Path(arguments.categories)
    output_directory = Path(arguments.output_dir)
    manifest_path = Path(arguments.manifest)
    failures_path = Path(arguments.failures)
    zip_path = Path(arguments.zip_path)

    output_directory.mkdir(parents=True, exist_ok=True)

    products: list[dict[str, Any]] = load_json(products_path)
    categories: list[dict[str, Any]] = load_json(categories_path)

    category_lookup, subcategory_lookup = build_lookups(categories)

    selected_products = products[max(0, arguments.start):]

    if arguments.limit is not None:
        selected_products = selected_products[: min(5000, max(0, arguments.limit))]
    else:
        selected_products = selected_products[:5000]

    # Never hard-code credentials in source code.
    client = InferenceClient(
        provider=arguments.provider,
        api_key=api_key,
        timeout=arguments.timeout,
    )

    manifest_fields = [
        "product_id",
        "image_filename",
        "product_name",
        "category_id",
        "category_name",
        "subcategory_id",
        "subcategory_name",
        "base_price",
        "current_stock",
        "prompt",
    ]

    failure_fields = [
        "product_id",
        "error",
    ]

    generated_count = 0
    skipped_count = 0
    failure_count = 0

    logging.info("Selected products: %d", len(selected_products))
    logging.info("Model: %s", arguments.model)
    logging.info("Provider: %s", arguments.provider)

    for position, product in enumerate(selected_products, start=1):
        product_id = product["product_id"]
        filename = f"{product_id}.png"
        destination = output_directory / filename

        if (
            destination.exists()
            and destination.stat().st_size > 0
            and not arguments.overwrite
        ):
            skipped_count += 1
            logging.info(
                "[%d/%d] Skip existing %s",
                position,
                len(selected_products),
                product_id,
            )
            continue

        category_id = product.get("category_id", "")
        subcategory_id = product.get("subcategory_id", "")

        category_name = category_lookup.get(
            category_id,
            {},
        ).get("name", category_id)

        subcategory_name = subcategory_lookup.get(
            subcategory_id,
            {},
        ).get("name", subcategory_id)

        prompt = build_prompt(
            product,
            category_name,
            subcategory_name,
        )

        last_error: Exception | None = None

        for attempt in range(1, max(1, arguments.retries) + 1):
            try:
                logging.info(
                    "[%d/%d] Generate %s — attempt %d",
                    position,
                    len(selected_products),
                    product_id,
                    attempt,
                )

                image_bytes = generate_image_bytes(
                    client,
                    model=arguments.model,
                    prompt=prompt,
                    negative_prompt=arguments.negative_prompt,
                    width=arguments.width,
                    height=arguments.height,
                    guidance_scale=arguments.guidance_scale,
                    num_inference_steps=arguments.steps,
                )

                temporary_path = destination.with_suffix(
                    destination.suffix + ".part"
                )

                temporary_path.write_bytes(image_bytes)
                temporary_path.replace(destination)

                append_csv(
                    manifest_path,
                    manifest_fields,
                    {
                        "product_id": product_id,
                        "image_filename": filename,
                        "product_name": product.get("name", ""),
                        "category_id": category_id,
                        "category_name": category_name,
                        "subcategory_id": subcategory_id,
                        "subcategory_name": subcategory_name,
                        "base_price": product.get("base_price", ""),
                        "current_stock": product.get("current_stock", ""),
                        "prompt": prompt.replace("\n", " "),
                    },
                )

                generated_count += 1
                last_error = None
                break

            except Exception as error:
                last_error = error
                wait_seconds = min(
                    60.0,
                    (2 ** (attempt - 1)) + random.random(),
                )

                logging.warning(
                    "%s failed: %s. Retrying in %.1f seconds.",
                    product_id,
                    error,
                    wait_seconds,
                )

                time.sleep(wait_seconds)

        if last_error is not None:
            failure_count += 1

            append_csv(
                failures_path,
                failure_fields,
                {
                    "product_id": product_id,
                    "error": repr(last_error),
                },
            )

            logging.error(
                "Permanent failure for %s: %s",
                product_id,
                last_error,
            )

        if arguments.delay > 0:
            time.sleep(arguments.delay)

    logging.info(
        "Completed: generated=%d, skipped=%d, failed=%d",
        generated_count,
        skipped_count,
        failure_count,
    )

    if not arguments.no_zip:
        create_zip(
            output_directory,
            manifest_path,
            zip_path,
        )

        logging.info(
            "ZIP created: %s",
            zip_path.resolve(),
        )


if __name__ == "__main__":
    main()
