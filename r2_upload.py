# -*- coding: utf-8 -*-
"""
Cloudflare R2 临时中转上传（S3 兼容协议）。

用途：Colab 生成的视频/图片体积大（10~100MB），经 gradio.live 隧道下载极慢。
配置 R2 后，生成完成即自动上传，本地走 Cloudflare CDN 加速下载。

依赖：boto3（Colab 环境通常自带；缺失时本模块会提示安装）
存储桶需设为公开，配合「公开访问地址」拼出可下载 URL。
生命周期建议 4 小时（由用户在 R2 控制台设置，本模块也可尝试自动配置）。
"""
import os
import time
import threading
import mimetypes
from datetime import datetime, timezone

# 全局状态
R2_STATE = {
    "last_error": None,
    "uploads": 0,
    "last_url": None,
    "last_object": None,
    "last_ts": None,
}

_R2_LOCK = threading.Lock()


def normalize_public_base(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u.rstrip("/")


def is_configured(cfg: dict) -> bool:
    if not isinstance(cfg, dict) or not cfg.get("enabled"):
        return False
    need = ("account_id", "access_key_id", "secret_access_key", "bucket")
    return all(str(cfg.get(k) or "").strip() for k in need)


def _make_client(cfg: dict):
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError as e:
        raise RuntimeError(
            "缺少 boto3，无法上传 R2。请在 Colab 依赖单元执行：!pip install -q boto3"
        ) from e
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg['account_id'].strip()}.r2.cloudflarestorage.com",
        aws_access_key_id=cfg["access_key_id"].strip(),
        aws_secret_access_key=cfg["secret_access_key"].strip(),
        region_name="auto",
        config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _guess_content_type(path: str) -> str:
    ct, _ = mimetypes.guess_type(path)
    return ct or "application/octet-stream"


def object_key_for(filename: str, prefix: str = "") -> str:
    """按日期分目录，避免同名覆盖。"""
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    p = (prefix or "").strip().strip("/")
    base = os.path.basename(filename)
    return f"{p}/{day}/{base}" if p else f"{day}/{base}"


def public_url_for(cfg: dict, key: str) -> str:
    base = normalize_public_base(cfg.get("public_base_url", ""))
    if base:
        return f"{base}/{key}"
    # 未填公开地址时退化为 R2 的 r2.dev 域名（需在控制台开启 Public Development URL）
    bucket = str(cfg.get("bucket") or "").strip()
    return f"https://{bucket}.r2.dev/{key}"


def upload_file(local_path: str, cfg: dict, key: str = None, delete_after: bool = False) -> dict:
    """上传单个文件到 R2，返回 {ok, url, key, size, elapsed, error}。"""
    if not os.path.exists(local_path):
        return {"ok": False, "error": f"文件不存在: {local_path}"}
    if not is_configured(cfg):
        return {"ok": False, "error": "R2 未配置或不完整"}

    key = key or object_key_for(local_path, cfg.get("prefix") or "")
    size = os.path.getsize(local_path)
    t0 = time.time()
    try:
        client = _make_client(cfg)
        extra = {
            "ContentType": _guess_content_type(local_path),
            "CacheControl": "public, max-age=14400",  # 4 小时
        }
        client.upload_file(
            Filename=local_path,
            Bucket=str(cfg["bucket"]).strip(),
            Key=key,
            ExtraArgs=extra,
        )
        url = public_url_for(cfg, key)
        elapsed = round(time.time() - t0, 1)
        with _R2_LOCK:
            R2_STATE.update(
                last_error=None, last_url=url, last_object=key,
                last_ts=datetime.now(timezone.utc).isoformat(), uploads=R2_STATE["uploads"] + 1,
            )
        if delete_after:
            try:
                os.remove(local_path)
            except Exception:
                pass
        return {"ok": True, "url": url, "key": key, "size": size, "elapsed": elapsed}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        with _R2_LOCK:
            R2_STATE["last_error"] = msg
        return {"ok": False, "error": msg, "key": key}


def upload_async(local_path: str, cfg: dict, key: str = None, delete_after: bool = False, on_done=None):
    """后台线程上传，不阻塞生成任务收尾。"""
    def _worker():
        res = upload_file(local_path, cfg, key=key, delete_after=delete_after)
        if on_done:
            try:
                on_done(res)
            except Exception:
                pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def test_connection(cfg: dict) -> dict:
    """测试连接：写一个极小对象并尝试读回公开 URL。"""
    if not is_configured(cfg):
        return {"ok": False, "error": "R2 配置不完整（需 Account ID / Access Key / Secret / 存储桶）"}
    probe_name = f"_easycolab_probe_{int(time.time())}.txt"
    key = object_key_for(probe_name, cfg.get("prefix") or "")
    try:
        client = _make_client(cfg)
        client.put_object(
            Bucket=str(cfg["bucket"]).strip(), Key=key,
            Body=b"easycolab r2 probe", ContentType="text/plain",
        )
        url = public_url_for(cfg, key)
        # 校验公开可读
        import urllib.request
        reachable = None
        try:
            with urllib.request.urlopen(url, timeout=12) as r:
                reachable = r.status
        except Exception as e:
            reachable = f"公开访问失败: {type(e).__name__}"
        # 清理探针
        try:
            client.delete_object(Bucket=str(cfg["bucket"]).strip(), Key=key)
        except Exception:
            pass
        return {
            "ok": True,
            "url": url,
            "public_reachable": reachable == 200,
            "public_status": reachable,
            "hint": None if reachable == 200 else
                    "对象已写入，但公开地址不可访问：请确认存储桶已开启公开访问，且「公开访问地址」填写正确。",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
