from pathlib import Path

HERE = Path(__file__).resolve().parent
for name, old, new in [
    ('DuoRun.cs', '"roles" => PlanRoles(),', '"hivev4" => PlanHiveV4(),\n            "roles" => PlanRoles(),'),
    ('DuoRun.cs', 'var a = msg.Split(\' \');', 'if (HiveV4.Handle(msg)) return;\n        var a = msg.Split(\' \');'),
    ('DuoCore.cs', 'DuoCommands.Tick();', 'DuoCommands.Tick();\n        HiveV4.Tick();'),
]:
    p = HERE / name
    text = p.read_text(encoding='utf-8-sig')
    if new not in text:
        assert old in text, (name, old)
        p.write_text(text.replace(old, new), encoding='utf-8')
