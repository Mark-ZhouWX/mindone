# coding=utf-8
# Copyright 2024 NUS Show Lab.
#
# This code is adapted from https://github.com/Gen-Verse/MMaDA
# with the modifications to run MMaDA on mindspore.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any, Callable, Optional

from training.image_folder_dataset import DatasetFolder, default_loader
from training.utils import image_transform


class ImageNetDataset(DatasetFolder):
    def __init__(
        self,
        root: str,
        loader: Callable[[str], Any] = default_loader,
        is_valid_file: Optional[Callable[[str], bool]] = None,
        image_size=256,
    ):
        IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".pgm", ".tif", ".tiff", ".webp")

        self.transform = image_transform
        self.image_size = image_size

        super().__init__(
            root,
            loader,
            IMG_EXTENSIONS if is_valid_file is None else None,
            transform=self.transform,
            target_transform=None,
            is_valid_file=is_valid_file,
        )

        with open("./training/imagenet_label_mapping", "r") as f:
            self.labels = {}
            for line in f:
                num, description = line.split(":")
                self.labels[int(num)] = description.strip()

        print("ImageNet dataset loaded.")

    def __getitem__(self, idx):
        try:
            path, target = self.samples[idx]
            image = self.loader(path)
            image = self.transform(image, resolution=self.image_size)
            input_ids = "{}".format(self.labels[target])
            class_ids = target

            # return {"images": image, "input_ids": input_ids, "class_ids": class_ids}
            return image, input_ids, class_ids

        except Exception as e:
            print(e)
            return self.__getitem__(idx + 1)


if __name__ == "__main__":
    pass
