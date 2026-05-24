import React from 'react';
import { Bluetooth, Database, Download, FileArchive, MessageSquare, RadioTower, ShieldCheck, Smartphone, WifiOff } from 'lucide-react';

const apkUrl = '/downloads/accessible-chat.apk';

const features = [
  {
    icon: WifiOff,
    title: 'No internet required',
    text: 'Nearby Android devices communicate directly over Bluetooth Classic sockets.',
  },
  {
    icon: RadioTower,
    title: 'Server and client roles',
    text: 'One phone waits as the Bluetooth server while the other connects as the client.',
  },
  {
    icon: FileArchive,
    title: 'Binary transfer',
    text: 'The protocol supports framed text and media payloads for practical offline exchange.',
  },
  {
    icon: Database,
    title: 'Local history',
    text: 'Room stores conversations on device so chats remain available after reconnecting.',
  },
];

const OfflineChatPage = () => {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="panel overflow-hidden">
        <div className="grid gap-6 border-b border-gray-200 bg-white p-6 lg:grid-cols-[1fr_360px]">
          <div>
            <p className="section-title">Companion mobile system</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-950">Offline Bluetooth chat for nearby communication</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-500">
              The Android app adds a distributed-systems layer to the translator: socket programming,
              background transfer threads, Bluetooth discovery, and patient-assistant style text communication
              without Wi-Fi, mobile data, or sign language knowledge.
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
                <Bluetooth className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-950">Android project</p>
                <p className="text-xs font-medium text-gray-500">Kotlin, Jetpack Compose, Room</p>
              </div>
            </div>
            <code className="mt-4 block rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
              offline-chat-android/
            </code>
            <a
              href={apkUrl}
              download="accessible-chat.apk"
              className="btn-primary mt-4 w-full"
            >
              <Download className="h-4 w-4" />
              Download Android APK
            </a>
          </div>
        </div>

        <div className="grid gap-4 p-6 md:grid-cols-2 xl:grid-cols-4">
          {features.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <Icon className="mb-3 h-5 w-5 text-gray-900" />
              <h3 className="font-bold text-gray-950">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-500">{text}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-bold text-gray-950">What it demonstrates</h3>
          </div>
          <div className="mt-4 space-y-3 text-sm leading-6 text-gray-600">
            <p>Bluetooth RFCOMM socket setup with explicit server/client behavior.</p>
            <p>Threaded listening and transfer loops so the UI remains responsive while messages arrive.</p>
            <p>Structured local storage for conversations, messages, and media metadata.</p>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-2">
            <Smartphone className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-bold text-gray-950">Install on Android</h3>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Open this page from an Android phone and download the APK. Android may ask you to allow installation
            from the browser or file manager before the app can be installed.
          </p>
          <a href={apkUrl} download="accessible-chat.apk" className="btn-primary mt-4">
            <Download className="h-4 w-4" />
            Download APK
          </a>
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0" />
            Install the same APK on both phones, then use one device as the host and the other as the helper.
          </div>
        </div>
      </div>
    </div>
  );
};

export default OfflineChatPage;
