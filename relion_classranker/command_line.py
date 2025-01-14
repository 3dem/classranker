import sys

if sys.version_info < (3, 0):
    # This script requires Python 3. A Syntax error here means you are running it in Python 2.
    print('This script supports Python 3 or above.')
    exit(1)

import os
import argparse
import sys
import types

try:
    import torch
except ImportError:
    print("PYTHON ERROR: The required python module 'torch' was not found.")
    exit(1)

try:
    import numpy as np
except ImportError:
    print("PYTHON ERROR: The required python module 'numpy' was not found.")
    exit(1)


def install_and_load_model(
        name: str,
        device: str = "cpu",
        verbose: bool = False
):
    model_list = {
        "v1.0": [
            "https://zenodo.org/records/14618982/files/classranker_v1.0.ckpt.gz",
            "68a9855c16d7bab64b7e73e1e1442c7bf898f227ffd9a19c48ddfd2cf0646d73"
        ]
    }

    if name not in model_list.keys():
        return None

    dest_dir = os.path.join(torch.hub.get_dir(), "checkpoints", "relion_class_ranker")
    model_path = os.path.join(dest_dir, f"{name}.ckpt")
    model_path_gz = model_path + ".gz"
    completed_check_path = os.path.join(dest_dir, f"{name}_installed.txt")

    # Download file and install it if not already done
    if not os.path.isfile(completed_check_path):
        if verbose:
            print(f"Installing Classranker model ({name})...")
        os.makedirs(dest_dir, exist_ok=True)

        import gzip, shutil
        torch.hub.download_url_to_file(model_list[name][0], model_path_gz, hash_prefix=model_list[name][1])
        with gzip.open(model_path_gz, 'rb') as f_in:
            with open(model_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(model_path_gz)

        with open(completed_check_path, "w") as f:
            f.write("Successfully downloaded model")

        if verbose:
            print(f"Model ({name}) successfully installed in {dest_dir}")

    # Load checkpoint file
    checkpoint = torch.load(model_path, map_location="cpu")

    # Dynamically include model as a module
    # Make sure to check download integrity for this, otherwise major security risk
    model_module = types.ModuleType("classranker_model")
    exec(checkpoint['model_definition'], model_module.__dict__)
    sys.modules["classranker_model"] = model_module

    # Load the model
    model = model_module.Model().eval()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)

    if verbose:
        print(f"Model ({name}) loaded successfully from checkpoint {model_path}")

    return model, model_path


def apply_model(model, features, images):
    features_tensor = torch.from_numpy(features)
    images_tensor = torch.from_numpy(images).unsqueeze(1)
    scores = model(images_tensor, features_tensor).detach().cpu().numpy()
    return scores


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('project_dir', nargs='?', default=None)
    parser.add_argument('-m', '--model_name', type=str, default="v1.0")
    args = parser.parse_args()

    torch.no_grad()

    model, model_path = install_and_load_model(
        name=args.model_name,
        device="cpu",
        verbose=args.project_dir is None
    )

    if model is None:
        print("Model name not found!")
        exit(1)

    if args.project_dir is None:
        print("No project directory was specified... exiting!")
        exit(0)

    feature_fn = os.path.join(args.project_dir, "features.npy")
    images_fn = os.path.join(args.project_dir, "images.npy")

    scores = apply_model(
        model=model,
        features=np.load(feature_fn),
        images=np.load(images_fn)
    )

    for i in range(scores.shape[0]):
        print(scores[i, 0], end=" ")


if __name__ == "__main__":
    main()
