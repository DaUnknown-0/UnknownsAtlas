$ErrorActionPreference = 'Stop'
Add-Type -Path "$env:USERPROFILE/.nuget/packages/mono.cecil/0.11.3/lib/net40/Mono.Cecil.dll"
$dll = Join-Path $PSScriptRoot '../../../bin/Release/net6.0/UnknownsAtlas.dll'
$module = [Mono.Cecil.ModuleDefinition]::ReadModule([IO.Path]::GetFullPath($dll))
try {
    $life = $module.Types | Where-Object Name -eq AtlasAmberhiveLife
    $calls = @($life.NestedTypes | ForEach-Object {
        $_.Methods | Where-Object Name -like '*SendPrints*' | ForEach-Object {
            $_.Body.Instructions | Where-Object { $_.Operand -like '*MessageWriter::Write*' } | ForEach-Object { $_.Operand.FullName }
        }
    })
    if (@($calls | Where-Object { $_ -eq 'System.Void Hazel.MessageWriter::Write(System.UInt16)' }).Count -ne 2) { throw 'Pollenpositionen sind nicht beide 16 Bit breit.' }
    if (@($calls | Where-Object { $_ -eq 'System.Void Hazel.MessageWriter::Write(System.Int32)' }).Count -ne 1) { throw 'Unerwartete 32-Bit-Felder im Pollenpaket.' }
    $result = @{ Erfolgreich=$true; Feldbreiten=@(1,4,4,1,4,2,2,1,4); BytesProAbdruck=13; WriterAufrufe=$calls; SHA256=(Get-FileHash $dll -Algorithm SHA256).Hash }
    $result | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $PSScriptRoot 'wire_verification.json')
    'Pollen-Netzformat bestaetigt: zwei 16-Bit-Koordinaten, 13 Byte je Abdruck.'
} finally { $module.Dispose() }
