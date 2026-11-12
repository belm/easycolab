"""MiniMax-H3-Image 接入的轻量契约测试（无需 GPU / 不需要 import app.py）。

运行: python -m unittest discover -s tests -v
"""

import ast
import io
import json
import os
import typing
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(ROOT, "app.py")
NOTEBOOK = os.path.join(ROOT, "EasyColab_Server.ipynb")

MODEL_ID = "minimax_h3_image"
REPO_ID = "MiniMaxAI/MiniMax-H3-Image"

CLIENT_CATALOGS = (
    "macos_app/Sources/ModelsAndCatalogs.swift",
    "ios_app/Sources/LocalizationAndModels.swift",
    "windows_app/models.py",
    "android_app/app/src/main/java/app/easycolab/studio/LocalizationAndModels.kt",
)


def _load_helpers(*names):
    """从 app.py 中按 AST 抽取纯函数，在隔离命名空间执行（避开 torch / gradio 等重依赖）"""
    with io.open(APP_PY, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=APP_PY)
    picked = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in names
    ]
    assert len(picked) == len(names), "helper functions missing from app.py"
    ns = {
        "Tuple": typing.Tuple,
        "Optional": typing.Optional,
        "Dict": typing.Dict,
        "List": typing.List,
        "os": os,
        "json": json,
        "shutil": __import__("shutil"),
    }
    mod = ast.Module(body=picked, type_ignores=[])
    exec(compile(mod, APP_PY, "exec"), ns)  # noqa: S102 - trusted local source
    return ns


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class MiniMaxH3ImageCatalogTest(unittest.TestCase):
    def test_server_catalog_entry(self):
        src = _read("app.py")
        self.assertIn('"%s": {' % MODEL_ID, src)
        self.assertIn('"repo_id": "%s"' % REPO_ID, src)
        self.assertIn('"pipeline_arch": "minimax_h3_image"', src)
        self.assertIn('"modality": "image"', src)
        # 12 DiT 分片 + 14 文本编码器分片 + VAE + PDD 融合头
        self.assertIn("of-00012.safetensors", src)
        self.assertIn("of-00014.safetensors", src)
        self.assertIn("pdd_fused_heads.safetensors", src)
        # 官方 Modular Diffusers 集成使用 transformer_diffusers/ 与 vae_diffusers/
        self.assertIn("transformer_diffusers/", src)
        self.assertIn("vae_diffusers/", src)

    def test_all_client_catalogs_register_the_model(self):
        for rel in CLIENT_CATALOGS:
            with self.subTest(client=rel):
                self.assertIn(MODEL_ID, _read(rel))
                self.assertIn(REPO_ID, _read(rel))
                self.assertIn("4096 × 4096", _read(rel))

    def test_notebook_embeds_current_server_code_and_dependency(self):
        with io.open(NOTEBOOK, encoding="utf-8") as f:
            nb = json.load(f)
        cell5 = "".join(nb["cells"][5]["source"])
        self.assertEqual(cell5, _read("app.py"))
        self.assertIn("git+https://github.com/huggingface/diffusers.git", "".join(nb["cells"][3]["source"]))
        self.assertIn(MODEL_ID, cell5)

    def test_bridge_installs_diffusers(self):
        self.assertIn("git+https://github.com/huggingface/diffusers.git", _read("colab_bridge.py"))

    def test_pipeline_branches_exist(self):
        src = _read("app.py")
        # 下载 / 加载 / 推理 / OpenAI 网关四处都必须覆盖新管线
        self.assertGreaterEqual(src.count('pipeline_arch == "minimax_h3_image"'), 4)
        self.assertIn("_call_minimax_h3_image_pipe", src)
        self.assertIn("_localize_minimax_h3_image_index", src)
        self.assertIn("_reuse_minimax_h3_text_encoder", src)
        self.assertIn("ModularPipeline", src)
        self.assertIn("ComponentsManager", src)
        self.assertIn("modular_model_index.json", src)


class MiniMaxH3ImageHelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = _load_helpers(
            "_h3_image_effective_size",
            "_filter_diffusers_call_kwargs",
            "_call_minimax_h3_image_pipe",
        )

    def test_small_request_is_upscaled_to_16mp_canvas(self):
        fn = self.ns["_h3_image_effective_size"]
        self.assertEqual(fn(1024, 1024), (4096, 4096))
        w, h = fn(1344, 768)
        self.assertGreaterEqual(w * h, 4096 * 4096 * 0.95)
        self.assertAlmostEqual(w / h, 1344 / 768, delta=0.02)
        self.assertEqual(w % 32, 0)
        self.assertEqual(h % 32, 0)

    def test_native_4k_request_is_untouched(self):
        fn = self.ns["_h3_image_effective_size"]
        self.assertEqual(fn(4096, 4096), (4096, 4096))
        self.assertEqual(fn(5472, 3072), (5472, 3072))

    def test_call_kwargs_are_filtered_by_signature(self):
        class FakePipe:
            def __call__(self, prompt, height, width, num_inference_steps, guidance_scale, generator, image=None):
                return {"prompt": prompt, "image": image, "height": height, "width": width}

        pipe = FakePipe()
        out = self.ns["_call_minimax_h3_image_pipe"](
            pipe,
            dict(
                prompt="a cat",
                height=4096,
                width=4096,
                num_inference_steps=6,
                guidance_scale=1.0,
                generator=None,
                unsupported_kw=True,
            ),
            edit_images=["ref"],
        )
        self.assertEqual(out["prompt"], "a cat")
        self.assertEqual(out["image"], ["ref"])


if __name__ == "__main__":
    unittest.main()
