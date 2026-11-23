param([string]$CertifiBundle, [string]$OutFile = "$env:USERPROFILE\certs\combined.pem")
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null
$sb = New-Object System.Text.StringBuilder
[void]$sb.Append([IO.File]::ReadAllText($CertifiBundle))
$seen = @{}; $n = 0
foreach ($store in 'Cert:\LocalMachine\Root','Cert:\CurrentUser\Root') {
    foreach ($c in Get-ChildItem $store) {
        if ($seen.ContainsKey($c.Thumbprint)) { continue }
        $seen[$c.Thumbprint] = $true
        $b64 = [Convert]::ToBase64String($c.RawData, 'InsertLineBreaks')
        [void]$sb.Append("`n# $($c.Subject)`n-----BEGIN CERTIFICATE-----`n$b64`n-----END CERTIFICATE-----`n")
        $n++
    }
}
[IO.File]::WriteAllText($OutFile, $sb.ToString())
"Wrote $OutFile with certifi bundle + $n Windows-trusted roots"
