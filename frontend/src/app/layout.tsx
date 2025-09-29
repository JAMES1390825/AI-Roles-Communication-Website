// src/app/layout.tsx
import './globals.css'; // 导入全局样式，虽然我们主要用 Tailwind
import { AuthProvider } from '@/context/AuthContext'; // 导入 AuthProvider

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-100 text-gray-900 antialiased">
        <AuthProvider>{children}</AuthProvider> {/* 使用 AuthProvider 包裹 children */}
      </body>
    </html>
  );
}