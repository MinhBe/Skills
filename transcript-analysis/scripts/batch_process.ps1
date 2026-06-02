$SourceDir = "C:\Projects\Dashboard\1. Capture\Better_Version"
$CleanDir = "$SourceDir\clean"
$TreeDir = "$SourceDir\trees"
$OutputDir = "C:\Projects\Dashboard\4. Blueprint\Books"
$SkillDir = "C:\Projects\Dashboard\6. Vault\Skill\transcript-analysis"
$ScriptsDir = "$SkillDir\scripts"

New-Item -ItemType Directory -Path $CleanDir -Force | Out-Null
New-Item -ItemType Directory -Path $TreeDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$mdFiles = Get-ChildItem "$SourceDir\*_Fast.md" -File
$total = $mdFiles.Count
$i = 0

$results = @()

foreach ($file in $mdFiles) {
    $i++
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $cleanFile = "$CleanDir\$baseName.txt"
    $treeFile = "$TreeDir\$baseName.tree.json"

    Write-Progress -Activity "Processing files" -Status "$i / $total - $baseName" -PercentComplete (($i / $total) * 100)

    python "$ScriptsDir\preprocess_transcript.py" --input $file.FullName --output $cleanFile 2>$null
    if (-Not (Test-Path $cleanFile)) {
        Write-Host "[SKIP] $baseName - preprocess failed" -ForegroundColor Yellow
        continue
    }

    $videoTitle = $baseName -replace '_Fast', '' -replace '_', ' '
    python "$ScriptsDir\content_mapper.py" --input $cleanFile --source-type youtube --video-title "$videoTitle" --output $treeFile 2>$null
    if (-Not (Test-Path $treeFile)) {
        Write-Host "[SKIP] $baseName - content_mapper failed" -ForegroundColor Yellow
        continue
    }

    try {
        $treeContent = Get-Content $treeFile -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Host "[SKIP] $baseName - invalid JSON" -ForegroundColor Yellow
        continue
    }

    $bookMatch = [regex]::Match($baseName, 'S[áa]ch\s+(.+?)(?:_Fast|$)')
    $bookName = if ($bookMatch.Success) { $bookMatch.Groups[1].Value.Trim() } else { "" }

    $results += [PSCustomObject]@{
        FileName = $file.Name
        BaseName = $baseName
        BookName = $bookName
        WordCount = $treeContent.word_count
        LeafCount = $treeContent.estimated_leaf_nodes
        YieldCheck = $treeContent.minimum_yield_check
        TreePath = $treeFile
    }

    Write-Host "[OK] $baseName - $($treeContent.estimated_leaf_nodes) leaves, $($treeContent.word_count) words" -ForegroundColor Green
}

# Build dossier as string[] instead of here-string
$dossierLines = New-Object System.Collections.Generic.List[string]

$dossierLines.Add("# Master Learning Dossier - Better Version Library")
$dossierLines.Add("")
$dossierLines.Add("**Domain:** book")
$dossierLines.Add("**Source type:** youtube")
$dossierLines.Add("**Channel:** Better Version")
$dossierLines.Add("**Total sources processed:** $($results.Count)")
$dossierLines.Add("**Extracted:** $(Get-Date -Format 'yyyy-MM-dd')")
$dossierLines.Add("")
$dossierLines.Add("---")
$dossierLines.Add("")
$dossierLines.Add("## T[o^]ng quan")
$dossierLines.Add("")
$dossierLines.Add("Better Version l[a`]_ k[es]nh YouTube chia s[e] ki[ees]n th[uw]c ph[a't] tri[ee]n to[a`n] di[e^]n ba[rn] th[a^]n qua c[a'c] cuo[os]n s[a'ch] hay, do m[oo^]t ng[uw] [oo^]i Vi[e^]t Nam thu[rw]c hi[e^]n. Ke[nh] t[a^.]p trung va[of] to'm t[a't] v[a`] pha^n t[i'ch] c[a'c] cuo[os]n s[a'ch] thuo[oo^]c nhi[e^]u l[ix]nh v[uw]c: pha't tri[e]n ba[rn] tha^n, ta^m l[ys] ho[c], tri[e]t ho[c], ta[i`] ch[i'nh] ca' nha^n, khoa ho[c], va[n] ho[c] va[ s] [uw]c kho[e].")
$dossierLines.Add("")
$dossierLines.Add("Better Version l[a`] ke[nh] YouTube to'm t[a't] sa'ch v[e^`] [da] l[ix]nh v[uw]c] t[uf] [Better Version channel]. Dossier n[a`y] cover $($results.Count) transcripts. Sau khi ho[c], ba[n] co' the[^'] a'p du[ng] ki[ees]n th[uw]c t[uf] nhi[e^]u l[ix]nh v[uw]c kha'c nhau va[of] cuo[oo^]c so[os]ng va[ c]o^ng vi[e^]c h[a`ng] ng[a`y].")
$dossierLines.Add("")
$dossierLines.Add("---")
$dossierLines.Add("")
$dossierLines.Add("## Mu[c lu[c] theo s[a'ch]")
$dossierLines.Add("")

$grouped = $results | Group-Object BookName
foreach ($group in $grouped) {
    $bookLabel = if ([string]::IsNullOrWhiteSpace($group.Name)) { "Kho^ng xa'c [di. nh]" } else { $group.Name }
    $dossierLines.Add("### $bookLabel")
    $dossierLines.Add("")
    $idx = 0
    foreach ($item in $group.Group) {
        $idx++
        $leafInfo = $item.YieldCheck
        $dossierLines.Add("$idx. **$($item.BaseName)** - $($item.WordCount) t[uw], $($item.LeafCount) concepts _($leafInfo)_")
    }
    $dossierLines.Add("")
}

$dossierLines.Add("---")
$dossierLines.Add("")
$dossierLines.Add("## Tho[oos]ng ke^ t[oo^]ng ho[sp]")
$dossierLines.Add("")
$dossierLines.Add("| Metric | Value |")
$dossierLines.Add("|--------|-------|")
$dossierLines.Add("| To[^']ng so[os] transcript | $($results.Count) |")
$dossierLines.Add("| To[^']ng so[os] t[uw] (word count) | $(($results | Measure-Object WordCount -Sum).Sum) |")
$totalLeaves = ($results | Measure-Object LeafCount -Sum).Sum
$dossierLines.Add("| To[^']ng so[os] leaf nodes | $totalLeaves |")
$avgLeaves = [math]::Round(($results | Measure-Object LeafCount -Average).Average, 1)
$dossierLines.Add("| Trung b`nh leaves/video | $avgLeaves |")
$avgWords = [math]::Round(($results | Measure-Object WordCount -Average).Average, 0)
$dossierLines.Add("| Trung b`nh t[uw]/video | $avgWords |")
$dossierLines.Add("")
$dossierLines.Add("### Pha^n pho[oos]i Yield Check")
$dossierLines.Add("")

$yieldStats = $results | Group-Object { ($_.YieldCheck -split ':')[0].Trim() }
foreach ($ys in $yieldStats) {
    $pct = [math]::Round(($ys.Count / $results.Count) * 100, 1)
    $dossierLines.Add("- **$($ys.Name)**: $($ys.Count) files ($pct%)")
}

$dossierLines.Add("")
$dossierLines.Add("---")
$dossierLines.Add("")
$dossierLines.Add("## Danh s[a'ch] [d] [a^`y] [d]u[ur] (chi tie^t t[uf]ng transcript)")
$dossierLines.Add("")

$idx = 0
foreach ($r in $results) {
    $idx++
    try {
        $tree = Get-Content $r.TreePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        continue
    }

    $dossierLines.Add("### $idx. $($r.BaseName)")
    $dossierLines.Add("")
    $dossierLines.Add("| Field | Value |")
    $dossierLines.Add("|-------|-------|")
    $dossierLines.Add("| Sa'ch | $($r.BookName) |")
    $dossierLines.Add("| Word count | $($r.WordCount) |")
    $dossierLines.Add("| Leaf nodes | $($r.LeafCount) |")
    $dossierLines.Add("| Yield | $($r.YieldCheck) |")
    $dossierLines.Add("")
    $dossierLines.Add("**Concept tree:**")
    $dossierLines.Add("```")
    $dossierLines.Add($($tree | ConvertTo-Json -Depth 3 -Compress))
    $dossierLines.Add("```")
    $dossierLines.Add("")
    $dossierLines.Add("---")
    $dossierLines.Add("")
}

$dossierLines.Add("---")
$dossierLines.Add("*Generated on $(Get-Date -Format 'yyyy-MM-dd HH:mm') by transcript-analysis skill*")

$dossierPath = "$OutputDir\Better_Version_Master_Dossier.md"
[System.IO.File]::WriteAllLines($dossierPath, $dossierLines, [System.Text.Encoding]::UTF8)

Write-Host "`n`n====== DONE =====" -ForegroundColor Cyan
Write-Host "Processed $($results.Count) / $total files" -ForegroundColor Green
Write-Host "Dossier written to: $dossierPath" -ForegroundColor Green

$summaryPath = "$OutputDir\Better_Version_Summary.json"
$results | ConvertTo-Json -Depth 3 | Out-File -FilePath $summaryPath -Encoding UTF8
Write-Host "Summary JSON written to: $summaryPath" -ForegroundColor Green
