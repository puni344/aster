param([string]$OutputDirectory = ".tools/qa-caller")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$folder = [System.IO.Directory]::CreateDirectory($OutputDirectory).FullName
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
$lines = @{
    book = "Please book me with Doctor Asha Menon tomorrow at nine A M. My mobile number is nine eight seven six five four three two one zero."
    time = "Tomorrow at nine A M with Doctor Asha Menon, please."
    phone = "My mobile number is nine eight seven six five four three two one zero."
    yes = "Yes, that is correct."
    cancel = "Please cancel the appointment you just booked with Doctor Asha Menon."
}
try {
    foreach ($entry in $lines.GetEnumerator()) {
        $speech.SetOutputToWaveFile((Join-Path $folder ($entry.Key+".wav")))
        $speech.Speak($entry.Value)
        $speech.SetOutputToNull()
    }
} finally {$speech.Dispose()}
