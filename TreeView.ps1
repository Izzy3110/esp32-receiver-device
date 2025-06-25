param (
    [string]$Path = ".",
    [string]$OutputFile = "lib_treeview.txt",
    [int]$IndentLevel = 0
)

function Show-Tree {
    param (
        [string]$Path,
        [string]$OutputFile,
        [int]$IndentLevel
    )

    $indent = ("|   " * $IndentLevel)
    $items = Get-ChildItem -LiteralPath $Path | Sort-Object -Property PSIsContainer, Name

    for ($i = 0; $i -lt $items.Count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $items.Count - 1)
        $prefix = if ($isLast) { "`+--" } else { "|--" }
        Add-Content -Path $OutputFile -Value "$indent$prefix $($item.Name)"

        if ($item.PSIsContainer) {
            Show-Tree -Path $item.FullName -OutputFile $OutputFile -IndentLevel ($IndentLevel + 1)
        }
    }
}

# Clear output file if it exists
if (Test-Path $OutputFile) {
    Clear-Content $OutputFile
}

if (-not (Test-Path $Path)) {
    Write-Error "Path '$Path' does not exist."
    exit
}

Add-Content -Path $OutputFile -Value "Directory Tree: $Path`n"
Show-Tree -Path $Path -OutputFile $OutputFile -IndentLevel 0
