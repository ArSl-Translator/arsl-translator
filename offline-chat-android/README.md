# Accessible Chat Android App

Accessible Chat is the Android companion application for the ArSL Translator platform. It is built for nearby, face-to-face communication when internet access is unavailable, while also offering optional online AI writing support when the deployed ArSL API is reachable.

## What It Does

- Discovers nearby Android devices over Bluetooth Classic.
- Lets one phone host a chat and another phone connect as the helper device.
- Exchanges text messages through RFCOMM socket streams.
- Transfers images, video, audio, and files with a framed binary protocol.
- Runs blocking socket reads on background threads so the Compose UI remains responsive.
- Stores conversations and messages locally with Room.
- Includes Assistive Message Studio for optional message clarification, simplification, and context suggestions.
- Supports Arabic and English usage, including RTL text rendering.

The core Bluetooth chat is fully offline. Assistive Message Studio is optional and online: the app calls the deployed ArSL API, and the API calls a local open-source Ollama model running on the VM. If the AI service is unavailable, Bluetooth messaging still works.

## Project Structure

```text
offline-chat-android/
  app/
    src/main/java/com/healthcare/offlinechat/
      ai/             API client for Assistive Message Studio
      bluetooth/      Bluetooth discovery, server/client sockets, framed transfer
      data/           Room entities, DAOs, and database
      media/          File handling, media metadata, and audio recording helpers
      ui/             Jetpack Compose screens, components, and theme
      viewmodel/      Chat state and connection orchestration
      MainActivity.kt
    build.gradle.kts
  gradle/
  gradlew
  gradlew.bat
  settings.gradle.kts
```

## Assistive Message Studio

The chat screen integrates three AI actions:

| Action | Used by | API mode |
|---|---|---|
| Make clearer | Helper reading a rough message from the assisted user | `deaf_to_hearing` |
| Simplify | Assisted user reading a longer message from the helper | `hearing_to_deaf` |
| Sparkle composer suggestions | Either user preparing a new message | `suggestions` |

Client file:

```text
app/src/main/java/com/healthcare/offlinechat/ai/AiAssistantClient.kt
```

Default production API:

```text
https://arsl.hadighazi.com/api/ai/assist
```

The deployed backend currently supports both the base Ollama model and the fine-tuned healthcare communication model:

```text
qwen2.5:1.5b
qwen25-healthcare
```

The backend also applies a cleanup guardrail for the fine-tuned model so leaked prompt text such as examples, arrows, or instruction fragments is not returned to the app.

## Build In Android Studio

1. Open Android Studio.
2. Select `Open`.
3. Choose:

```text
arsl-translator/offline-chat-android
```

4. Let Gradle sync.
5. Connect an Android phone with USB debugging enabled.
6. Run the `app` configuration.

Bluetooth chat should be tested with two physical Android devices. Emulators are not reliable for Bluetooth Classic workflows.

## Build APK From Terminal

Debug build:

```powershell
cd offline-chat-android
.\gradlew.bat assembleDebug
```

Release build:

```powershell
cd offline-chat-android
.\gradlew.bat :app:assembleRelease --no-daemon --console=plain
```

The release APK is generated at:

```text
offline-chat-android/app/build/outputs/apk/release/app-release.apk
```

The website-download APK is:

```text
frontend/public/downloads/accessible-chat.apk
```

When publishing a new Android build, copy the release APK to the frontend download path:

```powershell
Copy-Item `
  offline-chat-android\app\build\outputs\apk\release\app-release.apk `
  frontend\public\downloads\accessible-chat.apk `
  -Force
```

Current checked website APK matches the latest local release build:

```text
SHA-256: 499EE72EEC0AB061B8E4CA06E9DEF3477988C06C5E1E6165D02317EC2A3AE0F5
Size:    13,124,454 bytes
```

## Installation Notes

- The package name is `com.healthcare.offlinechat`.
- If Android says the package conflicts with an existing package, uninstall the USB-debug build first.
- Android 12+ requires runtime Bluetooth permissions before scanning or connecting.
- Some phones require pairing in Android system settings before the app can connect.
- Install the same signed APK on both phones for normal testing.

## Files Not To Commit

The following are intentionally ignored:

- `local.properties`
- `.gradle/`
- `.idea/`
- `.kotlin/`
- `build/`
- keystore files
- `keystore.properties`
