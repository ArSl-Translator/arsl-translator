# Accessible Chat Android App

Accessible Chat is the Android companion application for the ArSL Translator platform. It is designed for nearby communication when internet access is unavailable, especially for people who need text-based communication with someone beside them.

## What It Does

- Discovers nearby Android devices over Bluetooth.
- Uses explicit Bluetooth server and client roles.
- Exchanges chat messages through RFCOMM socket programming.
- Runs background listening and transfer threads so the Compose UI stays responsive.
- Stores conversations and messages locally with Room.
- Supports media-oriented chat flows including images, video, audio, and files.
- Includes Assistive Message Studio for optional chat-integrated clarification, simplification, and context-aware suggested replies.
- Includes Arabic and English resources with RTL support.

The core Bluetooth chat works without internet access. Assistive Message Studio is optional: it requires network access to the deployed ArSL API, where a local open-source Ollama model runs on the VM. If the AI service is unavailable, Bluetooth chat is unaffected.

## Project Structure

```text
offline-chat-android/
├── app/
│   ├── src/main/java/com/healthcare/offlinechat/
│   │   ├── bluetooth/      # Bluetooth discovery, server/client sockets, framed transfer
│   │   ├── data/           # Room entities, DAOs, and database
│   │   ├── media/          # File handling and audio recording helpers
│   │   ├── ui/             # Jetpack Compose screens, components, and theme
│   │   ├── viewmodel/      # Chat state and connection orchestration
│   │   └── MainActivity.kt
│   └── build.gradle.kts
├── gradle/
├── gradlew
├── gradlew.bat
└── settings.gradle.kts
```

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

From this folder:

```bash
./gradlew assembleDebug
```

On Windows PowerShell:

```powershell
.\gradlew.bat assembleDebug
```

The debug APK is generated at:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Notes

- The app package is `com.healthcare.offlinechat`.
- `local.properties`, `.gradle`, `.idea`, `.kotlin`, and `build/` outputs are intentionally not committed.
- Android 12+ requires runtime Bluetooth permissions before scanning or connecting.
