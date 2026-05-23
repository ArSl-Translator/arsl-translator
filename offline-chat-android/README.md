# Accessible Offline Chat Android App

This is a separate Android app inside the ArSL Translator project. It lets a deaf, hard-of-hearing, mute, or speech-impaired person communicate with someone nearby using text and media without internet access.

## What It Does

- Works offline over Bluetooth Classic RFCOMM sockets.
- One phone chooses **I need assistance** and hosts the chat.
- The nearby helper chooses **I want to help**, selects the host phone, and connects.
- Messages are stored locally with Room.
- Each nearby device gets its own conversation, so chats with multiple phones are not mixed together.
- Supports text, images, camera photos, audio recordings, videos, and files.
- Arabic is the default UI direction/language, with English resources included.

## Distributed Systems Concepts

- Peer-to-peer communication.
- Client/server roles over Bluetooth sockets.
- Background listening thread for incoming data.
- Message framing protocol for text and binary media.
- Local persistence and per-peer conversation state.
- Disconnection handling.

## Open In Android Studio

1. Open Android Studio.
2. Choose **File > Open**.
3. Select:

```text
arsl-translator/offline-chat-android
```

4. Let Android Studio sync Gradle.
5. If sync is not automatic, use **File > Sync Project with Gradle Files**.

## Required Environment

- Android Studio Ladybug or newer is recommended.
- Android SDK 35 installed.
- JDK 17. Android Studio usually bundles this.
- Two real Android phones. Bluetooth does not work properly on Android emulators.

## Run On Two Phones

1. Enable Developer Options and USB Debugging on both phones.
2. Connect both phones by USB.
3. In Android Studio, select Phone A from the device dropdown and press Run.
4. On Phone A, tap **أحتاج مساعدة** / **I need assistance**.
5. Select Phone B from the Android Studio device dropdown and press Run again.
6. On Phone B, tap **أريد المساعدة** / **I want to help**.
7. Pair the phones in Android Bluetooth settings if they are not already paired.
8. On Phone B, select Phone A from the paired/scanned devices list.
9. Start chatting.

## Media Transfer Notes

Bluetooth is slow compared to Wi-Fi. For a classroom demo, use small files:

- Images: under 3 MB
- Audio: short clips
- Video: very short clips
- Files: under 10-20 MB

The current transport rejects media larger than 25 MB to avoid memory problems on phones.

## Important Testing Notes

- Keep the host phone app open on the conversation list screen while the helper connects.
- If a connection fails, turn Bluetooth off/on on both phones and retry.
- Some Android versions require pairing from system Bluetooth settings before app-level RFCOMM sockets connect reliably.
- If the database schema changes during development, uninstall the app from both phones before reinstalling.

## File Structure

```text
offline-chat-android/
  app/src/main/java/com/arsl/offlinechat/
    MainActivity.kt
    AccessibleChatApplication.kt
    bluetooth/
      BluetoothController.kt
      BluetoothServer.kt
      BluetoothClient.kt
      BluetoothDataTransfer.kt
      BluetoothModels.kt
    data/
      AppDatabase.kt
      Conversation.kt
      ConversationDao.kt
      ChatMessage.kt
      ChatMessageDao.kt
      MessageType.kt
    media/
      MediaHandler.kt
      FileUtils.kt
      AudioRecorder.kt
    ui/
      components/
      screens/
      theme/
    viewmodel/
      ChatViewModel.kt
```

## Future Improvements

- Transfer progress indicator for large media.
- Wi-Fi Direct mode for faster video sharing.
- Message acknowledgements and retry queue.
- Optional encryption using a shared session key.
- Integrate the sign-language translator by sending translated text into this chat.
