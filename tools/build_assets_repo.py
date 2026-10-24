# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# build_assets_repo.py [tag]: Kartenbilder aus der DLL auslagern (Download wie die UTS-Musik).
#
# Kopiert alle Dateien, die Atlas zur Laufzeit aus dem Asset-Repo laedt, nach ../UnknownsAtlas-Assets/files/,
# schreibt dort catalog.json und erzeugt src/AtlasAssetCatalog.g.cs (Name, Ressource, Groesse, SHA-256, Tag).
# Danach im Asset-Repo committen, Tag setzen (v1, v2 ...) und pushen; derselbe Tag steht dann im Katalog der DLL.
# Dateien, die im Asset-Ordner liegen, aber nicht mehr im Katalog stehen, werden dort geloescht.
#
# Ausgelagert: Boden-, Objekt- und Konsolenatlanten (.atx) aller eingebauten Karten, die Minispiel- und
# Rauswurfgrafiken (task_*), die Grafiken der Vanilla-Krisen (task_vc_*, fx_vc_*) und die Bilder der Zugkarte
# (Bodenkacheln, Objekte, Konsolen, Hintergrund, Effekte, Minispiele). In der DLL bleiben nur Dinge, die vor dem
# ersten Download gebraucht werden: Knoepfe und Symbole (button_*, icon_*, task_*_button), Minikarten, Klaenge,
# map.json der Karten im Dateiformat. Das Werkzeug prueft, dass keine ausgelagerte Datei zugleich im csproj
# eingebettet ist (sonst laege sie doppelt vor: in der DLL und im Download).

import fnmatch
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
REPO = ROOT.parent / "UnknownsAtlas-Assets"
CS = ROOT / "src" / "AtlasAssetCatalog.g.cs"
CSPROJ = ROOT / "UnknownsAtlas.csproj"

RES = "UnknownsAtlas.Resources."

# (Ordner unter assets, Ressourcen-Praefix, Muster, Ausnahmen)
GROUPS = [
    ("", RES,
     ["museum_floor_*.atx", "museum_props_*.atx", "museum_consoles_*.atx",
      "wald_floor_*.atx", "wald_props_*.atx", "wald_consoles_*.atx",
      "park_floor_*.atx", "park_props_*.atx", "park_consoles_*.atx",
      "task_*.png", "task_eject_*.jpg"], []),
    # Vanilla-Krisen: Minispiel-Tafeln und Effekte; die Kartenknoepfe icon_vc_* bleiben eingebettet
    ("vanilla_crises", RES, ["task_vc_*.png", "fx_vc_*.png"], []),
    # Zugkarte (Karte im Dateiformat): alles ausser map.json, Knopf, Symbol, Minikarte und Benutzen-Knoepfen
    ("train", "UnknownsAtlas.Maps.train.",
     ["train_floor_*.png", "train_props_*.png", "train_consoles_*.png", "train_scroll*.png", "train_fx_*.png",
      "task_train_*.png"],
     ["*_button.png"]),
]


# Gerenderte Vorspanne (AtlasCinematic), gebaut ausserhalb des Repos von Assets/Cinematics/_common/make_pack.py:
# Dateiname -> (Quelldatei, Ressourcenname)
CINEMATICS = {
    "train_intro.cine": (ROOT.parent / "Assets" / "Cinematics" / "train" / "train_intro.cine", "UnknownsAtlas.Maps.train.train_intro.cine"),
}


def collect():
    out = {}
    for name, (p, res) in CINEMATICS.items():
        if not p.exists():
            sys.exit(f"Vorspann fehlt: {p}")
        out[name] = (p, res)
    for sub, prefix, pats, excl in GROUPS:
        base = ASSETS / sub if sub else ASSETS
        for pat in pats:
            for p in base.glob(pat):
                if any(fnmatch.fnmatch(p.name, x) for x in excl):
                    continue
                if p.name in out and out[p.name][0] != p:
                    sys.exit(f"Name doppelt: {p.name} ({out[p.name][0]} und {p})")
                out[p.name] = (p, prefix + p.name)
    return [out[k] for k in sorted(out)]


def embedded_globs():
    text = CSPROJ.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    globs = []
    for inc in re.findall(r'<EmbeddedResource\s+Include="([^"]+)"', text):
        globs += [g.strip().replace("\\", "/") for g in inc.split(";") if g.strip()]
    return globs


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "v1"
    files = collect()
    globs = embedded_globs()
    double = [p for p, _ in files if p.is_relative_to(ROOT) and any(fnmatch.fnmatch(p.relative_to(ROOT).as_posix(), g) for g in globs)]
    if double:
        sys.exit("ausgelagert UND im csproj eingebettet:\n  " + "\n  ".join(str(p.relative_to(ROOT)) for p in double))
    out = REPO / "files"
    out.mkdir(parents=True, exist_ok=True)
    keep = {p.name for p, _ in files}
    removed = 0
    for old in out.iterdir():
        if old.is_file() and old.name not in keep:
            old.unlink()
            removed += 1
    entries = []
    for p, res in files:
        data = p.read_bytes()
        entries.append({"name": p.name, "res": res, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        dst = out / p.name
        if not dst.exists() or dst.read_bytes() != data:
            shutil.copyfile(p, dst)
    (REPO / "catalog.json").write_text(json.dumps({"tag": tag, "files": entries}, indent=1), encoding="utf-8")
    lines = ["// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0",
             "// Licensed under GPL-3.0-or-later. See LICENSE for details.",
             "//",
             "// AUTOMATISCH ERZEUGT von tools/build_assets_repo.py - NICHT VON HAND AENDERN.",
             "// Dateien, die Atlas aus dem Asset-Repo laedt (AtlasAssetStore): Dateiname im Repo, Ressourcenname,",
             "// unter dem der Code sie anfragt, Groesse und SHA-256.",
             "",
             "namespace UnknownsAtlas;",
             "",
             "internal static class AtlasAssetCatalog",
             "{",
             f"    public const string Tag = \"{tag}\";",
             "",
             "    public static readonly (string Name, string Res, long Size, string Sha256)[] Files =",
             "    {"]
    for e in entries:
        lines.append(f"        (\"{e['name']}\", \"{e['res']}\", {e['size']}L, \"{e['sha256']}\"),")
    lines += ["    };", "}", ""]
    CS.write_text("\n".join(lines), encoding="utf-8")
    total = sum(e["size"] for e in entries)
    print(f"{len(entries)} Dateien, {total / 1048576:.1f} MB -> {out} ({removed} alte entfernt)")
    print(f"Katalog {tag} -> {CS.name}")


if __name__ == "__main__":
    main()
