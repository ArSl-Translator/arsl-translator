import React from 'react';
import { Bluetooth, Database, Download, FileArchive, MessageSquare, RadioTower, ShieldCheck, Smartphone, WifiOff } from 'lucide-react';

const apkUrl = '/downloads/accessible-chat.apk';

const features = [
  {
    icon: WifiOff,
    title: 'Works without internet',
    text: 'Start a nearby conversation even when Wi-Fi and mobile data are unavailable.',
  },
  {
    icon: RadioTower,
    title: 'Nearby device pairing',
    text: 'One person opens a chat session and the other joins from a nearby Android phone.',
  },
  {
    icon: FileArchive,
    title: 'Text and media sharing',
    text: 'Exchange messages and helpful media during face-to-face communication.',
  },
  {
    icon: Database,
    title: 'On-device history',
    text: 'Conversations stay available on the phone for later reference.',
  },
];

const OfflineChatPage = () => {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="panel overflow-hidden">
        <div className="grid gap-6 border-b border-gray-200 bg-white p-6 lg:grid-cols-[1fr_360px]">
          <div>
            <p className="section-title">Mobile companion</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-950">Accessible Chat for nearby communication</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-500">
              A companion Android app that helps people communicate with someone beside them using text and
              media, even when there is no internet connection. It is built for quick, private, face-to-face
              conversations in clinics, classrooms, public services, and everyday settings.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
                <Bluetooth className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-950">Accessible Chat for Android</p>
                <p className="text-xs font-medium text-gray-500">Private nearby messaging</p>
              </div>
            </div>
            <p className="mt-4 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm leading-6 text-gray-600">
              Install on two Android phones, choose complementary roles, and start communicating nearby.
            </p>
            <a href={apkUrl} download="accessible-chat.apk" className="btn-primary mt-4 w-full">
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
            <h3 className="text-lg font-bold text-gray-950">Designed for real conversations</h3>
          </div>
          <div className="mt-4 space-y-3 text-sm leading-6 text-gray-600">
            <p>Use one phone for the person who needs assistance and another for the person helping nearby.</p>
            <p>Messages appear in a familiar chat interface with connection status always visible.</p>
            <p>Conversation history remains on the device, so important context is not lost after reconnecting.</p>
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
