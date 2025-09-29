// src/app/layout.tsx
import './globals.css';
import { AuthProvider } from '@/context/AuthContext'; // 导入 AuthProvider

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider> {/* 包裹在 AuthProvider 中 */}
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
