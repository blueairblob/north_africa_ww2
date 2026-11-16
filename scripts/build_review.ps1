$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root '.venv-review-win\Scripts\python.exe'
if (-not (Test-Path $python)) {
    py -3.13 -m venv (Join-Path $root '.venv-review-win')
}
& $python -m pip install --disable-pip-version-check -r requirements-review-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }
& $python scripts/make_icon.py
if ($LASTEXITCODE -ne 0) { throw 'Icon build failed.' }
& $python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name 'Benghazi Handicap' --icon art/icon.ico `
    --add-data 'art/basemap.jpg:art' `
    --add-data 'art/history:art/history' `
    --add-data 'art/counters:art/counters' `
    --add-data 'art/fonts:art/fonts' `
    --add-data 'data:data' play.py
if ($LASTEXITCODE -ne 0) { throw 'Windows executable build failed.' }
$folder = Join-Path $root 'dist\Benghazi Handicap'
Copy-Item docs\REVIEWER_GUIDE.md (Join-Path $folder 'READ ME FIRST.txt')
Copy-Item docs\ART_CREDITS.md (Join-Path $folder 'ART CREDITS.txt')
Copy-Item docs\FULL_CAMPAIGN_TRIAL_1940_1942.md (Join-Path $folder 'CAMPAIGN RESEARCH NOTES.txt')
Copy-Item docs\HISTORICAL_VALIDATION_LEDGER.md (Join-Path $folder 'HISTORICAL VALIDATION LEDGER.txt')
$historyFolder = Join-Path $folder 'Historical Research'
New-Item -ItemType Directory -Path $historyFolder -Force | Out-Null
Copy-Item docs\HISTORICAL_STORY_REVIEW.md (Join-Path $historyFolder 'HISTORICAL STORY.md')
New-Item -ItemType Directory -Path (Join-Path $folder 'art') -Force | Out-Null
Copy-Item art\history (Join-Path $folder 'art\history') -Recurse -Force
$historyRecord = Get-Content data\history\north_africa_1940_1942.json -Raw | ConvertFrom-Json
$battleRecord = Get-Content data\history\battles_1940_1942.json -Raw | ConvertFrom-Json
$historyStories = @($historyRecord.episodes) + @($battleRecord.battles)
$historyNotes = $historyStories | ForEach-Object { $_.research } | Sort-Object -Unique
foreach ($note in $historyNotes) {
    Copy-Item $note (Join-Path $historyFolder (Split-Path $note -Leaf))
}
Copy-Item 'scripts\Compass Research Trial.cmd' (Join-Path $folder 'Compass Research Trial.cmd')
Copy-Item 'scripts\Campaign Research Trial.cmd' (Join-Path $folder 'Campaign Research Trial.cmd')
$menu = Join-Path $env:TEMP ('benghazi-review-menu-' + [guid]::NewGuid().ToString('N') + '.png')
$game = Join-Path $env:TEMP ('benghazi-review-game-' + [guid]::NewGuid().ToString('N') + '.png')
$trial = Join-Path $env:TEMP ('benghazi-review-trial-' + [guid]::NewGuid().ToString('N') + '.png')
$campaign = Join-Path $env:TEMP ('benghazi-review-campaign-' + [guid]::NewGuid().ToString('N') + '.png')
$exe = Join-Path $folder 'Benghazi Handicap.exe'
$check = Start-Process -FilePath $exe -ArgumentList @('--shot', $menu) -Wait -PassThru
if ($check.ExitCode -ne 0 -or -not (Test-Path $menu)) { throw 'Packaged menu smoke test failed.' }
$check = Start-Process -FilePath $exe -ArgumentList @('sidi_rezegh', '--shot', $game) -Wait -PassThru
if ($check.ExitCode -ne 0 -or -not (Test-Path $game)) { throw 'Packaged game smoke test failed.' }
$check = Start-Process -FilePath $exe -ArgumentList @('--trial', 'compass_opening', '--at', 'Nibeiwa', '--shot', $trial) -Wait -PassThru
if ($check.ExitCode -ne 0 -or -not (Test-Path $trial)) { throw 'Packaged Compass trial smoke test failed.' }
$check = Start-Process -FilePath $exe -ArgumentList @('--trial', 'italian_frontier_1940', '--shot', $campaign) -Wait -PassThru
if ($check.ExitCode -ne 0 -or -not (Test-Path $campaign)) { throw 'Packaged campaign trial smoke test failed.' }
Remove-Item $menu, $game, $trial, $campaign
$zip = Join-Path $root 'dist\Benghazi-Handicap-Windows-Review.zip'
$packed = $false
for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path $folder -DestinationPath $zip -CompressionLevel Optimal -ErrorAction Stop
        $packed = $true
        break
    } catch {
        if ($attempt -eq 5) { throw }
        Start-Sleep -Seconds 2
    }
}
if (-not $packed) { throw 'Review archive was not created.' }
Write-Host "Review build: $zip"
