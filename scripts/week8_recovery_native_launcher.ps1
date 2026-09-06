param(
    [string] $ReleaseReceipt = '',
    [string] $ReceiptSha256 = '',
    [string] $LauncherSha256 = '',
    [ValidateSet('status', 'adjudicate', 'recover', 'seal', 'monitor', 'finalize', 'report', 'figures')]
    [string] $Command = 'status',
    [switch] $MeasureRuntime,
    [switch] $StartupSmoke,
    [string] $SmokeRuntime = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This script is decoded and compiled only after its own externally approved
# SHA-256 has been checked.  It is the native pre-Python side of D-167: every
# non-Windows file that can supply CPython startup code is hashed and held open
# with read-only sharing until the child exits.  Windows itself, the kernel DLL
# loader, PowerShell/.NET, and Microsoft system DLLs remain explicit trust roots.
$Python = 'D:\Aenv\pro\pro\pro2\.venv\Scripts\python.exe'
$BasePython = 'C:\Users\aladdin-alyanai\AppData\Local\Programs\Python\Python313\python.exe'
$BaseRuntime = 'C:\Users\aladdin-alyanai\AppData\Local\Programs\Python\Python313'
$Pyvenv = 'D:\Aenv\pro\pro\pro2\.venv\pyvenv.cfg'
$VenvScripts = 'D:\Aenv\pro\pro\pro2\.venv\Scripts'
$OuterPath = 'D:\Aenv\pro\pro\week8-recovery-controller-worktree\scripts\week8_recovery_outer_bootstrap.txt'
$EntryPath = 'D:\Aenv\pro\pro\week8-recovery-controller-worktree\scripts\week8_exp2a_recovery_entrypoint.py'
$HelperPath = 'D:\Aenv\pro\pro\week8-recovery-controller-worktree\scripts\week8_recovery_raw_authority.py'
$Runtime = 'D:\Aenv\pro\pro\week8-d167-native-runtime-attempt-001'
$Stage0Runtime = 'D:\Aenv\pro\pro\week8-d168-stage0-runtime-attempt-001'
$Stage0EnvelopeEnvironmentName = 'WEEK8_D168_STAGE0_ENVELOPE'
$ExpectedPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$ExpectedPythonSha256 = '935016795f3e6908e75acbc2040a01e2e4cdb494a57c42f63a0d6eedb2372256'
$ExpectedBasePythonSha256 = '5341746f92483a93e44c313de830f2fba2956f0759094404a16b2fed06c9a2ed'
$ExpectedPyvenvSha256 = 'be7ef6e263b1f7242a8ce45cf329e96896d2d5d54e7fc565acb94fb722f66d71'

# Filled from this script's deterministic MeasureRuntime mode before release.
$ExpectedBaseRuntimeFileCount = 5368
$ExpectedBaseRuntimeDirectoryCount = 504
$ExpectedBaseRuntimeTotalBytes = 155022742
$ExpectedBaseRuntimeInventorySha256 = '0a5aff918e4a46fae2427a593261f8e3640ba439ba4ffebf5081b15eb7df6760'
$ExpectedVenvScriptsFileCount = 22
$ExpectedVenvScriptsDirectoryCount = 0
$ExpectedVenvScriptsTotalBytes = 2145386
$ExpectedVenvScriptsInventorySha256 = '1b9814979baf41e16ba3f9a7e754e55fd650bd786338e6ebb3b88441e0ef4c56'

$Utf8 = New-Object System.Text.UTF8Encoding -ArgumentList @($false, $true)
$HeldStreams = New-Object 'System.Collections.Generic.List[System.IO.FileStream]'

function ConvertTo-Week8Hex([byte[]] $Bytes) {
    return ([BitConverter]::ToString($Bytes)).Replace('-', '').ToLowerInvariant()
}

function Get-Week8Sha256([byte[]] $Bytes) {
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try { return ConvertTo-Week8Hex $Hasher.ComputeHash($Bytes) }
    finally { $Hasher.Dispose() }
}

function Assert-Week8LowerHex([string] $Value, [int] $Length, [string] $What) {
    if ($null -eq $Value -or $Value.Length -ne $Length -or
        -not [Regex]::IsMatch($Value, '^[0-9a-f]+$')) {
        throw "$What is not canonical lowercase hexadecimal"
    }
    return $Value
}

function Read-Week8ReleaseReceipt(
    [string] $Text,
    [string] $ExpectedReceiptSha256,
    [string] $ExpectedLauncherSha256
) {
    [void] (Assert-Week8LowerHex $ExpectedReceiptSha256 64 'release receipt SHA-256')
    [void] (Assert-Week8LowerHex $ExpectedLauncherSha256 64 'native launcher SHA-256')
    if ($Text.IndexOf("`r", [StringComparison]::Ordinal) -ge 0) {
        throw 'release receipt contains a carriage return'
    }
    $Bytes = $Utf8.GetBytes($Text)
    if ((Get-Week8Sha256 $Bytes) -cne $ExpectedReceiptSha256) {
        throw 'release receipt SHA-256 differs'
    }
    $Lines = $Text.Split([char[]] @([char] 10))
    if ($Lines.Count -ne 10 -or $Lines[0] -cne 'WEEK8_D168_RELEASE_RECEIPT_V2' -or
        $Lines[9] -cne '') {
        throw 'release receipt framing differs'
    }
    $Names = @(
        'controller_commit', 'native_launcher_sha256', 'outer_sha256',
        'entry_sha256', 'helper_sha256', 'stage0_source_sha256',
        'stage0_encoded_sha256', 'stage0_environment_policy_sha256'
    )
    $Values = @{}
    for ($Index = 0; $Index -lt $Names.Count; $Index += 1) {
        $Prefix = $Names[$Index] + '='
        if (-not $Lines[$Index + 1].StartsWith($Prefix, [StringComparison]::Ordinal)) {
            throw 'release receipt field order or name differs'
        }
        $Value = $Lines[$Index + 1].Substring($Prefix.Length)
        $Length = if ($Names[$Index] -eq 'controller_commit') { 40 } else { 64 }
        $Values[$Names[$Index]] = Assert-Week8LowerHex $Value $Length $Names[$Index]
    }
    if ($Values['native_launcher_sha256'] -cne $ExpectedLauncherSha256) {
        throw 'release receipt does not bind the captured native launcher'
    }
    return [pscustomobject]@{
        ControllerCommit = $Values['controller_commit']
        LauncherSha256 = $Values['native_launcher_sha256']
        OuterSha256 = $Values['outer_sha256']
        EntrySha256 = $Values['entry_sha256']
        HelperSha256 = $Values['helper_sha256']
        Stage0SourceSha256 = $Values['stage0_source_sha256']
        Stage0EncodedSha256 = $Values['stage0_encoded_sha256']
        Stage0EnvironmentPolicySha256 = $Values['stage0_environment_policy_sha256']
        ReceiptSha256 = $ExpectedReceiptSha256
    }
}

function Assert-Week8NativeHost {
    $Observed = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    $Canonical = [IO.Path]::GetFullPath($Observed)
    if (-not $Canonical.Equals($ExpectedPowerShell, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'native launcher requires the fixed inbox Windows PowerShell host'
    }
    if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) {
        throw 'native launcher requires Windows PowerShell 5.1'
    }
}

function Get-Week8Stage0BindingSha256([object] $Receipt, [string] $CommandName) {
    if ([IO.Path]::GetFullPath((Get-Location).Path) -cne $Stage0Runtime) {
        throw 'stage-0 working directory differs'
    }
    $RuntimeItem = Assert-Week8PlainPath $Stage0Runtime $true
    if (@(Get-ChildItem -LiteralPath $RuntimeItem.FullName -Force).Count -ne 0) {
        throw 'stage-0 runtime directory is not empty'
    }
    $Fixed = @(
        @('ComSpec', 'C:\Windows\System32\cmd.exe'),
        @('PATH', 'C:\Windows\System32;C:\Windows'),
        @('PSModulePath', 'C:\Program Files\WindowsPowerShell\Modules;C:\Windows\System32\WindowsPowerShell\v1.0\Modules'),
        @('PathEXT', '.CPL'),
        @('SystemRoot', 'C:\Windows'),
        @('TEMP', $Stage0Runtime),
        @('TMP', $Stage0Runtime),
        @('TMPDIR', $Stage0Runtime),
        @('WINDIR', 'C:\Windows')
    )
    $Environment = [Environment]::GetEnvironmentVariables()
    if ($Environment.Count -ne ($Fixed.Count + 1)) {
        throw 'stage-0 complete host environment count differs'
    }
    $ObservedNames = @($Environment.Keys | ForEach-Object { [string] $_ })
    foreach ($Pair in $Fixed) {
        $Name = [string] $Pair[0]
        $ExactNames = @($ObservedNames | Where-Object { $_ -ceq $Name })
        if ($ExactNames.Count -ne 1 -or [string] $Environment[$Name] -cne [string] $Pair[1]) {
            throw 'stage-0 complete host environment differs'
        }
    }
    if (@($ObservedNames | Where-Object { $_ -ceq $Stage0EnvelopeEnvironmentName }).Count -ne 1) {
        throw 'stage-0 envelope environment name differs'
    }
    $Envelope = [string] $Environment[$Stage0EnvelopeEnvironmentName]
    if (-not [Regex]::IsMatch($Envelope, '^[A-Za-z0-9+/]+={0,2}$')) {
        throw 'stage-0 envelope environment value differs'
    }
    $PolicyRows = New-Object 'System.Collections.Generic.List[string]'
    [void] $PolicyRows.Add('WEEK8_D168_STAGE0_ENVIRONMENT_POLICY_V1')
    for ($Index = 0; $Index -lt ($Fixed.Count - 1); $Index += 1) {
        $Pair = $Fixed[$Index]
        [void] $PolicyRows.Add(([string] $Pair[0]) + '=' + ([string] $Pair[1]))
    }
    [void] $PolicyRows.Add($Stage0EnvelopeEnvironmentName + '=<CANONICAL_BASE64_ENVELOPE>')
    $Pair = $Fixed[$Fixed.Count - 1]
    [void] $PolicyRows.Add(([string] $Pair[0]) + '=' + ([string] $Pair[1]))
    $PolicySha256 = Get-Week8Sha256 $Utf8.GetBytes((($PolicyRows -join "`n") + "`n"))
    if ($PolicySha256 -cne $Receipt.Stage0EnvironmentPolicySha256) {
        throw 'stage-0 environment policy SHA-256 differs'
    }
    $Match = [Regex]::Match(
        [Environment]::CommandLine,
        '(?i)-EncodedCommand\s+([A-Za-z0-9+/]+={0,2})\s*$'
    )
    if (-not $Match.Success) { throw 'stage-0 encoded command line differs' }
    $Encoded = $Match.Groups[1].Value
    $SourceBytes = [Convert]::FromBase64String($Encoded)
    if ([Convert]::ToBase64String($SourceBytes) -cne $Encoded) {
        throw 'stage-0 encoded command is noncanonical'
    }
    $EncodedSha256 = Get-Week8Sha256 ([Text.Encoding]::ASCII.GetBytes($Encoded))
    $Source = [Text.Encoding]::Unicode.GetString($SourceBytes)
    $SourceSha256 = Get-Week8Sha256 ($Utf8.GetBytes($Source))
    if ($EncodedSha256 -cne $Receipt.Stage0EncodedSha256 -or
        $SourceSha256 -cne $Receipt.Stage0SourceSha256) {
        throw 'stage-0 fixed payload differs from the release receipt'
    }
    $HostRows = New-Object 'System.Collections.Generic.List[string]'
    [void] $HostRows.Add('WEEK8_D168_STAGE0_HOST_ENVIRONMENT_V1')
    for ($Index = 0; $Index -lt ($Fixed.Count - 1); $Index += 1) {
        $Pair = $Fixed[$Index]
        [void] $HostRows.Add(([string] $Pair[0]) + '=' + ([string] $Pair[1]))
    }
    [void] $HostRows.Add($Stage0EnvelopeEnvironmentName + '=' + $Envelope)
    $Pair = $Fixed[$Fixed.Count - 1]
    [void] $HostRows.Add(([string] $Pair[0]) + '=' + ([string] $Pair[1]))
    $HostEnvironmentSha256 = Get-Week8Sha256 $Utf8.GetBytes((($HostRows -join "`n") + "`n"))
    $EnvelopeSha256 = Get-Week8Sha256 ([Text.Encoding]::ASCII.GetBytes($Envelope))
    $Rows = @(
        'WEEK8_D168_STAGE0_BINDING_V1',
        "powershell=$ExpectedPowerShell",
        "runtime_path=$Stage0Runtime",
        "receipt_sha256=$($Receipt.ReceiptSha256)",
        "native_launcher_sha256=$($Receipt.LauncherSha256)",
        "stage0_source_sha256=$SourceSha256",
        "stage0_encoded_sha256=$EncodedSha256",
        "stage0_environment_policy_sha256=$PolicySha256",
        "stage0_host_environment_sha256=$HostEnvironmentSha256",
        "stage0_envelope_sha256=$EnvelopeSha256",
        "command=$CommandName"
    )
    return Get-Week8Sha256 $Utf8.GetBytes((($Rows -join "`n") + "`n"))
}

function Get-Week8StartupEnvironment([string] $RuntimePath) {
    $SafePath = "$BaseRuntime;C:\Windows\System32;C:\Windows"
    return ,@(
        @('CUDA_VISIBLE_DEVICES', '-1'),
        @('HIP_VISIBLE_DEVICES', '-1'),
        @('MKL_NUM_THREADS', '4'),
        @('NUMEXPR_NUM_THREADS', '4'),
        @('OMP_NUM_THREADS', '4'),
        @('OPENBLAS_NUM_THREADS', '4'),
        @('PATH', $SafePath),
        @('SystemRoot', 'C:\Windows'),
        @('TEMP', $RuntimePath),
        @('TMP', $RuntimePath),
        @('TMPDIR', $RuntimePath),
        @('WINDIR', 'C:\Windows')
    )
}

function Get-Week8StartupEnvironmentSha256([object[]] $Pairs) {
    $Rows = New-Object 'System.Collections.Generic.List[string]'
    [void] $Rows.Add('WEEK8_D168_STARTUP_ENVIRONMENT_V2')
    foreach ($Pair in $Pairs) {
        if ($Pair.Count -ne 2 -or ([string] $Pair[0]).IndexOf('=') -ge 0 -or
            ([string] $Pair[1]).IndexOf("`n") -ge 0 -or ([string] $Pair[1]).IndexOf("`r") -ge 0) {
            throw 'native startup environment row is malformed'
        }
        [void] $Rows.Add(([string] $Pair[0]) + '=' + ([string] $Pair[1]))
    }
    return Get-Week8Sha256 $Utf8.GetBytes((($Rows -join "`n") + "`n"))
}

function Get-Week8StartupBindingSha256(
    [object] $Receipt,
    [object] $BaseIdentity,
    [object] $VenvIdentity,
    [string] $Stage0BindingSha256,
    [string] $EnvironmentSha256,
    [string] $CommandName,
    [string] $RuntimePath
) {
    $Rows = @(
        'WEEK8_D168_STARTUP_BINDING_V2',
        "powershell=$ExpectedPowerShell",
        "receipt_sha256=$($Receipt.ReceiptSha256)",
        "native_launcher_sha256=$($Receipt.LauncherSha256)",
        "stage0_binding_sha256=$Stage0BindingSha256",
        "controller_commit=$($Receipt.ControllerCommit)",
        "outer_sha256=$($Receipt.OuterSha256)",
        "entry_sha256=$($Receipt.EntrySha256)",
        "helper_sha256=$($Receipt.HelperSha256)",
        "command=$CommandName",
        "runtime_path=$RuntimePath",
        "python_path=$Python",
        "python_sha256=$ExpectedPythonSha256",
        "base_python_path=$BasePython",
        "base_python_sha256=$ExpectedBasePythonSha256",
        "prefix_path=$BaseRuntime",
        "base_prefix_path=$BaseRuntime",
        "pyvenv_path=$Pyvenv",
        "pyvenv_sha256=$ExpectedPyvenvSha256",
        "venv_scripts_path=$($VenvIdentity.Path)",
        "venv_scripts_file_count=$($VenvIdentity.FileCount)",
        "venv_scripts_directory_count=$($VenvIdentity.DirectoryCount)",
        "venv_scripts_total_bytes=$($VenvIdentity.TotalBytes)",
        "venv_scripts_inventory_sha256=$($VenvIdentity.InventorySha256)",
        "base_runtime_path=$($BaseIdentity.Path)",
        "base_runtime_file_count=$($BaseIdentity.FileCount)",
        "base_runtime_directory_count=$($BaseIdentity.DirectoryCount)",
        "base_runtime_total_bytes=$($BaseIdentity.TotalBytes)",
        "base_runtime_inventory_sha256=$($BaseIdentity.InventorySha256)",
        "startup_environment_sha256=$EnvironmentSha256"
    )
    return Get-Week8Sha256 $Utf8.GetBytes((($Rows -join "`n") + "`n"))
}

function Assert-Week8PlainPath([string] $Path, [bool] $Directory) {
    $Expected = [IO.Path]::GetFullPath($Path)
    $Item = Get-Item -LiteralPath $Expected -Force
    if ([IO.Path]::GetFullPath($Item.FullName) -cne $Expected) {
        throw "native authority path resolved elsewhere: $Path"
    }
    if ($Directory -and -not $Item.PSIsContainer) {
        throw "native authority directory is not a directory: $Path"
    }
    if (-not $Directory -and $Item.PSIsContainer) {
        throw "native authority file is not a file: $Path"
    }
    if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "native authority path contains a reparse point: $($Item.FullName)"
    }
    $Cursor = if ($Item.PSIsContainer) { $Item } else { $Item.Directory }
    while ($null -ne $Cursor) {
        if (($Cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "native authority path contains a reparse point: $($Cursor.FullName)"
        }
        $Cursor = $Cursor.Parent
    }
    if (-not $Directory -and $Item.LinkType) {
        throw "native authority file is linked: $Path"
    }
    return $Item
}

function Open-Week8HashedFile([string] $Path) {
    $Item = Assert-Week8PlainPath $Path $false
    $Arguments = [object[]] @(
        $Item.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read,
        [IO.FileShare]::Read, 131072, [IO.FileOptions]::SequentialScan
    )
    $Stream = [Activator]::CreateInstance([IO.FileStream], $Arguments)
    try {
        $Hasher = [Security.Cryptography.SHA256]::Create()
        try { $Digest = ConvertTo-Week8Hex $Hasher.ComputeHash($Stream) }
        finally { $Hasher.Dispose() }
        $Stream.Position = 0
        [void] $HeldStreams.Add($Stream)
        return [pscustomobject]@{
            Path = $Item.FullName
            Length = [int64] $Item.Length
            Sha256 = $Digest
        }
    }
    catch {
        $Stream.Dispose()
        throw
    }
}

function Get-Week8HeldTreeIdentity([string] $Root) {
    $RootItem = Assert-Week8PlainPath $Root $true
    $Entries = New-Object 'System.Collections.Generic.List[object]'
    $RootPrefix = $RootItem.FullName.TrimEnd('\') + '\'
    foreach ($Item in Get-ChildItem -LiteralPath $RootItem.FullName -Force -Recurse) {
        if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $Item.LinkType) {
            throw "native runtime contains a linked or reparse entry: $($Item.FullName)"
        }
        if (-not $Item.FullName.StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "native runtime entry escaped its root: $($Item.FullName)"
        }
        $Relative = $Item.FullName.Substring($RootPrefix.Length).Replace('\', '/')
        [void] $Entries.Add([pscustomobject]@{ Relative = $Relative; Item = $Item })
    }
    $Entries.Sort([Comparison[object]]{
        param($Left, $Right)
        [StringComparer]::Ordinal.Compare($Left.Relative, $Right.Relative)
    })
    $ManifestHasher = [Security.Cryptography.SHA256]::Create()
    $FileCount = 0
    $DirectoryCount = 0
    $TotalBytes = [int64] 0
    try {
        foreach ($Entry in $Entries) {
            if ($Entry.Item.PSIsContainer) {
                $DirectoryCount += 1
                $Row = "D`t$($Entry.Relative)`n"
            }
            else {
                $File = Open-Week8HashedFile $Entry.Item.FullName
                $FileCount += 1
                $TotalBytes += $File.Length
                $Row = "F`t$($Entry.Relative)`t$($File.Length)`t$($File.Sha256)`n"
            }
            $Bytes = $Utf8.GetBytes($Row)
            [void] $ManifestHasher.TransformBlock($Bytes, 0, $Bytes.Length, $null, 0)
        }
        $Empty = New-Object byte[] 0
        [void] $ManifestHasher.TransformFinalBlock($Empty, 0, 0)
        return [pscustomobject]@{
            Path = $RootItem.FullName
            FileCount = $FileCount
            DirectoryCount = $DirectoryCount
            TotalBytes = $TotalBytes
            InventorySha256 = ConvertTo-Week8Hex $ManifestHasher.Hash
            RetainedReadHandleCount = $FileCount
        }
    }
    finally { $ManifestHasher.Dispose() }
}

function Assert-Week8FixedHash([string] $Path, [string] $Expected, [string] $What) {
    $Observed = Open-Week8HashedFile $Path
    if ($Observed.Sha256 -cne $Expected) { throw "$What SHA-256 differs" }
    return $Observed
}

function Assert-Week8PyvenvSemantics {
    $Bytes = [IO.File]::ReadAllBytes($Pyvenv)
    $Text = $Utf8.GetString($Bytes)
    $Expected = (@(
        "home = $BaseRuntime",
        'include-system-site-packages = false',
        'version = 3.13.5',
        "executable = $BasePython",
        "command = $BasePython -m venv D:\Aenv\pro\pro\pro2\.venv"
    ) -join "`r`n") + "`r`n"
    if ($Text -cne $Expected) {
        throw 'pyvenv.cfg startup semantics differ'
    }
}

function ConvertTo-Week8WindowsArgument([string] $Argument) {
    if ($null -eq $Argument) { throw 'native launcher argument is null' }
    if ($Argument.Length -gt 0 -and $Argument -notmatch '[\s"]') {
        return $Argument
    }
    $Builder = New-Object Text.StringBuilder
    [void] $Builder.Append('"')
    $Backslashes = 0
    foreach ($Character in $Argument.ToCharArray()) {
        if ($Character -eq '\') {
            $Backslashes += 1
        }
        elseif ($Character -eq '"') {
            if ($Backslashes -gt 0) {
                [void] $Builder.Append(('\' * (2 * $Backslashes)))
            }
            [void] $Builder.Append('\"')
            $Backslashes = 0
        }
        else {
            if ($Backslashes -gt 0) {
                [void] $Builder.Append(('\' * $Backslashes))
                $Backslashes = 0
            }
            [void] $Builder.Append($Character)
        }
    }
    if ($Backslashes -gt 0) {
        [void] $Builder.Append(('\' * (2 * $Backslashes)))
    }
    [void] $Builder.Append('"')
    return $Builder.ToString()
}

try {
    Assert-Week8NativeHost
    if ($MeasureRuntime -and $StartupSmoke) {
        throw 'native measurement and startup smoke modes are mutually exclusive'
    }
    if (-not $MeasureRuntime -and -not $StartupSmoke) {
        $Receipt = Read-Week8ReleaseReceipt `
            $ReleaseReceipt $ReceiptSha256 $LauncherSha256
    }
    $BaseIdentity = Get-Week8HeldTreeIdentity $BaseRuntime
    $VenvScriptsIdentity = Get-Week8HeldTreeIdentity $VenvScripts
    if ($MeasureRuntime) {
        [pscustomobject]@{
            BaseRuntime = $BaseIdentity
            VenvScripts = $VenvScriptsIdentity
        } | ConvertTo-Json -Compress | Write-Output
        return
    }
    if (
        $BaseIdentity.FileCount -ne $ExpectedBaseRuntimeFileCount -or
        $BaseIdentity.DirectoryCount -ne $ExpectedBaseRuntimeDirectoryCount -or
        $BaseIdentity.TotalBytes -ne $ExpectedBaseRuntimeTotalBytes -or
        $BaseIdentity.InventorySha256 -cne $ExpectedBaseRuntimeInventorySha256 -or
        $BaseIdentity.RetainedReadHandleCount -ne $ExpectedBaseRuntimeFileCount
    ) { throw 'base CPython runtime inventory differs' }
    if (
        $VenvScriptsIdentity.FileCount -ne $ExpectedVenvScriptsFileCount -or
        $VenvScriptsIdentity.DirectoryCount -ne $ExpectedVenvScriptsDirectoryCount -or
        $VenvScriptsIdentity.TotalBytes -ne $ExpectedVenvScriptsTotalBytes -or
        $VenvScriptsIdentity.InventorySha256 -cne $ExpectedVenvScriptsInventorySha256 -or
        $VenvScriptsIdentity.RetainedReadHandleCount -ne $ExpectedVenvScriptsFileCount
    ) { throw 'virtual-environment Scripts inventory differs' }

    [void] (Assert-Week8FixedHash $Python $ExpectedPythonSha256 'venv launcher')
    [void] (Assert-Week8FixedHash $BasePython $ExpectedBasePythonSha256 'base interpreter')
    [void] (Assert-Week8FixedHash $Pyvenv $ExpectedPyvenvSha256 'pyvenv.cfg')
    Assert-Week8PyvenvSemantics
    if (-not $StartupSmoke) {
        $Outer = Assert-Week8FixedHash $OuterPath $Receipt.OuterSha256 'outer bootstrap'
        [void] (Assert-Week8FixedHash $EntryPath $Receipt.EntrySha256 'entrypoint')
        [void] (Assert-Week8FixedHash $HelperPath $Receipt.HelperSha256 'raw helper')
    }

    $WorkspaceItem = Assert-Week8PlainPath 'D:\Aenv\pro\pro' $true
    if ($StartupSmoke) {
        if ([string]::IsNullOrWhiteSpace($SmokeRuntime)) {
            throw 'native startup smoke requires an explicit runtime path'
        }
        $RuntimeFullPath = [IO.Path]::GetFullPath($SmokeRuntime)
        $SmokeRoot = Assert-Week8PlainPath 'D:\Aenv\pro\pro\.tmp' $true
        $SmokePrefix = $SmokeRoot.FullName.TrimEnd('\') + '\'
        if (-not $RuntimeFullPath.StartsWith(
            $SmokePrefix, [StringComparison]::OrdinalIgnoreCase
        )) {
            throw 'native startup smoke runtime is outside project-local .tmp'
        }
    }
    else {
        $RuntimeFullPath = [IO.Path]::GetFullPath($Runtime)
        if (-not [IO.Path]::GetDirectoryName($RuntimeFullPath).Equals(
            $WorkspaceItem.FullName, [StringComparison]::OrdinalIgnoreCase
        )) {
            throw 'native launcher runtime is not one direct project-local directory'
        }
    }
    if ([IO.File]::Exists($RuntimeFullPath)) {
        throw 'native launcher runtime path is a file'
    }
    if (-not [IO.Directory]::Exists($RuntimeFullPath)) {
        [void] [IO.Directory]::CreateDirectory($RuntimeFullPath)
    }
    $RuntimeItem = Assert-Week8PlainPath $RuntimeFullPath $true
    if (@(Get-ChildItem -LiteralPath $RuntimeItem.FullName -Force).Count -ne 0) {
        throw 'native launcher runtime directory is not empty'
    }

    $EnvironmentPairs = Get-Week8StartupEnvironment $RuntimeItem.FullName
    if ($StartupSmoke) {
        $ChildLiteral = @'
import ctypes,json,os,sys
k=ctypes.WinDLL("kernel32",use_last_error=True)
g=k.GetEnvironmentStringsW
g.restype=ctypes.c_void_p
f=k.FreeEnvironmentStringsW
f.argtypes=[ctypes.c_void_p]
p=g()
rows=[]
offset=0
width=ctypes.sizeof(ctypes.c_wchar)
try:
 while True:
  value=ctypes.wstring_at(p+offset*width)
  if not value: break
  rows.append(value)
  offset+=len(value)+1
finally:
 if not f(p): raise OSError(ctypes.get_last_error())
print(json.dumps({"argv":sys.argv,"cwd":os.getcwd(),"native_environment":rows,"orig_argv":sys.orig_argv,"executable":sys.executable,"base_executable":getattr(sys,"_base_executable",None),"prefix":sys.prefix,"base_prefix":sys.base_prefix},sort_keys=True))
'@
        $ChildArguments = @(
            '-I', '-S', '-B', '-X', 'utf8', '-c', $ChildLiteral, 'plain', 'two words',
            'quote"inside', 'trailing\', "line1`nline2", ''
        )
    }
    else {
        $OuterBytes = [IO.File]::ReadAllBytes($Outer.Path)
        $OuterLiteral = $Utf8.GetString($OuterBytes)
        $EnvironmentSha256 = Get-Week8StartupEnvironmentSha256 $EnvironmentPairs
        $Stage0BindingSha256 = Get-Week8Stage0BindingSha256 $Receipt $Command
        $StartupBindingSha256 = Get-Week8StartupBindingSha256 `
            $Receipt $BaseIdentity $VenvScriptsIdentity $Stage0BindingSha256 `
            $EnvironmentSha256 `
            $Command $RuntimeItem.FullName
        $ChildArguments = @(
            '-I', '-S', '-B', '-X', 'utf8', '-c', $OuterLiteral, $Receipt.EntrySha256,
            $Receipt.HelperSha256, $Receipt.ControllerCommit, $Command,
            $Receipt.ReceiptSha256, $Receipt.LauncherSha256,
            $Stage0BindingSha256, $StartupBindingSha256
        )
    }

    $Info = New-Object Diagnostics.ProcessStartInfo
    $Info.FileName = $Python
    $Info.WorkingDirectory = $RuntimeItem.FullName
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $true
    $Info.RedirectStandardInput = $true
    $Info.RedirectStandardOutput = $true
    $Info.RedirectStandardError = $true
    $Info.StandardOutputEncoding = [Text.Encoding]::UTF8
    $Info.StandardErrorEncoding = [Text.Encoding]::UTF8
    $Info.EnvironmentVariables.Clear()
    foreach ($Pair in $EnvironmentPairs) {
        $Info.EnvironmentVariables[$Pair[0]] = $Pair[1]
    }
    $Info.Arguments = (($ChildArguments | ForEach-Object {
        ConvertTo-Week8WindowsArgument ([string] $_)
    }) -join ' ')
    $Process = [Diagnostics.Process]::Start($Info)
    $Process.StandardInput.Close()
    $Stdout = $Process.StandardOutput.ReadToEndAsync()
    $Stderr = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    $OutputText = $Stdout.GetAwaiter().GetResult()
    $ErrorText = $Stderr.GetAwaiter().GetResult()
    if ($OutputText) { $OutputText | Write-Output }
    if ($ErrorText) { [Console]::Error.Write($ErrorText) }
    if ($Process.ExitCode -ne 0) {
        throw "Week-8 authority command $Command refused with exit code $($Process.ExitCode)"
    }
}
finally {
    foreach ($Stream in $HeldStreams) { $Stream.Dispose() }
}
