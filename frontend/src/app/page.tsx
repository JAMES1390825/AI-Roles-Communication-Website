// src/app/page.tsx
export default function HomePage() {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Welcome to AI Role Playing!
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Your journey with AI characters begins here.
            </p>
          </div>
          {/* 这里将来会是登录/注册或角色选择的入口 */}
        </div>
      </div>
    );
  }