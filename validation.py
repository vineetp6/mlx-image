import argparse
import json
import os
import time
from shutil import copy2
from typing import Dict, Union

from tqdm import tqdm

from mlxim.data import DataLoader, LabelFolderDataset
from mlxim.io import load_config
from mlxim.metrics.classification import Accuracy
from mlxim.model import create_model, num_params
from mlxim.transform import ImageNetTransform
from mlxim.utils.time import now
from mlxim.utils.validation import ValidationResults


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validation script")

    parser.add_argument("--config", type=str, default="config/validation.yaml")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    config = load_config(args.config)

    print("Validation setup:")
    print(f"> Model: {config['model']['model_name']}")
    print(f"> Transform: {config['transform']}")

    dataset = LabelFolderDataset(transform=ImageNetTransform(**config["transform"]), **config["dataset"])

    loader = DataLoader(dataset=dataset, **config["loader"])

    model = create_model(num_classes=len(dataset.class_map), **config["model"])
    model.eval()

    accuracy = Accuracy(**config["metric"])
    for _i, batch in tqdm(enumerate(loader), total=len(loader)):
        x, target = batch
        logits = model(x)
        accuracy.update(logits, target)

    acc = accuracy.compute()

    print("Validation result:")
    print("Accuracy:")
    print(accuracy)

    output_dir = os.path.join(config["output"], config["model"]["model_name"], now())

    results = ValidationResults("results/results-imagenet-1k.csv")
    results.update(
        model_name=config["model"]["model_name"],
        acc_1=acc["acc@1"],
        acc_5=acc["acc@5"],
        param_count=num_params(model),
        img_size=config["transform"]["img_size"],
        crop_pct=config["transform"]["crop_pct"],
        interpolation=config["transform"]["interpolation"],
        engine=config["dataset"]["engine"],
    )
    results.save()

    print(f"Saving output files to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # save accuracy dict to file
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(accuracy.as_dict(), f, indent=4)

    # copy config file
    copy2(args.config, output_dir)
