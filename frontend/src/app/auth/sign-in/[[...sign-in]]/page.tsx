import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070b14] py-12 px-4 sm:px-6 lg:px-8">
      <SignIn
        path="/auth/sign-in"
        routing="path"
        signUpUrl="/auth/sign-up"
        fallbackRedirectUrl="/dashboard"
      />
    </div>
  );
}
