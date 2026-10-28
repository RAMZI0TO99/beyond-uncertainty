param(
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$RequestSha256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$RootAdmissionSha256
)
$ErrorActionPreference='Stop'
$entry=[DateTimeOffset]::UtcNow
$watch=[Diagnostics.Stopwatch]::StartNew()
$run=$PSScriptRoot
$root='D:\Aenv\pro3'
$scope='cho51_p3_contracts_20261027_v1_bootstrap_observation_004'
$runtime='C:\Users\aladdin-alyanai\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell'
if($run -cne 'D:\Aenv\pro3\runs\coordination\cho51_p3_contracts_20261027_v1' -or $PSCommandPath -cne (Join-Path $run 'bootstrap-observation_004.ps1')){throw 'Exact owned bootstrap Source path required'}
$pauses=@('20261007','20261012','20261013','20261015','20261025')|ForEach-Object{"D:\Aenv\pro2\WORK\resume-$_-001\coordination\PRO2_REQUEST_PRO3_PAUSE.json"}
function Need([bool]$condition,[string]$message){if(-not $condition){throw $message}}
function Missing-Path($exception){
 $depth=0
 while($null -ne $exception.InnerException -and ($exception -is [Management.Automation.RuntimeException] -or $exception -is [Reflection.TargetInvocationException])){
  $depth++;if($depth -gt 4){throw 'Excessive filesystem exception wrapping'}
  $exception=$exception.InnerException
 }
 return (($exception -is [IO.FileNotFoundException] -and ($exception.HResult -band 65535) -eq 2) -or ($exception -is [IO.DirectoryNotFoundException] -and ($exception.HResult -band 65535) -eq 3))
}
function Present([string]$path){
 Need ([IO.Path]::IsPathFullyQualified($path) -and [IO.Path]::GetFullPath($path) -ceq $path) 'Direct normalized presence path required'
 try{[void][IO.File]::GetAttributes($path);return $true}
 catch{if(-not (Missing-Path $_.Exception)){throw}}
 $parent=[IO.Path]::GetDirectoryName($path);$depth=0
 while(-not [string]::IsNullOrEmpty($parent)){
  $depth++;Need ($depth -le 16) 'Bounded presence ancestry required'
  try{
   $attributes=[IO.File]::GetAttributes($parent)
   Need (($attributes -band [IO.FileAttributes]::Directory) -ne 0 -and ($attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'Accessible direct directory ancestor required for known absence'
   return $false
  }catch{if(-not (Missing-Path $_.Exception)){throw}}
  $parent=[IO.Path]::GetDirectoryName($parent)
 }
 throw 'No accessible directory ancestor establishes known absence'
}
function Read-Metadata([string]$path,[string]$expected){
 $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 try{
  Need ($stream.Length -gt 0 -and $stream.Length -le 1048576) 'Bounded bootstrap metadata required'
  $raw=[byte[]]::new([int]$stream.Length);$stream.ReadExactly($raw)
  $observed=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
  Need ($observed -ceq $expected) 'Independent bootstrap metadata pin changed'
  $document=[Text.Json.JsonDocument]::Parse([ReadOnlyMemory[byte]]::new($raw))
  try{
   $script:jsonNodes=0
   function Inspect-Json($element,[int]$depth){
    $script:jsonNodes++;Need ($depth -le 32 -and $script:jsonNodes -le 50000) 'Bounded bootstrap JSON graph required'
    if($element.ValueKind -eq [Text.Json.JsonValueKind]::Object){
     $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
     foreach($property in $element.EnumerateObject()){Need ($names.Add($property.Name)) 'Duplicate JSON property';Inspect-Json $property.Value ($depth+1)}
    }elseif($element.ValueKind -eq [Text.Json.JsonValueKind]::Array){foreach($child in $element.EnumerateArray()){Inspect-Json $child ($depth+1)}}
    elseif($element.ValueKind -eq [Text.Json.JsonValueKind]::Number){$number=$element.GetDouble();Need (-not [double]::IsInfinity($number) -and -not [double]::IsNaN($number)) 'Finite JSON number required'}
   }
   Inspect-Json $document.RootElement 0
  }finally{$document.Dispose()}
  return ,([Text.UTF8Encoding]::new($false,$true).GetString($raw)|ConvertFrom-Json -AsHashtable -DateKind String)
 }finally{$stream.Dispose()}
}
function Effect-Clock{
 $now=[DateTimeOffset]::UtcNow
 Need ($watch.Elapsed.TotalSeconds -lt 50 -and $now -lt $entry.AddSeconds(50)) 'Bootstrap helper effect deadline reached'
 Need ($now -ge $start -and $now -lt $end.AddSeconds(-60) -and $now -lt (Utc $sourceScope 'interval_end').AddSeconds(-60)) 'Strict live publication reserve required'
 foreach($pausePath in $pauses){Need (-not (Present $pausePath)) 'Genuine peer pause before or after effect'}
}
function Write-New([string]$path,$value){
 Effect-Clock
 $raw=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 12 -Compress)+[char]10)
 Need ($raw.Length -le 1048576) 'Bounded bootstrap output required'
 Effect-Clock
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 Effect-Clock
 $expected=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
 [void](Read-Metadata $path $expected)
 Effect-Clock
}
$request=Read-Metadata (Join-Path $run 'bootstrap-request_004.json') $RequestSha256
$admission=Read-Metadata (Join-Path $run 'bootstrap-admission_004.json') $RootAdmissionSha256
Need ($request.schema -ceq 'cho51_p3_bootstrap_observation_request_v1' -and $request.scope -ceq $scope) 'Exact bootstrap request required'
Need ($admission.schema -ceq 'cho51_p3_bootstrap_observation_admission_v1' -and $admission.accepted -is [bool] -and $admission.accepted) 'Fresh exact Root bootstrap admission required'
Need ($admission.request_sha256 -ceq $RequestSha256) 'Root admission request differs'
Need ($admission.peer_decision_path -is [string] -and $admission.peer_decision_path.StartsWith('D:\Aenv\pro2\WORK\resume-20261027-002\coordination\',[StringComparison]::Ordinal) -and [IO.Path]::GetFullPath($admission.peer_decision_path) -ceq $admission.peer_decision_path) 'Direct normalized genuine peer decision path required'
$peer=Read-Metadata $admission.peer_decision_path $admission.peer_decision_sha256
foreach($record in @($request,$peer,$admission)){
 Need ($record.scope -ceq $scope) 'Bootstrap scope differs'
 Need ($record.maximum_seconds -is [long] -and $record.maximum_seconds -eq 90) 'Exact90-second full-caller bootstrap bound required'
 Need ($record.maximum_files -is [long] -and $record.maximum_files -eq 2500 -and $record.maximum_code_bytes -is [long] -and $record.maximum_code_bytes -eq 1073741824) 'Bootstrap read inventory bounds differ'
 foreach($field in @('startup_ram_gib','active_ram_gib')){Need ($record[$field] -is [long] -and $record[$field] -eq 4) 'Exact4GiB phase-only floor required'}
 Need ($record.outer_child_processes -is [long] -and $record.outer_child_processes -eq 1) 'Exactly one outer-owned helper process required'
 Need ($record.disk_gib -is [long] -and $record.disk_gib -eq 20) 'Disk floor differs'
 foreach($field in @('python_invocations','jobs','helper_child_processes')){Need ($record[$field] -is [long] -and $record[$field] -eq 0) 'Bootstrap cannot launch Python, children or Jobs'}
 foreach($field in @('automatic_retry_permitted','native_helper_compilation_admitted','scientific_admission')){Need ($record[$field] -is [bool] -and -not $record[$field]) 'Bootstrap cannot widen authority'}
 Need ($record.source_scope_path -ceq $request.source_scope_path -and $record.source_adoption_path -ceq $request.source_adoption_path -and $record.source_scope_sha256 -ceq $request.source_scope_sha256 -and $record.source_adoption_sha256 -ceq $request.source_adoption_sha256) 'Exact admitted coordination join required'
 Need ($record.source_sha256 -ceq $request.source_sha256 -and $record.source_review_sha256 -ceq $request.source_review_sha256 -and $record.owner_resource_amendment_sha256 -ceq $request.owner_resource_amendment_sha256) 'Bootstrap source/resource authority join differs'
}
foreach($record in @($peer,$admission)){Need ($record.request_sha256 -ceq $RequestSha256) 'Bootstrap request join differs'}
Need ($peer.schema -ceq 'pro2_pro3_bootstrap_observation_decision_v1' -and $peer.released -is [bool] -and $peer.released) 'Genuine fresh peer bootstrap decision required'
Need ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $request.source_sha256) 'Bootstrap source changed'
$review=Read-Metadata (Join-Path $run 'bootstrap-source-review_004.json') $request.source_review_sha256
Need ($review.schema -ceq 'cho51_p3_bootstrap_source_review_v4') 'Exact consolidated independent Source review required'
Need ($review.source_only -is [bool] -and $review.source_only -and @($review.remaining_actionable_findings).Count -eq 0 -and $review.source_sha256 -ceq $request.source_sha256) 'Different bootstrap Source review required'
$amendment=Read-Metadata (Join-Path $run 'owner-resource-amendment.json') $request.owner_resource_amendment_sha256
Need ($amendment.scope -ceq 'cho51_p3_contracts_20261027_v1_tests' -and $amendment.applies_to -ceq 'metadata_profile_mapping_and_telemetry_contract_tests_only') 'Exact new phase resource scope required'
foreach($field in @('startup_ram_gib','active_ram_gib','disk_gib')){Need ($amendment[$field] -is [long] -and $amendment[$field] -eq $request[$field]) 'Exact phase resource integer required'}
foreach($field in @('canonical_guard_modified','scientific_admission')){Need ($amendment[$field] -is [bool] -and -not $amendment[$field]) 'Canonical guard/scientific authority cannot change'}
function Utc($value,[string]$name){Need ($value[$name] -is [string] -and $value[$name] -cmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|\+00:00)$') 'Explicit UTC string required';return [DateTimeOffset]::Parse($value[$name],[Globalization.CultureInfo]::InvariantCulture)}
$start=Utc $peer 'window_start_utc';$end=Utc $peer 'window_end_utc'
foreach($record in @($peer,$admission)){Need ((Utc $record 'observed_utc') -le $entry -and (Utc $record 'observed_utc') -ge (Utc $request 'created_utc')) 'Actual bootstrap dispositions must follow this request and precede entry'}
Need ($entry -ge $start -and $entry.AddSeconds(90) -lt $end.AddSeconds(-60)) 'Whole caller and publication reserve must fit live peer window'
foreach($record in @($request,$admission)){Need ($record.window_start_utc -ceq $peer.window_start_utc -and $record.window_end_utc -ceq $peer.window_end_utc) 'Exact bootstrap window differs'}
$sourceScopeSha=$request.source_scope_sha256
$sourceAdoptionSha=$request.source_adoption_sha256
foreach($path in @($request.source_scope_path,$request.source_adoption_path)){Need ($path -is [string] -and $path.StartsWith('D:\Aenv\pro2\WORK\resume-20261027-002\coordination\',[StringComparison]::Ordinal) -and [IO.Path]::GetFullPath($path) -ceq $path) 'Direct normalized genuine peer coordination path required'}
$sourceScope=Read-Metadata $request.source_scope_path $sourceScopeSha
$sourceAdoption=Read-Metadata $request.source_adoption_path $sourceAdoptionSha
Need ($sourceAdoption.Source_only_coexistence_adopted -is [bool] -and $sourceAdoption.Source_only_coexistence_adopted -and $sourceAdoption.Source_only_scope.sha256 -ceq $sourceScopeSha) 'Genuine separate current Source adoption required'
Need ($sourceScope.Pro2_max_including_Root -is [long] -and $sourceScope.Pro2_max_including_Root -eq 3 -and $sourceScope.Pro3_max_including_Root_and_reviewer -is [long] -and $sourceScope.Pro3_max_including_Root_and_reviewer -eq 2 -and $sourceScope.shared_max_including_both_roots_and_overlap -is [long] -and $sourceScope.shared_max_including_both_roots_and_overlap -eq 5) 'current Source agent caps differ'
Need ($entry -ge (Utc $sourceScope 'interval_start') -and $entry.AddSeconds(90) -lt (Utc $sourceScope 'interval_end').AddSeconds(-60)) 'current Source finite interval and publication reserve required'
Need ($PSHOME -ceq $runtime -and (Get-Process -Id $PID).Path -ceq (Join-Path $runtime 'pwsh.exe')) 'Actual installed PowerShell root differs'
$minimumRam=[long]::MaxValue;$minimumDisk=[long]::MaxValue;$startup=[Collections.Generic.List[object]]::new()
function Floors{
 Need ($watch.Elapsed.TotalSeconds -lt 45 -and [DateTimeOffset]::UtcNow -lt $entry.AddSeconds(45)) 'Bootstrap work stop reached with caller reserve'
 $available=[long](Get-CimInstance -ClassName Win32_OperatingSystem -OperationTimeoutSec 3).FreePhysicalMemory*1024
 $disk=[IO.DriveInfo]::new('D:\').AvailableFreeSpace
 $script:minimumRam=[math]::Min($script:minimumRam,$available);$script:minimumDisk=[math]::Min($script:minimumDisk,$disk)
 Need ($available -ge 4GB -and $disk -ge 20GB) 'Bootstrap native resource floor refused'
 foreach($pausePath in $pauses){Need (-not (Present $pausePath)) 'Genuine peer pause'}
 return [ordered]@{observed_utc=[DateTimeOffset]::UtcNow.ToString('o');available_ram_bytes=$available;free_disk_bytes=$disk;method='native local CIM FreePhysicalMemory KiB and DriveInfo'}
}
foreach($name in @('bootstrap-helper-attempt_004.json','preparation-bootstrap-pins_004.json')){Need (-not (Present (Join-Path $run $name))) 'Bootstrap output already used'}
Write-New (Join-Path $run 'bootstrap-helper-attempt_004.json') ([ordered]@{schema='cho51_p3_bootstrap_attempt_v1';observed_utc=[DateTimeOffset]::UtcNow.ToString('o');request_sha256=$RequestSha256;root_admission_sha256=$RootAdmissionSha256;maximum_seconds=90;automatic_retry_permitted=$false;scientific_admission=$false})
$startup.Add((Floors));[Threading.Thread]::Sleep(200);$startup.Add((Floors))
$files=[ordered]@{};$total=[long]0;$enumerated=0
$options=[IO.EnumerationOptions]::new();$options.RecurseSubdirectories=$true;$options.MaxRecursionDepth=16;$options.IgnoreInaccessible=$false;$options.AttributesToSkip=[IO.FileAttributes]::ReparsePoint
$enumerator=[IO.Directory]::EnumerateFileSystemEntries($runtime,'*',$options).GetEnumerator()
try{while($enumerator.MoveNext()){
 $enumerated++;Need ($enumerated -le 10000 -and $watch.Elapsed.TotalSeconds -lt 45 -and [DateTimeOffset]::UtcNow -lt $entry.AddSeconds(45)) 'Bootstrap enumeration bound exceeded'
 $file=Get-Item -LiteralPath $enumerator.Current
 if($file.PSIsContainer){continue}
 if($file.Extension.ToLowerInvariant() -notin @('.dll','.exe','.json','.ps1','.psm1','.psd1')){continue}
 [void](Floors)
 Need ($files.Count -lt 2500 -and ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'Bounded direct bootstrap runtime inventory required'
 $before=Get-Item -LiteralPath $file.FullName
 $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 try{
  Need ($stream.Length -eq $before.Length -and $total+$stream.Length -le 1GB) 'Bootstrap aggregate byte cap refused'
  $digest=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
  try{
   $buffer=[byte[]]::new(65536);$counted=[long]0;$sinceFloor=[long]0
   while($true){
    Need ($watch.Elapsed.TotalSeconds -lt 45 -and [DateTimeOffset]::UtcNow -lt $entry.AddSeconds(45)) 'Bootstrap read deadline reached'
    $read=$stream.Read($buffer,0,$buffer.Length);if($read -eq 0){break}
    $counted+=$read;$sinceFloor+=$read;Need ($counted -le $before.Length) 'Bootstrap file grew'
    $digest.AppendData($buffer,0,$read);if($sinceFloor -ge 4MB){[void](Floors);$sinceFloor=0}
   }
   $after=Get-Item -LiteralPath $file.FullName
   Need ($counted -eq $before.Length -and $after.Length -eq $before.Length -and $after.LastWriteTimeUtc.Ticks -eq $before.LastWriteTimeUtc.Ticks) 'Bootstrap metadata changed while hashing'
   $files[$file.FullName]=[ordered]@{sha256=[Convert]::ToHexString($digest.GetHashAndReset()).ToLowerInvariant();bytes=$counted}
   $total+=$counted
  }finally{$digest.Dispose()}
 }finally{$stream.Dispose()}
}}finally{$enumerator.Dispose()}
[void](Floors)
$result=[ordered]@{schema='cho51_p3_powershell_bootstrap_observation_v1';scope=$scope;observed_utc=[DateTimeOffset]::UtcNow.ToString('o');request_sha256=$RequestSha256;root_admission_sha256=$RootAdmissionSha256;peer_decision_path=$admission.peer_decision_path;peer_decision_sha256=$admission.peer_decision_sha256;source_sha256=$request.source_sha256;source_review_sha256=$request.source_review_sha256;runtime_root=$runtime;files=$files;file_count=$files.Count;code_bytes=$total;elapsed_seconds=$watch.Elapsed.TotalSeconds;startup_samples=@($startup);minimum_available_ram_bytes=$minimumRam;minimum_free_disk_bytes=$minimumDisk;native_same_handle_identity_verified=$false;full_pro3_pins_created=$false;python_executed=$false;child_process_started=$false;job_created=$false;native_helper_compiled=$false;scientific_admission=$false}
Write-New (Join-Path $run 'preparation-bootstrap-pins_004.json') $result
Effect-Clock
[ordered]@{passed=$true;file_count=$files.Count;code_bytes=$total;elapsed_seconds=$watch.Elapsed.TotalSeconds;full_caller_release_still_requires_external_evidence=$true;python_executed=$false;native_helper_compiled=$false;scientific_admission=$false}|ConvertTo-Json -Compress
