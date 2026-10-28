param(
 [Parameter(Mandatory)][ValidateSet('Begin','Invoke','Complete','Release')][string]$Mode,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$RequestSha256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$RootAdmissionSha256,
 [long]$ExternalEntryQpc=0,
 [string]$ExternalEntryUtc='',
 [long]$ExternalFrequency=0,
 [string]$InvokeToolCallId='',
 [Nullable[int]]$BeginToolExitCode=$null,
 [Nullable[int]]$InvokeToolExitCode=$null,
 [Nullable[int]]$CompleteToolExitCode=$null
)
$ErrorActionPreference='Stop'
$modeEntryQpc=[Diagnostics.Stopwatch]::GetTimestamp()
$modeEntryUtc=[DateTimeOffset]::UtcNow
$frequency=[Diagnostics.Stopwatch]::Frequency
$run='D:\Aenv\pro3\runs\coordination\cho51_p3_contracts_20261027_v1'
$runtime='C:\Users\aladdin-alyanai\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell'
$scope='cho51_p3_contracts_20261027_v1_bootstrap_observation_004'
$scopeSha='';$adoptionSha=''
$amendmentSha='733d6505fb24ee552ae0abd7e1bec46c14f6fc33e66a71d1adb3cf2f30c9fe75'
$pausePaths=@('20261007','20261012','20261013','20261015','20261025')|ForEach-Object{"D:\Aenv\pro2\WORK\resume-$_-001\coordination\PRO2_REQUEST_PRO3_PAUSE.json"}
$outputNames=@('bootstrap-dispatch_004.json','bootstrap-attempt_004.json','bootstrap-supervision_004.json','bootstrap-stdout_004.txt','bootstrap-stderr_004.txt','bootstrap-caller-completion_004.json','bootstrap-release_004.json','bootstrap-failure_004.json','bootstrap-helper-attempt_004.json','preparation-bootstrap-pins_004.json')
$held=[Collections.Generic.Dictionary[string,IO.FileStream]]::new([StringComparer]::Ordinal)
$commonQpc=$modeEntryQpc;$commonUtc=$modeEntryUtc
$windowStart=$null;$windowEnd=$null;$sourceEnd=$null
$authenticated=$false;$dispatch=$null;$process=$null;$safeHandle=$null;$handleRef=$false
$childStarted=$false;$childReaped=$false;$custodyClosed=($Mode -cin @('Begin','Invoke'));$childId=0;$childStartTicks=0
$startAttempted=$false;$startOutcome=if($custodyClosed){'not_attempted'}else{'unknown'}
$minimumRam=[long]::MaxValue;$minimumDisk=[long]::MaxValue
$failure=$null;$stdout=$null;$stderr=$null
$cleanupOnly=($Mode -cin @('Complete','Release'))
$closureGuardPassed=$true;$closureGuardRefusal=$null
$lastFloorQpc=[long]0
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
function Utc([string]$value){
 Need ($value -cmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|\+00:00)$') 'Explicit UTC required'
 return [DateTimeOffset]::Parse($value,[Globalization.CultureInfo]::InvariantCulture)
}
function Seconds{
 $nowQpc=[Diagnostics.Stopwatch]::GetTimestamp()
 Need ($nowQpc -ge $commonQpc -and $frequency -gt 0) 'Monotonic clock regression'
 return ($nowQpc-$commonQpc)/[double]$frequency
}
function Clock([double]$limit=85,[bool]$checkPauses=(-not $script:cleanupOnly)){
 $now=[DateTimeOffset]::UtcNow
 Need ((Seconds) -lt $limit -and $now -ge $commonUtc -and $now -lt $commonUtc.AddSeconds($limit)) 'Common caller deadline reached'
 if($null -ne $windowStart){Need ($now -ge $windowStart -and $now -lt $windowEnd.AddSeconds(-60)) 'Strict peer publication reserve reached'}
 if($null -ne $sourceEnd){Need ($now -lt $sourceEnd.AddSeconds(-60)) 'Strict Source publication reserve reached'}
 if($checkPauses){foreach($pausePath in $pausePaths){Need (-not (Present $pausePath)) 'Peer pause requested'}}
}
function Floor([double]$limit=65){
 Clock $limit $true
 $rows=@(Get-CimInstance -ClassName Win32_OperatingSystem -OperationTimeoutSec 3)
 Need ($rows.Count -eq 1) 'One local resource observation required'
 $available=[long]$rows[0].FreePhysicalMemory*1024
 $disk=[IO.DriveInfo]::new('D:\').AvailableFreeSpace
 $script:minimumRam=[math]::Min($script:minimumRam,$available)
 $script:minimumDisk=[math]::Min($script:minimumDisk,$disk)
 $script:lastFloorQpc=[Diagnostics.Stopwatch]::GetTimestamp()
 Clock $limit $true
 Need ($available -ge 4GB -and $disk -ge 20GB) 'Active resource floor refused'
 return [ordered]@{observed_utc=[DateTimeOffset]::UtcNow.ToString('o');available_ram_bytes=$available;free_disk_bytes=$disk}
}
function Input-Guard{
 Clock
 if(([Diagnostics.Stopwatch]::GetTimestamp()-$lastFloorQpc)/[double]$frequency -ge 1){
  if($cleanupOnly){try{[void](Floor 85)}catch{$script:closureGuardPassed=$false;$script:closureGuardRefusal=$_.Exception.Message}}
  else{[void](Floor)}
 }
}
function Bytes([string]$path,[string]$expected,[long]$maximum=1048576,[bool]$retain=$false){
 Input-Guard
 Need ($expected -cmatch '^[0-9a-f]{64}$' -and [IO.Path]::IsPathFullyQualified($path)) 'Exact independent file pin required'
 $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 $keep=$false
 try{
  Need ($stream.Length -gt 0 -and $stream.Length -le $maximum) 'Bounded nonempty control file required'
  $raw=[byte[]]::new([int]$stream.Length);$offset=0
  while($offset -lt $raw.Length){
   Input-Guard
   $disk=[IO.DriveInfo]::new('D:\').AvailableFreeSpace
   Need ($disk -ge 20GB) 'Read disk floor refused'
   $count=$stream.Read($raw,$offset,[math]::Min(65536,$raw.Length-$offset))
   Need ($count -gt 0) 'Truncated pinned input'
   $offset+=$count
   Clock
  }
  Need ($stream.ReadByte() -eq -1) 'Pinned input grew'
  Need ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -ceq $expected) 'Independent input SHA differs'
  if($retain){Need (-not $held.ContainsKey($path)) 'Duplicate retained input';$held.Add($path,$stream);$keep=$true}
  return ,$raw
 }finally{if(-not $keep){$stream.Dispose()}}
}
function Parse([byte[]]$raw){
 $document=[Text.Json.JsonDocument]::Parse([ReadOnlyMemory[byte]]::new($raw))
 try{
  $script:jsonNodes=0
  function Inspect($element,[int]$depth){
   $script:jsonNodes++;Need ($depth -le 32 -and $script:jsonNodes -le 50000) 'Bounded JSON graph required'
   if($element.ValueKind -eq [Text.Json.JsonValueKind]::Object){
    $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach($property in $element.EnumerateObject()){Need ($names.Add($property.Name)) 'Duplicate JSON property';Inspect $property.Value ($depth+1)}
   }elseif($element.ValueKind -eq [Text.Json.JsonValueKind]::Array){foreach($item in $element.EnumerateArray()){Inspect $item ($depth+1)}}
   elseif($element.ValueKind -eq [Text.Json.JsonValueKind]::Number){$number=$element.GetDouble();Need (-not [double]::IsInfinity($number) -and -not [double]::IsNaN($number)) 'Finite JSON number required'}
  }
  Inspect $document.RootElement 0
 }finally{$document.Dispose()}
 return ,([Text.UTF8Encoding]::new($false,$true).GetString($raw)|ConvertFrom-Json -AsHashtable -DateKind String)
}
function Metadata([string]$name,[string]$expected,[bool]$retain=$false){return ,(Parse (Bytes (Join-Path $run $name) $expected 1048576 $retain))}
function Hash([byte[]]$raw){return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()}
function Existing([string]$name){
 Clock
 $path=Join-Path $run $name
 $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 try{
  Need ($stream.Length -gt 0 -and $stream.Length -le 1048576) 'Bounded existing receipt required'
  $raw=[byte[]]::new([int]$stream.Length);$stream.ReadExactly($raw)
  Clock
  return [ordered]@{value=(Parse $raw);sha256=(Hash $raw)}
 }finally{$stream.Dispose()}
}
function Closed($value,[string[]]$fields){
 Need ($value -is [Collections.IDictionary] -and $value.Count -eq $fields.Count) 'Closed receipt fields required'
 foreach($field in $fields){Need ($value.Contains($field)) 'Required receipt field missing'}
}
function Write-New([string]$name,$value,[double]$limit=85){
 Need ($name -cin $outputNames) 'Unowned output refused'
 Clock $limit
 $raw=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 16 -Compress)+[char]10)
 Need ($raw.Length -le 1048576) 'Bounded output required'
 Clock $limit
 $stream=[IO.File]::Open((Join-Path $run $name),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 Clock $limit
 [void](Bytes (Join-Path $run $name) (Hash $raw))
 Clock $limit
 if($cleanupOnly -and $value.Contains('operation_succeeded') -and $value.operation_succeeded){Need ($closureGuardPassed) 'Closure guard changed during publication; no accepted pass'}
 return (Hash $raw)
}
function Write-Stream([string]$name,[byte[]]$raw){
 Need ($name -cin @('bootstrap-stdout_004.txt','bootstrap-stderr_004.txt') -and $raw.Length -le 1048576) 'Bounded owned stream required'
 Clock 85
 $stream=[IO.File]::Open((Join-Path $run $name),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 Clock 85
 $read=[IO.File]::OpenRead((Join-Path $run $name))
 try{Need ($read.Length -eq $raw.Length) 'Stream readback size differs';$copy=[byte[]]::new($raw.Length);$read.ReadExactly($copy);Need ((Hash $copy) -ceq (Hash $raw)) 'Stream readback SHA differs'}finally{$read.Dispose()}
 Clock 85
 return [ordered]@{path=(Join-Path $run $name);bytes=$raw.Length;sha256=(Hash $raw)}
}
function Common([string]$schema){return [ordered]@{schema=$schema;scope=$scope;observed_utc=[DateTimeOffset]::UtcNow.ToString('o');request_sha256=$RequestSha256;root_admission_sha256=$RootAdmissionSha256;scientific_admission=$false}}
function Receipt($value,[string]$schema){
 Need ($value.schema -ceq $schema -and $value.scope -ceq $scope -and $value.request_sha256 -ceq $RequestSha256 -and $value.root_admission_sha256 -ceq $RootAdmissionSha256) 'Receipt authority join differs'
 Need ($value.scientific_admission -is [bool] -and -not $value.scientific_admission) 'No scientific admission permitted'
}
function Drain-New($stream){return [ordered]@{stream=$stream;buffer=[byte[]]::new(65536);data=[IO.MemoryStream]::new();task=$null;eof=$false}}
function Drain-Poll($state){
 for($iteration=0;$iteration -lt 16 -and -not $state.eof;$iteration++){
  if($null -eq $state.task){$state.task=$state.stream.ReadAsync($state.buffer,0,$state.buffer.Length)}
  if(-not $state.task.IsCompleted){break}
  $count=$state.task.GetAwaiter().GetResult();$state.task=$null
  if($count -eq 0){$state.eof=$true;break}
  Need ($state.data.Length+$count -le 1048576) 'Helper output exceeded one MiB'
  $state.data.Write($state.buffer,0,$count)
 }
}
function Original-Handle{
 Need ($null -ne $process -and $startAttempted) 'Only the exact Start-attempted Process may be inspected'
 $flags=[Reflection.BindingFlags]'Instance,NonPublic'
 $haveField=[Diagnostics.Process].GetField('_haveProcessHandle',$flags)
 $handleField=[Diagnostics.Process].GetField('_processHandle',$flags)
 Need ($null -ne $haveField -and $null -ne $handleField) 'Pinned retained-handle implementation fields required'
 $have=$haveField.GetValue($process)
 Need ($have -is [bool] -and $have) 'Original Start-owned process handle is not established'
 $original=$handleField.GetValue($process)
 Need ($original -is [Microsoft.Win32.SafeHandles.SafeProcessHandle] -and -not $original.IsClosed -and -not $original.IsInvalid) 'Valid original Start-owned handle required'
 if($null -eq $safeHandle){$script:safeHandle=$original;$script:safeHandle.DangerousAddRef([ref]$script:handleRef);$script:handleValue=$script:safeHandle.DangerousGetHandle()}
 Need ([object]::ReferenceEquals($original,$safeHandle) -and $original.DangerousGetHandle() -eq $handleValue) 'Original retained handle changed'
}
function Identity{
 Original-Handle
 Need ($childStarted -and $childId -gt 0 -and $childStartTicks -gt 0 -and $process.Id -eq $childId -and $process.StartTime.ToUniversalTime().Ticks -eq $childStartTicks) 'Retained process generation differs'
}
function Cleanup-Identity{
 Original-Handle
 if($childId -gt 0){Need ($process.Id -eq $childId) 'Owned process PID changed'}
 if($childStartTicks -gt 0){Need ($process.StartTime.ToUniversalTime().Ticks -eq $childStartTicks) 'Owned process generation changed'}
}
function Child-Table{
 Clock 80 $false
 try{
  $count=0;$seenHelper=$false
  foreach($parentId in @($PID,$childId)){
   foreach($row in Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId = $parentId" -OperationTimeoutSec 3){
    $count++;Need ($count -le 64) 'Process table row cap exceeded'
    Need ($parentId -eq $PID -and [long]$row.ProcessId -eq $childId -and [long]$row.ParentProcessId -eq $PID) 'Unexpected descendant; no authority to kill it'
    Need ($row.CreationDate -is [datetime] -and [math]::Abs($row.CreationDate.ToUniversalTime().Ticks-$childStartTicks) -le 10000) 'CIM helper generation differs'
    $seenHelper=$true
   }
  }
  Need ($process.HasExited -or $seenHelper) 'Live retained helper missing from process table'
  Clock 80 $false
 }catch{$script:custodyClosed=$false;throw}
}
try{
 Need ($PSScriptRoot -ceq $run -and $PSCommandPath -ceq (Join-Path $run 'bootstrap-supervise_004.ps1')) 'Exact supervisor Source path required'
 if($Mode -ceq 'Begin'){
  Need ($ExternalFrequency -eq $frequency -and $ExternalEntryQpc -gt 0 -and $ExternalEntryQpc -le $modeEntryQpc) 'Fresh external pre-dispatch QPC required'
  $commonUtc=Utc $ExternalEntryUtc;$commonQpc=$ExternalEntryQpc
  Need (($modeEntryQpc-$commonQpc)/[double]$frequency -lt 5 -and $modeEntryUtc -ge $commonUtc -and $modeEntryUtc -lt $commonUtc.AddSeconds(5)) 'External pre-dispatch observation is stale'
 }else{
  Need ($ExternalEntryQpc -eq 0 -and $ExternalEntryUtc -ceq '' -and $ExternalFrequency -eq 0) 'Only Begin accepts external entry'
  $dispatchRef=Existing 'bootstrap-dispatch_004.json';$dispatch=$dispatchRef.value
  Closed $dispatch @('schema','scope','observed_utc','request_sha256','root_admission_sha256','scientific_admission','external_entry_qpc','external_entry_utc','qpc_frequency','begin_entry_qpc','begin_entry_utc','maximum_seconds','caller_return_observed','automatic_retry_permitted')
  Receipt $dispatch 'cho51_p3_bootstrap_dispatch_v4'
  Need ($dispatch.external_entry_qpc -is [long] -and $dispatch.qpc_frequency -is [long] -and $dispatch.qpc_frequency -eq $frequency -and $dispatch.maximum_seconds -is [long] -and $dispatch.maximum_seconds -eq 90 -and $dispatch.caller_return_observed -is [bool] -and -not $dispatch.caller_return_observed -and $dispatch.automatic_retry_permitted -is [bool] -and -not $dispatch.automatic_retry_permitted) 'Exact common dispatch clock required'
  $commonQpc=$dispatch.external_entry_qpc;$commonUtc=Utc $dispatch.external_entry_utc
 }
 Clock
 $request=Metadata 'bootstrap-request_004.json' $RequestSha256 $true
 $scopeSha=$request.source_scope_sha256;$adoptionSha=$request.source_adoption_sha256
 foreach($path in @($request.source_scope_path,$request.source_adoption_path)){Need ($path -is [string] -and $path.StartsWith('D:\Aenv\pro2\WORK\resume-20261027-002\coordination\',[StringComparison]::Ordinal) -and [IO.Path]::GetFullPath($path) -ceq $path) 'Direct normalized genuine peer coordination path required'}
 $admission=Metadata 'bootstrap-admission_004.json' $RootAdmissionSha256 $true
 Need ($request.schema -ceq 'cho51_p3_bootstrap_observation_request_v1' -and $admission.schema -ceq 'cho51_p3_bootstrap_observation_admission_v1' -and $admission.accepted -is [bool] -and $admission.accepted) 'Exact fresh Root admission required'
 Need ($admission.peer_decision_path -is [string] -and $admission.peer_decision_path.StartsWith('D:\Aenv\pro2\WORK\resume-20261027-002\coordination\',[StringComparison]::Ordinal) -and [IO.Path]::GetFullPath($admission.peer_decision_path) -ceq $admission.peer_decision_path) 'Direct normalized actual Pro2 peer decision path required'
 $peer=Parse (Bytes $admission.peer_decision_path $admission.peer_decision_sha256 1048576 $true)
 Need ($peer.schema -ceq 'pro2_pro3_bootstrap_observation_decision_v1' -and $peer.released -is [bool] -and $peer.released) 'Genuine explicit peer bootstrap grant required'
 foreach($record in @($request,$admission,$peer)){
  Need ($record.scope -ceq $scope -and $record.source_scope_path -ceq $request.source_scope_path -and $record.source_adoption_path -ceq $request.source_adoption_path) 'Exact bootstrap004 scope and coordination paths required'
  foreach($field in @('source_sha256','supervisor_sha256','protocol_sha256','source_review_sha256','owner_resource_amendment_sha256','source_scope_sha256','source_adoption_sha256','runtime_executable_sha256','process_dll_sha256')){Need ($record[$field] -is [string] -and $record[$field] -ceq $request[$field] -and $record[$field] -cmatch '^[0-9a-f]{64}$') 'Exact admitted Source/runtime join required'}
  foreach($pair in @(@('maximum_seconds',90),@('maximum_files',2500),@('maximum_code_bytes',1073741824),@('maximum_enumerated_entries',10000),@('maximum_directory_depth',16),@('maximum_manifest_bytes',1048576),@('startup_ram_gib',4),@('active_ram_gib',4),@('disk_gib',20),@('outer_child_processes',1),@('helper_child_processes',0),@('python_invocations',0),@('jobs',0),@('publication_reserve_seconds',60))){Need ($record[$pair[0]] -is [long] -and $record[$pair[0]] -eq $pair[1]) 'Exact integer admission cap required'}
  foreach($field in @('automatic_retry_permitted','native_helper_compilation_admitted','scientific_admission')){Need ($record[$field] -is [bool] -and -not $record[$field]) 'Admission cannot widen scope'}
  Need ($record.bounded_cleanup_after_pause_admitted -is [bool] -and $record.bounded_cleanup_after_pause_admitted) 'Explicit bounded cleanup-only publication authority required'
  $zeroFields=@('source_updates','restore_count','support_updates','gradient_updates','target_inference_calls','query_count','model_constructions','measured_cells')
  Closed $record.expected_numerical_budget $zeroFields
  foreach($field in $zeroFields){Need ($record.expected_numerical_budget[$field] -is [long] -and $record.expected_numerical_budget[$field] -eq 0) 'Exact zero numerical budget required'}
  Need ($record.window_start_utc -ceq $request.window_start_utc -and $record.window_end_utc -ceq $request.window_end_utc) 'Exact peer/Root/request window required'
 }
 foreach($record in @($peer,$admission)){Need ($record.request_sha256 -ceq $RequestSha256 -and (Utc $record.observed_utc) -le $commonUtc -and (Utc $record.observed_utc) -ge (Utc $request.created_utc)) 'Actual decisions must follow this request and predate external dispatch'}
 $windowStart=Utc $request.window_start_utc;$windowEnd=Utc $request.window_end_utc
 $sourceScope=Parse (Bytes $request.source_scope_path $scopeSha)
 $sourceAdoption=Parse (Bytes $request.source_adoption_path $adoptionSha)
 $sourceEnd=Utc $sourceScope.interval_end
 Need ($request.source_scope_sha256 -ceq $scopeSha -and $request.source_adoption_sha256 -ceq $adoptionSha -and $sourceAdoption.Source_only_coexistence_adopted -is [bool] -and $sourceAdoption.Source_only_coexistence_adopted -and $sourceAdoption.Source_only_scope.sha256 -ceq $scopeSha) 'Actual current Source authority required'
 foreach($pair in @(@('Pro2_max_including_Root',3),@('Pro3_max_including_Root_and_reviewer',2),@('shared_max_including_both_roots_and_overlap',5))){Need ($sourceScope[$pair[0]] -is [long] -and $sourceScope[$pair[0]] -eq $pair[1]) 'current Source concurrency caps differ'}
 Need ($commonUtc -ge $windowStart -and $commonUtc -ge (Utc $sourceScope.interval_start) -and $commonUtc.AddSeconds(90) -lt $windowEnd.AddSeconds(-60) -and $commonUtc.AddSeconds(90) -lt $sourceEnd.AddSeconds(-60)) 'External whole caller and strict reserve must fit both windows'
 Clock
 Need ($request.output_root -ceq $run -and @($request.create_once_outputs).Count -eq $outputNames.Count) 'Exact owned output namespace required'
 for($index=0;$index -lt $outputNames.Count;$index++){Need ($request.create_once_outputs[$index] -ceq $outputNames[$index]) 'Exact ordered output names required'}
 Need ($request.runtime_root -ceq $runtime -and $PSHOME -ceq $runtime -and [Environment]::ProcessPath -ceq (Join-Path $runtime 'pwsh.exe')) 'Exact installed PowerShell process required'
 Need ($request.owner_resource_amendment_sha256 -ceq $amendmentSha) 'Exact fresh human resource amendment required'
 $amendment=Metadata 'owner-resource-amendment.json' $amendmentSha
 Need ($amendment.scope -ceq 'cho51_p3_contracts_20261027_v1_tests' -and $amendment.applies_to -ceq 'metadata_profile_mapping_and_telemetry_contract_tests_only') 'Phase-only resource amendment required'
 foreach($pair in @(@('startup_ram_gib',4),@('active_ram_gib',4),@('disk_gib',20))){Need ($amendment[$pair[0]] -is [long] -and $amendment[$pair[0]] -eq $pair[1]) 'Resource amendment cap differs'}
 foreach($field in @('canonical_guard_modified','scientific_admission')){Need ($amendment[$field] -is [bool] -and -not $amendment[$field]) 'Canonical/scientific guard cannot change'}
 $review=Metadata 'bootstrap-source-review_004.json' $request.source_review_sha256
 Need ($review.schema -ceq 'cho51_p3_bootstrap_source_review_v4' -and $review.source_only -is [bool] -and $review.source_only -and @($review.remaining_actionable_findings).Count -eq 0 -and $review.source_sha256 -ceq $request.source_sha256 -and $review.files.Count -eq 3) 'Exact clean consolidated three-Source review required'
 foreach($pair in @(@('bootstrap-observation_004.ps1','source_sha256'),@('bootstrap-supervise_004.ps1','supervisor_sha256'),@('bootstrap-protocol_004.md','protocol_sha256'))){
  $path=Join-Path $run $pair[0]
  Need ($review.files[$path] -ceq $request[$pair[1]]) 'Composite Source map differs'
  [void](Bytes $path $request[$pair[1]] 1048576 $true)
 }
 [void](Bytes (Join-Path $runtime 'pwsh.exe') $request.runtime_executable_sha256 1048576 $true)
 Need ($request.process_dll_sha256 -ceq '2b4871e02b366113c6ccf3b1436fadde5e69fc0a3e3ac421e2fa0f7af8c2bc3b') 'Source-reviewed retained-handle Kill implementation pin differs'
 Need ([Diagnostics.Process].Assembly.Location -ceq (Join-Path $runtime 'System.Diagnostics.Process.dll')) 'Actual retained-handle Process implementation differs'
 [void](Bytes (Join-Path $runtime 'System.Diagnostics.Process.dll') $request.process_dll_sha256 1048576 $true)
 $authenticated=$true
 if($cleanupOnly){try{[void](Floor 85)}catch{$closureGuardPassed=$false;$closureGuardRefusal=$_.Exception.Message}}
 else{[void](Floor)}
 if($Mode -ceq 'Begin'){
  foreach($name in $outputNames){Need (-not (Present (Join-Path $run $name))) 'Bootstrap004 namespace already used'}
  $record=Common 'cho51_p3_bootstrap_dispatch_v4'
  $record.external_entry_qpc=$commonQpc;$record.external_entry_utc=$commonUtc.ToString('o');$record.qpc_frequency=$frequency
  $record.begin_entry_qpc=$modeEntryQpc;$record.begin_entry_utc=$modeEntryUtc.ToString('o');$record.maximum_seconds=90
  $record.caller_return_observed=$false;$record.automatic_retry_permitted=$false
  [void](Write-New 'bootstrap-dispatch_004.json' $record 65)
 }elseif($Mode -ceq 'Invoke'){
  Need ($null -ne $BeginToolExitCode -and $BeginToolExitCode -eq 0) 'Actual successful Begin tool exit required before child launch'
  foreach($name in $outputNames|Where-Object{$_ -cne 'bootstrap-dispatch_004.json'}){Need (-not (Present (Join-Path $run $name))) 'Once-only invocation output already used'}
  $attempt=Common 'cho51_p3_bootstrap_attempt_v4';$attempt.dispatch_sha256=$dispatchRef.sha256;$attempt.helper_invocations=0;$attempt.automatic_retry_permitted=$false
  [void](Write-New 'bootstrap-attempt_004.json' $attempt 65)
  $samples=[Collections.Generic.List[object]]::new();$samples.Add((Floor));[Threading.Thread]::Sleep(200);$samples.Add((Floor))
  Need ((Seconds) -lt 15) 'Insufficient helper work and cleanup reserve'
  $startInfo=[Diagnostics.ProcessStartInfo]::new();$startInfo.FileName=Join-Path $runtime 'pwsh.exe';$startInfo.WorkingDirectory='D:\Aenv\pro3'
  $startInfo.UseShellExecute=$false;$startInfo.CreateNoWindow=$true;$startInfo.RedirectStandardOutput=$true;$startInfo.RedirectStandardError=$true
  foreach($argument in @('-NoProfile','-NonInteractive','-File',(Join-Path $run 'bootstrap-observation_004.ps1'),'-RequestSha256',$RequestSha256,'-RootAdmissionSha256',$RootAdmissionSha256)){[void]$startInfo.ArgumentList.Add($argument)}
  Clock 65
  $process=[Diagnostics.Process]::new();$process.StartInfo=$startInfo
  $startAttempted=$true;$startOutcome='unknown';$custodyClosed=$false
  Need ($process.Start()) 'Owned helper launch failed or uncertain'
  $childStarted=$true;Original-Handle
  $childId=$process.Id;$childStartTicks=$process.StartTime.ToUniversalTime().Ticks
  Identity
  $startOutcome='started';$custodyClosed=$true
  $stdout=Drain-New $process.StandardOutput.BaseStream;$stderr=Drain-New $process.StandardError.BaseStream
  Child-Table
  $nextFloor=Seconds;$nextTable=Seconds
  while(-not $process.HasExited){
   Clock 65
   Identity;Drain-Poll $stdout;Drain-Poll $stderr
   if((Seconds) -ge $nextFloor){[void](Floor);$nextFloor=(Seconds)+1}
   if((Seconds) -ge $nextTable){Child-Table;$nextTable=(Seconds)+1}
   [Threading.Thread]::Sleep(20)
  }
  $childReaped=$process.WaitForExit(0)
  Need ($childReaped -and $process.ExitCode -eq 0) 'Helper failed or unreaped'
  while((-not $stdout.eof -or -not $stderr.eof) -and (Seconds) -lt 80){Clock 80;Drain-Poll $stdout;Drain-Poll $stderr;[Threading.Thread]::Sleep(10)}
  Need ($stdout.eof -and $stderr.eof) 'Both stream EOF receipts required'
  Child-Table
  $stdoutRef=Write-Stream 'bootstrap-stdout_004.txt' $stdout.data.ToArray();$stderrRef=Write-Stream 'bootstrap-stderr_004.txt' $stderr.data.ToArray()
  $helperAttempt=Existing 'bootstrap-helper-attempt_004.json';$manifest=Existing 'preparation-bootstrap-pins_004.json'
  Need ($manifest.value.schema -ceq 'cho51_p3_powershell_bootstrap_observation_v1' -and $manifest.value.scope -ceq $scope -and $manifest.value.request_sha256 -ceq $RequestSha256 -and $manifest.value.root_admission_sha256 -ceq $RootAdmissionSha256) 'Helper observational output join differs'
  $record=Common 'cho51_p3_bootstrap_supervision_v4'
  $record.dispatch_sha256=$dispatchRef.sha256;$record.attempt_sha256=(Existing 'bootstrap-attempt_004.json').sha256
  $record.helper_attempt_sha256=$helperAttempt.sha256;$record.manifest_sha256=$manifest.sha256;$record.helper_pid=$childId;$record.helper_creation_utc_ticks=$childStartTicks
  $record.start_attempted=$startAttempted;$record.start_outcome=$startOutcome
  $record.helper_invocations=1;$record.helper_exit_code=$process.ExitCode;$record.helper_reaped=$childReaped;$record.custody_closed=$custodyClosed
  $record.stdout=$stdoutRef;$record.stderr=$stderrRef;$record.stdout_eof=$stdout.eof;$record.stderr_eof=$stderr.eof
  $record.startup_samples=@($samples);$record.minimum_available_ram_bytes=$minimumRam;$record.minimum_free_disk_bytes=$minimumDisk
  $record.elapsed_seconds=Seconds;$record.caller_return_observed=$false;$record.full_caller_accepted=$false;$record.observational_manifest_accepted=$false
  [void](Write-New 'bootstrap-supervision_004.json' $record 85)
 }elseif($Mode -ceq 'Complete'){
  Need ($InvokeToolCallId.Length -gt 0 -and $InvokeToolCallId.Length -le 256 -and $InvokeToolCallId -notmatch '[\r\n]') 'Actual completed Invoke tool identity required'
  Need ($null -ne $InvokeToolExitCode) 'Actual completed Invoke tool exit required'
  $supervisionSha=$null;$failureSha=$null;$operationSucceeded=$false;$operationCustody=$false
  $operationAttempted=$false;$operationOutcome='unknown'
  if((Present (Join-Path $run 'bootstrap-failure_004.json'))){
   $failureRef=Existing 'bootstrap-failure_004.json';$failureRecord=$failureRef.value
   Receipt $failureRecord 'cho51_p3_bootstrap_failure_v4'
   Closed $failureRecord @('schema','scope','observed_utc','request_sha256','root_admission_sha256','scientific_admission','mode','failure','start_attempted','start_outcome','child_started','child_pid','child_reaped','custody_closed','stdout_eof','stderr_eof','stdout','stderr','partial_outputs_preserved','automatic_retry_permitted','full_caller_accepted')
   foreach($field in @('child_started','child_reaped','custody_closed','stdout_eof','stderr_eof')){Need ($failureRecord[$field] -is [bool]) 'Exact failure custody booleans required'}
   Need ($failureRecord.start_attempted -is [bool] -and $failureRecord.start_outcome -cin @('not_attempted','unknown','started')) 'Explicit failure start state required'
   $operationAttempted=$failureRecord.start_attempted;$operationOutcome=$failureRecord.start_outcome
   $operationCustody=$failureRecord.custody_closed -and $operationOutcome -cne 'unknown' -and ((-not $operationAttempted -and $operationOutcome -ceq 'not_attempted') -or ($operationAttempted -and $operationOutcome -ceq 'started' -and $failureRecord.child_started -and $failureRecord.child_reaped -and $failureRecord.stdout_eof -and $failureRecord.stderr_eof))
   $failureSha=$failureRef.sha256
  }else{
   $supervisionRef=Existing 'bootstrap-supervision_004.json';$supervision=$supervisionRef.value
   Receipt $supervision 'cho51_p3_bootstrap_supervision_v4'
   Closed $supervision @('schema','scope','observed_utc','request_sha256','root_admission_sha256','scientific_admission','dispatch_sha256','attempt_sha256','helper_attempt_sha256','manifest_sha256','helper_pid','helper_creation_utc_ticks','start_attempted','start_outcome','helper_invocations','helper_exit_code','helper_reaped','custody_closed','stdout','stderr','stdout_eof','stderr_eof','startup_samples','minimum_available_ram_bytes','minimum_free_disk_bytes','elapsed_seconds','caller_return_observed','full_caller_accepted','observational_manifest_accepted')
   foreach($field in @('helper_reaped','custody_closed','stdout_eof','stderr_eof')){Need ($supervision[$field] -is [bool] -and $supervision[$field]) 'Incomplete custody cannot complete successfully'}
   Need ($supervision.dispatch_sha256 -ceq $dispatchRef.sha256 -and $supervision.helper_invocations -is [long] -and $supervision.helper_invocations -eq 1 -and $supervision.helper_exit_code -is [long] -and $supervision.helper_exit_code -eq 0) 'Failed/partial operation cannot pass'
   Need ($supervision.start_attempted -is [bool] -and $supervision.start_attempted -and $supervision.start_outcome -ceq 'started') 'Successful retained start state required'
   $operationAttempted=$true;$operationOutcome='started'
   $supervisionSha=$supervisionRef.sha256;$operationSucceeded=$true;$operationCustody=$true
  }
  $record=Common 'cho51_p3_bootstrap_caller_completion_v4';$record.dispatch_sha256=$dispatchRef.sha256;$record.supervision_sha256=$supervisionSha;$record.failure_sha256=$failureSha
  $record.invoke_tool_call_id=$InvokeToolCallId;$record.post_invoke_return_upper_bound_qpc=$modeEntryQpc;$record.post_invoke_return_upper_bound_utc=$modeEntryUtc.ToString('o')
  $record.invoke_tool_exit_code=[int]$InvokeToolExitCode;$record.start_attempted=$operationAttempted;$record.start_outcome=$operationOutcome
  $record.qpc_frequency=$frequency;$record.external_entry_qpc=$commonQpc;$record.elapsed_upper_bound_seconds=($modeEntryQpc-$commonQpc)/[double]$frequency
  $record.observation_semantics='Root dispatched Complete only after actual Invoke tool completion; Complete entry is an upper bound, not the exact return instant'
  $record.invoke_tool_return_observed_by_root=$true;$record.operation_succeeded=($operationSucceeded -and $closureGuardPassed -and $InvokeToolExitCode -eq 0);$record.custody_closed=$operationCustody;$record.closure_guard_passed=$closureGuardPassed;$record.closure_guard_refusal=$closureGuardRefusal;$record.release_published=$false;$record.full_caller_accepted=$false
  [void](Write-New 'bootstrap-caller-completion_004.json' $record 85)
 }else{
  Need ($null -ne $CompleteToolExitCode) 'Actual completed Complete tool exit required'
  $completionRef=Existing 'bootstrap-caller-completion_004.json';$completion=$completionRef.value
  Receipt $completion 'cho51_p3_bootstrap_caller_completion_v4'
  Closed $completion @('schema','scope','observed_utc','request_sha256','root_admission_sha256','scientific_admission','dispatch_sha256','supervision_sha256','failure_sha256','invoke_tool_call_id','post_invoke_return_upper_bound_qpc','post_invoke_return_upper_bound_utc','invoke_tool_exit_code','start_attempted','start_outcome','qpc_frequency','external_entry_qpc','elapsed_upper_bound_seconds','observation_semantics','invoke_tool_return_observed_by_root','operation_succeeded','custody_closed','closure_guard_passed','closure_guard_refusal','release_published','full_caller_accepted')
  Need ($completion.invoke_tool_return_observed_by_root -is [bool] -and $completion.invoke_tool_return_observed_by_root -and $completion.post_invoke_return_upper_bound_qpc -is [long] -and $completion.post_invoke_return_upper_bound_qpc -lt $modeEntryQpc -and $completion.external_entry_qpc -eq $commonQpc -and $completion.qpc_frequency -eq $frequency -and $completion.dispatch_sha256 -ceq $dispatchRef.sha256 -and $completion.operation_succeeded -is [bool] -and $completion.custody_closed -is [bool]) 'Actual earlier caller completion required'
  Need ($completion.invoke_tool_exit_code -is [long] -and (-not $completion.operation_succeeded -or $completion.invoke_tool_exit_code -eq 0)) 'Actual nonzero Invoke cannot become successful'
  Need ($completion.start_attempted -is [bool] -and $completion.start_outcome -cin @('not_attempted','unknown','started') -and (-not $completion.custody_closed -or $completion.start_outcome -cne 'unknown')) 'Unknown start custody cannot be released'
  if($null -ne $completion.supervision_sha256){Need ((Existing 'bootstrap-supervision_004.json').sha256 -ceq $completion.supervision_sha256 -and $null -eq $completion.failure_sha256 -and -not (Present (Join-Path $run 'bootstrap-failure_004.json'))) 'Supervision changed after caller observation'}
  else{Need ((Existing 'bootstrap-failure_004.json').sha256 -ceq $completion.failure_sha256 -and $null -eq $completion.supervision_sha256) 'Failure changed after caller observation'}
  $record=Common 'cho51_p3_bootstrap_release_v4';$record.dispatch_sha256=$dispatchRef.sha256;$record.caller_completion_sha256=$completionRef.sha256
  $record.external_entry_qpc=$commonQpc;$record.qpc_frequency=$frequency;$record.release_publication_elapsed_seconds=Seconds
  $record.start_attempted=$completion.start_attempted;$record.start_outcome=$completion.start_outcome
  $record.complete_tool_exit_code=[int]$CompleteToolExitCode;$record.operation_succeeded=($completion.operation_succeeded -and $closureGuardPassed -and $CompleteToolExitCode -eq 0);$record.custody_closed=$completion.custody_closed;$record.operation_released=$completion.custody_closed;$record.closure_guard_passed=$closureGuardPassed;$record.closure_guard_refusal=$closureGuardRefusal;$record.release_tool_return_observed=$false;$record.post_release_external_audit_required=$true;$record.full_caller_accepted=$false;$record.observational_manifest_accepted=$false
  [void](Write-New 'bootstrap-release_004.json' $record 85)
 }
}catch{
 $failure=$_.Exception.Message
 $cleanupOnly=$true
 $failureStdout=$null;$failureStderr=$null;$partialPreserved=(-not $startAttempted -and $startOutcome -ceq 'not_attempted')
 if($startAttempted){
  try{
   Cleanup-Identity
   if(-not $process.HasExited){$process.Kill()}
   while((Seconds) -lt 80 -and -not $process.HasExited){
    Clock 80 $false
    if($null -ne $stdout){Drain-Poll $stdout};if($null -ne $stderr){Drain-Poll $stderr}
    [void]$process.WaitForExit(20)
   }
   $childReaped=$process.WaitForExit(0)
   if($null -eq $stdout){$stdout=Drain-New $process.StandardOutput.BaseStream}
   if($null -eq $stderr){$stderr=Drain-New $process.StandardError.BaseStream}
   while((Seconds) -lt 80 -and (-not $stdout.eof -or -not $stderr.eof)){
    Clock 80 $false;Drain-Poll $stdout;Drain-Poll $stderr;[Threading.Thread]::Sleep(10)
   }
   if(-not $childReaped -or -not $stdout.eof -or -not $stderr.eof){$custodyClosed=$false}
   if($childStartTicks -gt 0){Child-Table}else{$custodyClosed=$false}
  }catch{$custodyClosed=$false}
  try{
   if($null -ne $stdout -and -not (Present (Join-Path $run 'bootstrap-stdout_004.txt'))){$failureStdout=Write-Stream 'bootstrap-stdout_004.txt' $stdout.data.ToArray()}
   if($null -ne $stderr -and -not (Present (Join-Path $run 'bootstrap-stderr_004.txt'))){$failureStderr=Write-Stream 'bootstrap-stderr_004.txt' $stderr.data.ToArray()}
   $partialPreserved=((Present (Join-Path $run 'bootstrap-stdout_004.txt')) -and (Present (Join-Path $run 'bootstrap-stderr_004.txt')))
  }catch{$partialPreserved=$false}
 }
 if($startOutcome -ceq 'unknown'){$custodyClosed=$false}
 if($authenticated){
  try{
   $record=Common 'cho51_p3_bootstrap_failure_v4';$record.mode=$Mode;$record.failure=$failure.Substring(0,[math]::Min(512,$failure.Length))
   $record.start_attempted=$startAttempted;$record.start_outcome=$startOutcome;$record.child_started=$childStarted;$record.child_pid=$childId;$record.child_reaped=$childReaped;$record.custody_closed=$custodyClosed
   $record.stdout_eof=($null -ne $stdout -and $stdout.eof);$record.stderr_eof=($null -ne $stderr -and $stderr.eof)
   $record.stdout=$failureStdout;$record.stderr=$failureStderr;$record.partial_outputs_preserved=$partialPreserved;$record.automatic_retry_permitted=$false;$record.full_caller_accepted=$false
   [void](Write-New 'bootstrap-failure_004.json' $record 85)
  }catch{}
 }
}finally{
 if($null -ne $stdout){$stdout.stream.Dispose();$stdout.data.Dispose()}
 if($null -ne $stderr){$stderr.stream.Dispose();$stderr.data.Dispose()}
 if($handleRef){$safeHandle.DangerousRelease()}
 if($null -ne $process){$process.Dispose()}
 foreach($stream in $held.Values){$stream.Dispose()}
}
if($null -ne $failure){throw $failure}
Clock 85
[ordered]@{mode=$Mode;elapsed_seconds=(Seconds);full_caller_accepted=$false;post_release_external_audit_required=$true;scientific_admission=$false}|ConvertTo-Json -Compress
