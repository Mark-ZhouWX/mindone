# coding=utf-8
# Copyright 2025 HuggingFace Inc.
#
# This code is adapted from https://github.com/huggingface/diffusers
# with modifications to run diffusers on mindspore.
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

import random
import sys
import unittest

import numpy as np
import pytest
import torch
from ddt import data, ddt, unpack

import mindspore as ms

from mindone.diffusers import KolorsImg2ImgPipeline
from mindone.diffusers.utils.testing_utils import (
    fast,
    load_downloaded_image_from_hf_hub,
    load_numpy_from_local_file,
    slow,
)

from ..pipeline_test_utils import (
    THRESHOLD_FP16,
    THRESHOLD_FP32,
    THRESHOLD_PIXEL,
    PipelineTesterMixin,
    floats_tensor,
    get_module,
    get_pipeline_components,
    randn_tensor,
)

test_cases = [
    {"mode": ms.PYNATIVE_MODE, "dtype": "float32"},
    {"mode": ms.PYNATIVE_MODE, "dtype": "float16"},
    {"mode": ms.GRAPH_MODE, "dtype": "float32"},
    {"mode": ms.GRAPH_MODE, "dtype": "float16"},
]


@fast
@ddt
class KolorsPipelineImg2ImgFastTests(PipelineTesterMixin, unittest.TestCase):
    pipeline_config = [
        [
            "unet",
            "diffusers.models.unets.unet_2d_condition.UNet2DConditionModel",
            "mindone.diffusers.models.unets.unet_2d_condition.UNet2DConditionModel",
            dict(
                block_out_channels=(2, 4),
                layers_per_block=2,
                time_cond_proj_dim=None,
                sample_size=32,
                in_channels=4,
                out_channels=4,
                down_block_types=("DownBlock2D", "CrossAttnDownBlock2D"),
                up_block_types=("CrossAttnUpBlock2D", "UpBlock2D"),
                # specific config below
                attention_head_dim=(2, 4),
                use_linear_projection=True,
                addition_embed_type="text_time",
                addition_time_embed_dim=8,
                transformer_layers_per_block=(1, 2),
                projection_class_embeddings_input_dim=56,
                cross_attention_dim=8,
                norm_num_groups=1,
            ),
        ],
        [
            "scheduler",
            "diffusers.schedulers.scheduling_euler_discrete.EulerDiscreteScheduler",
            "mindone.diffusers.schedulers.scheduling_euler_discrete.EulerDiscreteScheduler",
            dict(
                beta_start=0.00085,
                beta_end=0.012,
                steps_offset=1,
                beta_schedule="scaled_linear",
                timestep_spacing="leading",
            ),
        ],
        [
            "vae",
            "diffusers.models.autoencoders.autoencoder_kl.AutoencoderKL",
            "mindone.diffusers.models.autoencoders.autoencoder_kl.AutoencoderKL",
            dict(
                block_out_channels=[32, 64],
                in_channels=3,
                out_channels=3,
                down_block_types=["DownEncoderBlock2D", "DownEncoderBlock2D"],
                up_block_types=["UpDecoderBlock2D", "UpDecoderBlock2D"],
                latent_channels=4,
                sample_size=128,
            ),
        ],
        [
            "text_encoder",
            "diffusers.pipelines.kolors.text_encoder.ChatGLMModel",
            "mindone.diffusers.pipelines.kolors.text_encoder.ChatGLMModel",
            dict(
                pretrained_model_name_or_path="hf-internal-testing/tiny-random-chatglm3-6b",
            ),
        ],
        [
            "tokenizer",
            "diffusers.pipelines.kolors.tokenizer.ChatGLMTokenizer",
            "mindone.diffusers.pipelines.kolors.tokenizer.ChatGLMTokenizer",
            dict(
                pretrained_model_name_or_path="hf-internal-testing/tiny-random-chatglm3-6b",
            ),
        ],
    ]

    # Copied from tests.pipelines.kolors.test_kolors.KolorsPipelineFastTests.get_dummy_components
    def get_dummy_components(self):
        components = {
            key: None
            for key in [
                "unet",
                "scheduler",
                "vae",
                "text_encoder",
                "tokenizer",
                "image_encoder",
                "feature_extractor",
            ]
        }

        return get_pipeline_components(components, self.pipeline_config)

    def get_dummy_inputs(self, seed=0):
        image = floats_tensor((1, 3, 64, 64), rng=random.Random(seed))
        image = image / 2 + 0.5
        pt_image = image
        ms_image = ms.tensor(pt_image.numpy())

        generator = torch.manual_seed(seed)

        pt_inputs = {
            "prompt": "A painting of a squirrel eating a burger",
            "image": pt_image,
            "generator": generator,
            "num_inference_steps": 2,
            "guidance_scale": 5.0,
            "output_type": "np",
            "strength": 0.8,
        }

        ms_inputs = {
            "prompt": "A painting of a squirrel eating a burger",
            "image": ms_image,
            "generator": generator,
            "num_inference_steps": 2,
            "guidance_scale": 5.0,
            "output_type": "np",
            "strength": 0.8,
        }

        return pt_inputs, ms_inputs

    @data(*test_cases)
    @unpack
    def test_inference(self, mode, dtype):
        ms.set_context(mode=mode)

        pt_components, ms_components = self.get_dummy_components()
        pt_pipe_cls = get_module("diffusers.pipelines.kolors.pipeline_kolors_img2img.KolorsImg2ImgPipeline")
        ms_pipe_cls = get_module("mindone.diffusers.pipelines.kolors.pipeline_kolors_img2img.KolorsImg2ImgPipeline")

        pt_pipe = pt_pipe_cls(**pt_components)
        ms_pipe = ms_pipe_cls(**ms_components)

        pt_pipe.set_progress_bar_config(disable=None)
        ms_pipe.set_progress_bar_config(disable=None)

        ms_dtype, pt_dtype = getattr(ms, dtype), getattr(torch, dtype)
        pt_pipe = pt_pipe.to(pt_dtype)
        ms_pipe = ms_pipe.to(ms_dtype)

        pt_inputs, ms_inputs = self.get_dummy_inputs()

        torch.manual_seed(0)
        pt_image = pt_pipe(**pt_inputs).images
        torch.manual_seed(0)
        ms_image = ms_pipe(**ms_inputs)[0]

        pt_image_slice = pt_image[0, -3:, -3:, -1]
        ms_image_slice = ms_image[0, -3:, -3:, -1]

        threshold = THRESHOLD_FP32 if dtype == "float32" else THRESHOLD_FP16
        assert np.linalg.norm(pt_image_slice - ms_image_slice) / np.linalg.norm(pt_image_slice) < threshold


@slow
@ddt
class KolorsPipelineImg2ImgIntegrationTests(unittest.TestCase):
    @data(*test_cases)
    @unpack
    def test_inference(self, mode, dtype):
        if dtype == "float32":
            pytest.skip("diffusers doesn't support fp32")

        # TODO: synchronize issue, and we need to put the replacement of randn_tensor after initialization.
        if mode == ms.PYNATIVE_MODE:
            ms.set_context(mode=mode, pynative_synchronize=True)
        else:
            ms.set_context(mode=mode)
        ms_dtype = getattr(ms, dtype)

        pipe = KolorsImg2ImgPipeline.from_pretrained(
            "Kwai-Kolors/Kolors-diffusers", variant="fp16", mindspore_dtype=ms_dtype
        )

        sys.modules[pipe.__module__].randn_tensor = randn_tensor
        sys.modules[pipe.vae.diag_gauss_dist.__module__].randn_tensor = randn_tensor

        init_image = load_downloaded_image_from_hf_hub(
            "huggingface/documentation-images",
            "bunny_source.png",
            subfolder="kolors",
        )
        prompt = (
            "high quality image of a capybara wearing sunglasses. In the background of the image there are trees,"
            " poles, grass and other objects. At the bottom of the object there is the road., 8k, highly detailed"
            "."
        )

        torch.manual_seed(0)
        image = pipe(prompt, image=init_image)[0][0]

        expected_image = load_numpy_from_local_file(
            "mindone-testing-arrays",
            f"kolors_i2i_{dtype}.npy",
            subfolder="kolors",
        )
        assert np.mean(np.abs(np.array(image, dtype=np.float32) - expected_image)) < THRESHOLD_PIXEL
