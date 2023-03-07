"""Generates gifs of environments.

Copied and adapted from Gymnasium:
https://github.com/Farama-Foundation/Gymnasium/blob/v0.27.0/docs/scripts/gen_gifs.py

"""
__author__ = "Sander Schulhoff"
__email__ = "sanderschulhoff@gmail.com"

import os
import os.path as osp
import re
import argparse
from typing import List

from PIL import Image
from tqdm import tqdm

import posggym
from utils import kill_strs

DOCS_DIR = osp.abspath(osp.join(osp.dirname(osp.abspath(__file__)), os.pardir))

# snake to camel case:
# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
pattern = re.compile(r"(?<!^)(?=[A-Z])")
# how many steps to record an env for
LENGTH = 300
# height of GIF in pixels, width will be scaled to ensure correct aspec ratio
HEIGHT = 256


def gen_gif(env_id: str, ignore_existing: bool = False):
    """Gen gif for env."""
    print(env_id)
    env = posggym.make(env_id, disable_env_checker=True, render_mode="rgb_array")

    # extract env name/type from class path
    split = str(type(env.unwrapped)).split(".")

    # get rid of version info
    env_name = env_id.split("-")[0]
    # convert NameLikeThis to name_like_this
    env_name = pattern.sub("_", env_name).lower()
    # get the env type (e.g. Box2D)
    env_type = split[2]

    # path for saving video
    v_dir_path = os.path.join(DOCS_DIR, "_static", "videos", env_type)
    # create dir if it doesn't exist
    os.makedirs(v_dir_path, exist_ok=True)
    v_file_path = os.path.join(v_dir_path, env_name + ".gif")

    if os.path.exists(v_file_path) and not ignore_existing:
        # don't overwrite existing video
        print(
            f"GIF already exists for {env_name} so skipping (Use `--ignore-existing` "
            "to overwrite existing files."
        )
        return

    # obtain and save LENGTH frames worth of steps
    frames: List[Image] = []
    while True:
        env.reset()
        done = False
        while not done and len(frames) <= LENGTH:
            frame = env.render()  # type: ignore
            repeat = (
                int(60 / env.metadata["render_fps"]) if env_type == "classic" else 1
            )
            for i in range(repeat):
                frames.append(Image.fromarray(frame))
            action = {i: env.action_spaces[i].sample() for i in env.agents}
            _, _, _, _, done, _ = env.step(action)

        if len(frames) > LENGTH:
            break

    env.close()

    for i, img in enumerate(frames):
        # h / w = H / w'
        # w' = Hw/h
        resized_img = img.resize((HEIGHT, int(HEIGHT * img.width / img.height)))
        frames[i] = resized_img

    frames[0].save(
        os.path.join(v_file_path),
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    print(f"Saved: {env_name} to {v_file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--env-id",
        type=str,
        default=None,
        help="ID of environment to run, if None then runs all registered envs.",
    )
    parser.add_argument(
        "--ignore-existing",
        action="store_true",
        help="Overwrite existing GIF if it exists.",
    )
    args = parser.parse_args()

    if args.env_id is None:
        # iterate through all envspecs
        for env_spec in tqdm(posggym.envs.registry.values()):
            if any(x in str(env_spec.id) for x in kill_strs):
                continue
            # try catch in case missing some installs
            try:
                env = posggym.make(env_spec.id, disable_env_checker=True)
                # the gymnasium needs to be rgb renderable
                if "rgb_array" not in env.metadata["render_modes"]:
                    continue
                gen_gif(env_spec.id, args.ignore_existing)
            except BaseException as e:
                print(f"{env_spec.id} ERROR", e)
                continue
    else:
        gen_gif(args.env_id, args.ignore_existing)
