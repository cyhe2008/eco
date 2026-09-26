"""神经网络存档：保存 / 列出 / 读取个体大脑基因组及其元数据。

每个存档是一个 JSON 文件，存于工作目录下的 brains/ 文件夹，
可保留多份并随时查看数据。
"""
import json
import os
import time

ARCHIVE_DIR = "brains"


def archive_dir():
    d = os.path.join(os.getcwd(), ARCHIVE_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def save_brain(species, brain, meta):
    """保存一个大脑基因组。meta 需包含 input_size/hidden_size 等。"""
    d = archive_dir()
    ts = time.strftime("%Y%m%d-%H%M%S")
    name = f"{species}_{ts}_{meta.get('id', 0)}.json"
    path = os.path.join(d, name)

    g = list(brain.genome)
    n = len(g)
    mean = sum(g) / n
    var = sum((x - mean) ** 2 for x in g) / n
    stats = {
        "genome_size": n,
        "input_size": meta.get("input_size"),
        "hidden_sizes": meta.get("hidden_sizes") or [meta.get("hidden_size")],
        "min": min(g),
        "max": max(g),
        "mean": mean,
        "std": var ** 0.5,
    }
    data = {
        "species": species,
        "saved_at": ts,
        "genome": g,
        "stats": stats,
        "meta": {k: v for k, v in meta.items() if isinstance(v, (int, float, str, bool, list, dict))},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def list_archives():
    """返回 [(文件名, 数据 dict 或 None)]，按文件名排序（即按时间）。"""
    d = archive_dir()
    try:
        files = sorted(os.listdir(d))
    except FileNotFoundError:
        return []
    out = []
    for fn in files:
        if not fn.endswith(".json"):
            continue
        p = os.path.join(d, fn)
        try:
            with open(p, "r", encoding="utf-8") as f:
                out.append((fn, json.load(f)))
        except Exception:
            out.append((fn, None))
    return out


def load_archive(filename):
    p = os.path.join(archive_dir(), filename)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
