# FIMonacci Entropy Test File Generator
# This script creates test files with different entropy levels for testing
# Run this script to generate fresh test files each time

# Configuration
$testDir = "C:\Users\orxan\OneDrive\Desktop\media\media"
$filePrefix = "entropy_test_"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FIMonacci Entropy Test File Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Delete previous test files
Write-Host "[1/4] Cleaning up old test files..." -ForegroundColor Yellow
$oldFiles = Get-ChildItem -Path $testDir -Filter "${filePrefix}*" -ErrorAction SilentlyContinue
if ($oldFiles) {
    foreach ($file in $oldFiles) {
        Remove-Item $file.FullName -Force
        Write-Host "  Deleted: $($file.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "  No old test files found" -ForegroundColor Gray
}

# Create HIGH entropy file (random bytes - simulates encrypted file)
Write-Host "`n[2/4] Creating HIGH entropy file (encrypted-like)..." -ForegroundColor Yellow
$highEntropyPath = Join-Path $testDir "${filePrefix}high_entropy.bin"
$randomBytes = New-Object byte[] 10240
$random = New-Object Random
$random.NextBytes($randomBytes)
[IO.File]::WriteAllBytes($highEntropyPath, $randomBytes)
Write-Host "  Created: ${filePrefix}high_entropy.bin (10 KB, random data)" -ForegroundColor Green
Write-Host "  Expected: Entropy >= 7.5, Classification: 'Encrypted'" -ForegroundColor Cyan

# Create LOW entropy file (plain text)
Write-Host "`n[3/4] Creating LOW entropy file (plain text)..." -ForegroundColor Yellow
$lowEntropyPath = Join-Path $testDir "${filePrefix}low_entropy.txt"
$plainText = "This is a plain text file for testing low entropy detection.`n" * 100
[IO.File]::WriteAllText($lowEntropyPath, $plainText)
Write-Host "  Created: ${filePrefix}low_entropy.txt (2.7 KB, plain text)" -ForegroundColor Green
Write-Host "  Expected: Entropy < 4.0, Classification: 'Plain Text'" -ForegroundColor Cyan

# Create MEDIUM entropy file (compressed-like pattern)
Write-Host "`n[4/4] Creating MEDIUM entropy file (compressed-like)..." -ForegroundColor Yellow
$mediumEntropyPath = Join-Path $testDir "${filePrefix}medium_entropy.bin"
$pattern = @()
for ($i = 0; $i -lt 256; $i++) {
    $pattern += [byte]($i % 128)
}
$mediumData = $pattern * 40
[IO.File]::WriteAllBytes($mediumEntropyPath, $mediumData)
Write-Host "  Created: ${filePrefix}medium_entropy.bin (10 KB, pattern data)" -ForegroundColor Green
Write-Host "  Expected: Entropy 4.0-7.5, Classification: 'Compressed'" -ForegroundColor Cyan

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] All test files created!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Check the FIMonacci client console for debug output" -ForegroundColor White
Write-Host "  2. Look for emoji messages like:" -ForegroundColor White
Write-Host "     - [Chart] Calculating entropy for: ..." -ForegroundColor Gray
Write-Host "     - [Lock] HIGH ENTROPY DETECTED (Encrypted): ..." -ForegroundColor Gray
Write-Host "     - [Box] COMPRESSED FILE DETECTED: ..." -ForegroundColor Gray
Write-Host "     - [Page] PLAIN TEXT DETECTED: ..." -ForegroundColor Gray
Write-Host "  3. Check the Alerts page for proper entropy values" -ForegroundColor White
Write-Host ""
Write-Host "Files created in: $testDir" -ForegroundColor Cyan
