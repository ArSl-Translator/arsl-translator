param(
    [switch]$Push,
    [string]$Remote = "origin",
    [string]$Branch = ""
)

$ErrorActionPreference = "Stop"

function Run-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed"
    }
}

function Commit-Group {
    param(
        [string]$Message,
        [string[]]$Paths,
        [string]$DateStr
    )

    $existing = @()
    foreach ($path in $Paths) {
        if (Test-Path -LiteralPath $path) {
            $existing += $path
        }
    }

    if ($existing.Count -eq 0) {
        Write-Host "Skipping '$Message' because none of its paths exist."
        return
    }

    Run-Git add -- $existing
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Skipping '$Message' because there are no staged changes."
        return
    }

    $env:GIT_COMMITTER_DATE = $DateStr
    Run-Git commit -m $Message --date $DateStr
    $env:GIT_COMMITTER_DATE = $null
}

$repoRoot = (& git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    throw "You already have staged changes. Commit or unstage them before running this script."
}

$status = (& git status --porcelain)
if (-not $status) {
    Write-Host "Working tree is clean. Nothing to commit."
    exit 0
}

$commits = @(
    @{
        Message = "chore: add commit series helper"
        Paths = @("scripts/create_commit_series.ps1")
    },
    @{
        Message = "build: add ArabSign runtime dependencies"
        Paths = @("requirements.base.txt")
    },
    @{
        Message = "build: configure Docker image for MediaPipe pose serving"
        Paths = @(".dockerignore", "Dockerfile", "docker-compose.yml")
    },
    @{
        Message = "feat(api): add ArabSign pose inference adapter"
        Paths = @("src/api/arabsign_inference.py")
    },
    @{
        Message = "feat(api): add model registry and model selection"
        Paths = @("src/api/main.py")
    },
    @{
        Message = "feat(frontend): pass selected model to prediction endpoints"
        Paths = @("frontend/src/services/api.js")
    },
    @{
        Message = "feat(frontend): add model selector to video upload"
        Paths = @("frontend/src/components/VideoUpload.jsx")
    },
    @{
        Message = "feat(frontend): add model selector to webcam capture"
        Paths = @("frontend/src/components/WebcamCapture.jsx")
    },
    @{
        Message = "fix(frontend): support text-only translation results"
        Paths = @("frontend/src/components/PredictionResults.jsx")
    },
    @{
        Message = "feat(frontend): add offline chat overview page"
        Paths = @("frontend/src/App.jsx", "frontend/src/pages/OfflineChatPage.jsx")
    },
    @{
        Message = "docs: add migrated ArabSign model notes"
        Paths = @("docs/arabsign.md")
    },
    @{
        Message = "ml: add ArabSign training entry point"
        Paths = @("scripts/arabsign/train_arabsign.py")
    },
    @{
        Message = "ml: add ArabSign live webcam demo"
        Paths = @("scripts/arabsign/demo_live.py")
    },
    @{
        Message = "ml: add ArabSign video file demo"
        Paths = @("scripts/arabsign/demo_video.py")
    },
    @{
        Message = "ml: add ArabSign skeleton playback demo"
        Paths = @("scripts/arabsign/demo_playback.py")
    },
    @{
        Message = "mobile: scaffold Android offline chat Gradle project"
        Paths = @(
            "offline-chat-android/settings.gradle.kts",
            "offline-chat-android/build.gradle.kts",
            "offline-chat-android/gradle.properties",
            "offline-chat-android/gradle/libs.versions.toml",
            "offline-chat-android/app/build.gradle.kts",
            "offline-chat-android/app/proguard-rules.pro"
        )
    },
    @{
        Message = "mobile: add Android manifest and Arabic-first resources"
        Paths = @(
            "offline-chat-android/app/src/main/AndroidManifest.xml",
            "offline-chat-android/app/src/main/res/values/strings.xml",
            "offline-chat-android/app/src/main/res/values-ar/strings.xml",
            "offline-chat-android/app/src/main/res/values/themes.xml",
            "offline-chat-android/app/src/main/res/xml/file_paths.xml",
            "offline-chat-android/app/src/main/res/xml/locales_config.xml"
        )
    },
    @{
        Message = "mobile: add application locale bootstrap"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/AccessibleChatApplication.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/LocaleHelper.kt"
        )
    },
    @{
        Message = "mobile: add Room conversation and message storage"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/AppDatabase.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/Conversation.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/ConversationDao.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/ChatMessage.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/ChatMessageDao.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/data/MessageType.kt"
        )
    },
    @{
        Message = "mobile: add Bluetooth server and client socket roles"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/bluetooth/BluetoothServer.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/bluetooth/BluetoothClient.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/bluetooth/BluetoothModels.kt"
        )
    },
    @{
        Message = "mobile: add framed Bluetooth text and binary transfer"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/bluetooth/BluetoothDataTransfer.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/bluetooth/BluetoothController.kt"
        )
    },
    @{
        Message = "mobile: add media handling and audio recording"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/media/FileUtils.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/media/MediaHandler.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/media/AudioRecorder.kt"
        )
    },
    @{
        Message = "mobile: add chat state management view model"
        Paths = @("offline-chat-android/app/src/main/java/com/arsl/offlinechat/viewmodel/ChatViewModel.kt")
    },
    @{
        Message = "mobile: add accessible chat theme and reusable components"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/theme/Color.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/theme/Theme.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/components/ConversationItem.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/components/DeviceItem.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/components/AttachmentSheet.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/components/MessageBubble.kt"
        )
    },
    @{
        Message = "mobile: add offline chat screens and activity routing"
        Paths = @(
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/MainActivity.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/screens/HomeScreen.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/screens/ConversationListScreen.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/screens/DeviceListScreen.kt",
            "offline-chat-android/app/src/main/java/com/arsl/offlinechat/ui/screens/ChatScreen.kt"
        )
    },
    @{
        Message = "docs: document Android offline chat app"
        Paths = @("offline-chat-android/README.md")
    },
    @{
        Message = "docs: consolidate platform README"
        Paths = @("README.md")
    }
)

$totalCommits = $commits.Count
$lastDate = [datetime]::new(2026, 5, 23, 12, 0, 0)

foreach ($i in 0..($totalCommits - 1)) {
    $daysBack = $totalCommits - 1 - $i
    $commitDate = $lastDate.AddDays(-$daysBack)
    $dateStr = $commitDate.ToString("yyyy-MM-dd HH:mm:ss")

    $commit = $commits[$i]
    Commit-Group -Message $commit.Message -Paths $commit.Paths -DateStr $dateStr
}

$remaining = (& git status --porcelain)
if ($remaining) {
    Write-Host "There are remaining changes not covered by the scripted groups:"
    Write-Host $remaining
    throw "Commit script stopped with remaining changes. Add another group or commit them manually."
}

if ($Push) {
    if ([string]::IsNullOrWhiteSpace($Branch)) {
        $Branch = (& git branch --show-current).Trim()
    }
    if ([string]::IsNullOrWhiteSpace($Branch)) {
        throw "Could not determine current branch. Pass -Branch <name>."
    }
    Run-Git push $Remote $Branch
}

Write-Host "Commit series complete."