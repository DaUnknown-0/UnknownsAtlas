# Helfer fuer maptest.sh: Test-Configs setzen bzw. die letzte Spielsitzung aus LogOutput.log ziehen.
#   python maptest_cfg.py <configordner> <karte> <tasktest> [Abschnitt.Schluessel=Wert ...]
#   python maptest_cfg.py --log <LogOutput.log> <ziel>
import re
import sys


def put(s, sec, key, val):
    i = s.index("[" + sec + "]")
    j = s.find("\n[", i + 1)
    j = len(s) if j < 0 else j
    blk = s[i:j]
    blk2, n = re.subn(r"(?m)^" + re.escape(key) + r" = .*$", f"{key} = {val}", blk)
    if n == 0:
        blk2 = blk.rstrip("\n") + f"\n{key} = {val}\n\n"
    return s[:i] + blk2 + s[j:]


def main(a):
    if a[0] == "--log":
        s = open(a[1], encoding="utf-8", errors="replace").read()
        p = re.split(r"(?m)^\[Message: Preloader\] BepInEx ", s)[-1]
        keep = [l for l in p.splitlines()
                if re.search(r"\[Atlas|Exception|\[Error|\[Warning:UNKNOWN", l) and "IMoniker" not in l
                and "GetTypesFromAssembly" not in l]
        open(a[2], "w", encoding="utf-8").write("\n".join(keep) + "\n")
        return
    cf, mp, task = a[0], a[1], a[2]
    p = cf + "/com.daunknown0.atlas.cfg"
    s = open(p, encoding="utf-8").read()
    s = put(s, "General", "Enabled", "true")
    s = put(s, "Diagnostics", "ForceMap", mp)
    s = put(s, "Diagnostics", "TaskTest", task)
    s = put(s, "Diagnostics", "MapShot", "true")
    for kv in a[3:]:
        k, v = kv.split("=", 1)
        sec, key = k.split(".", 1)
        s = put(s, sec, key, v)
    open(p, "w", encoding="utf-8").write(s)



if __name__ == "__main__":
    main(sys.argv[1:])
