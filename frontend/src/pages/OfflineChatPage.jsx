import React from 'react';
import { Bluetooth, MessageSquare, WifiOff, Smartphone } from 'lucide-react';

const OfflineChatPage = () => {
  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
            <Bluetooth className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 tracking-tight mb-2">Offline Bluetooth Chat</h2>
            <p className="text-gray-600">
              A companion Android app for nearby communication without internet. It helps people who cannot speak or hear easily chat with someone beside them using text and media over Bluetooth.
            </p>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card">
          <WifiOff className="w-6 h-6 text-primary-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-1">No connectivity</h3>
          <p className="text-sm text-gray-600">Works locally over Bluetooth Classic sockets.</p>
        </div>
        <div className="card">
          <MessageSquare className="w-6 h-6 text-primary-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-1">Separate chats</h3>
          <p className="text-sm text-gray-600">Each nearby device gets its own local conversation history.</p>
        </div>
        <div className="card">
          <Smartphone className="w-6 h-6 text-primary-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-1">Android app</h3>
          <p className="text-sm text-gray-600">Open <code>offline-chat-android</code> in Android Studio to build the APK.</p>
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-3">Android project location</h3>
        <code className="block px-4 py-3 rounded-xl bg-gray-50 text-sm text-gray-700">
          offline-chat-android/
        </code>
        <p className="mt-3 text-sm text-gray-500">
          After building in Android Studio, the debug APK is usually generated at <code>offline-chat-android/app/build/outputs/apk/debug/app-debug.apk</code>.
        </p>
      </div>
    </div>
  );
};

export default OfflineChatPage;
