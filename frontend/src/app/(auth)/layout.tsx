import type { Metadata } from "next";
import "../globals.css";

export const metadata: Metadata = {
  title: "CareerPilot AI — Sign In",
  description: "Sign in to CareerPilot AI",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4">
      <div className="w-full max-w-md">
        {children}
      </div>
    </div>
  );
}
