'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="text-center space-y-8 max-w-2xl">
        <h1 className="text-5xl font-bold text-gray-900">
          Welcome to <span className="text-blue-600">Bankan</span>
        </h1>
        <p className="text-xl text-gray-600">
          A production-grade task management platform with real-time collaboration.
          Manage your team's work efficiently.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/login">
            <Button size="lg" className="px-8">
              Sign In
            </Button>
          </Link>
          <Link href="/register">
            <Button size="lg" variant="outline" className="px-8">
              Get Started
            </Button>
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📋 Kanban Boards</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Visualize your workflow with drag-and-drop boards
              </CardDescription>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">💬 Real-time</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Live updates and instant notifications
              </CardDescription>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📊 Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Track team performance and sprint velocity
              </CardDescription>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}