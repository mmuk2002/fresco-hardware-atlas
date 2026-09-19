$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$demoNarration = Get-Content -LiteralPath 'output/demo/narration.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$demoSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$demoSynth.SelectVoice('Microsoft David Desktop')
$demoSynth.Rate = 0
for ($demoIndex = 0; $demoIndex -lt $demoNarration.Count; $demoIndex++) {
    $demoVoiceFile = Join-Path (Get-Location).Path "output/demo/voice-$demoIndex.wav"
    $demoSynth.SetOutputToWaveFile($demoVoiceFile)
    $demoSynth.Speak($demoNarration[$demoIndex].text)
    $demoSynth.SetOutputToNull()
}
$demoSynth.Dispose()
Write-Output 'Synthetic demo narration generated.'
