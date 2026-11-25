# Windows offline synthetic microphone fixtures. Does not call a voice provider.
param([string]$OutputDirectory = ".tools/qa-audio")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$folder = [System.IO.Directory]::CreateDirectory($OutputDirectory).FullName
$cases = @(
    @("availability", "Please check availability with Doctor Arjun Rao tomorrow.", 0),
    @("phone", "Nine eight seven six five four three two one zero.", 0),
    @("slow-phone", "Nine eight seven six five four three two one zero.", -3),
    @("fast-phone", "Nine eight seven six five four three two one zero.", 3),
    @("correction", "No, the last digit is one. Nine eight seven six five four three two one one.", 0),
    @("positive", "Yes, that is correct.", 0),
    @("negative", "No, wait.", 0),
    @("specialty", "Cardiology tomorrow at three ten P M.", 0),
    @("interrupt", "Actually, stop there.", 1)
)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $manifest = foreach ($case in $cases) {
        $synth.Rate = $case[2]
        $synth.SetOutputToWaveFile((Join-Path $folder ($case[0] + ".wav")))
        $synth.Speak($case[1])
        $synth.SetOutputToNull()
        [PSCustomObject]@{id=$case[0];reference=$case[1];rate=$case[2];voice=$synth.Voice.Name;classification="synthetic"}
    }
    $manifest | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $folder "manifest.json")
} finally {
    $synth.Dispose()
}
